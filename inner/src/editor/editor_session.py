# editor/editor_session.py
# module that owns the live editor document while the pywebview window is open.
#
# This is the backend dispatcher referenced in AGENTS.md / the editor pywebview
# plan. The frontend never owns document data; it sends intents (drawNote,
# eraseNoteAt, undo, etc.) and reads snapshots back. All transaction recording,
# audio preview, autosave, and persistence flow through this class so swapping
# the React surface later does not change correctness behavior.
###### IMPORT ######

import copy
import threading

###### INTERNAL MODULES ######

from console_controls.console import *
from utils.note import Note
import sound.sound_processing as sp
import utils.file_io as fio
import utils.project_state as pst
import utils.state_loading as sl
from utils.autosave import AutoSave

###### CONSTANTS ######

COLOR_NAMES = ["orange", "purple", "cyan", "lime", "blue", "pink"]
ALL_CHANNEL_NAME = "all"
ACCIDENTAL_FLATS = "flats"
ACCIDENTAL_SHARPS = "sharps"

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

MODES_INTERVALS = {
    "Lydian":         [0, 2, 4, 6, 7, 9, 11],
    "Ionian (maj.)":  [0, 2, 4, 5, 7, 9, 11],
    "Mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "Dorian":         [0, 2, 3, 5, 7, 9, 10],
    "Aeolian (min.)": [0, 2, 3, 5, 7, 8, 10],
    "Phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "Locrian":        [0, 1, 3, 5, 6, 8, 10],
}

###### HELPERS ######

def serializeNote(note: Note) -> dict:
    '''
    fields:
        note (Note) - runtime note instance
    outputs: dict

    Returns a JSON-friendly representation of a runtime note for the frontend.
    '''
    return {
        "pitch": note.pitch,
        "time": note.time,
        "duration": note.duration,
        "data_fields": copy.deepcopy(note.dataFields),
        "selected": bool(note.selected),
    }


def serializeNoteMap(noteMap: dict) -> dict:
    '''
    fields:
        noteMap (dict) - runtime note map keyed by color
    outputs: dict

    Serializes the runtime note map into JSON-safe lists for the frontend.
    '''
    out = {}
    for colorName, notes in noteMap.items():
        out[colorName] = [serializeNote(note) for note in notes]
    return out


def deserializeNote(data: dict) -> Note:
    '''
    fields:
        data (dict) - JSON note payload from the frontend
    outputs: Note

    Builds a runtime Note from a dict payload, preserving selection.
    '''
    note = Note({
        "pitch": data["pitch"],
        "time": data["time"],
        "duration": data["duration"],
        "data_fields": copy.deepcopy(data.get("data_fields", {})),
    })
    if data.get("selected", False):
        note.select()
    return note


###### CLASSES ######

class EditorSession:
    '''
    Holds the active editor document and exposes intent-level operations.

    Construction loads the project file, primes the transaction manager, and
    starts the autosave timer. Each public method mutates state in one place
    so the frontend never observes an intermediate inconsistent snapshot.
    '''

    def __init__(self,
                 workingFilePath: str,
                 titleText: str,
                 sessionID: str,
                 autoSaveDirectory: str = None,
                 stateChangeCallback=None,
                 autoSaveInterval: float = AutoSave.DEFAULT_INTERVAL_SECONDS,
                 debugUiEnabled: bool = False,
                 showDebugByDefault: bool = False):
        '''
        fields:
            workingFilePath (string) - absolute .symphony path
            titleText (string) - project title used for autosave file naming
            sessionID (string) - per-launch session id used for autosave file naming
            autoSaveDirectory (string | None) - directory to write autosave backups
            stateChangeCallback (callable | None) - notified after every state mutation
            autoSaveInterval (float) - autosave cadence in seconds
            debugUiEnabled (boolean) - whether developer debug UI can be shown
            showDebugByDefault (boolean) - whether debug UI opens on launch
        outputs: nothing
        '''
        self.workingFilePath = workingFilePath
        self.titleText = titleText
        self.sessionID = sessionID
        self.autoSaveDirectory = autoSaveDirectory
        self._stateChangeCallback = stateChangeCallback
        self.debugUiEnabled = bool(debugUiEnabled)
        self.showDebugByDefault = self.debugUiEnabled and bool(showDebugByDefault)

        self.lock = threading.RLock()
        self.suspendTransactionCapture = False

        self.noteMap: dict[str, list[Note]] = {color: [] for color in COLOR_NAMES}
        self.instrumentMap: dict[str, int] = {color: 0 for color in COLOR_NAMES}
        self.instrumentMap[ALL_CHANNEL_NAME] = 0
        self.key = "Eb"
        self.mode = "Lydian"
        self.tempo = 360
        self.beatLength = 4
        self.beatsPerMeasure = 4
        self.accidentals = ACCIDENTAL_FLATS
        self.currentColorIdx = 0
        self.projectMeta = copy.deepcopy(sl.DEFAULT_META_FIELD)
        self.playheadHomeTime = 0
        self._activePlayObject = None

        # Temp-note drag state: { action, color, originals[], proposed[] }
        # action is "move" or "duplicate". originals[] are the pre-drag note
        # snapshots used to find and remove originals on a move commit.
        self.tempDragState = None

        self._loadFromFile()

        self.psm = pst.ProjectStateManager(
            snapshotEditorState=self.snapshotEditorState,
            applyEditorStateToRuntime=self.applyEditorStateToRuntime,
            isCaptureSuspended=lambda: self.suspendTransactionCapture,
        )

        self.autoSave = AutoSave(saveCallback=self.saveNow, intervalSeconds=autoSaveInterval)
        self.autoSave.start()

    # ---- lifecycle / persistence ----------------------------------------

    def _loadFromFile(self):
        '''
        fields: none
        outputs: nothing

        Loads the working file and populates session state. Called only by
        the constructor; the open command handler creates a fresh session
        for each project.
        '''
        import dill as pkl

        with open(self.workingFilePath, "rb") as pf:
            ps = sl.toProgramState(pkl.load(pf))

        self.noteMap = ps["noteMap"]
        self.instrumentMap = ps["waveMap"]
        self.key = ps["key"]
        self.mode = ps["mode"]
        self.tempo = int(ps["tpm"])
        self.beatLength = int(ps["beatLength"])
        self.beatsPerMeasure = int(ps["beatsPerMeasure"])
        self.projectMeta = copy.deepcopy(ps["meta"])
        self.accidentals = ACCIDENTAL_SHARPS if "#" in self.key else ACCIDENTAL_FLATS

        for colorName in COLOR_NAMES:
            self.noteMap.setdefault(colorName, [])
        if ALL_CHANNEL_NAME not in self.instrumentMap:
            self.instrumentMap[ALL_CHANNEL_NAME] = 0

    def saveNow(self):
        '''
        fields: none
        outputs: nothing

        Writes the working file and the autosave backup using the existing
        `dumpToFile` path. Called by the autosave thread, on close, and
        whenever the frontend explicitly requests a save.
        '''
        with self.lock:
            programState = sl.newProgramState(
                self.key, self.mode, self.tempo,
                self.noteMap, self.instrumentMap,
                self.beatLength, self.beatsPerMeasure,
                meta=self.projectMeta,
            )
            try:
                fio.dumpToFile(
                    self.workingFilePath,
                    self.workingFilePath,
                    programState,
                    self.autoSaveDirectory,
                    self.titleText,
                    self.sessionID,
                )
            except Exception as exc:  # noqa: BLE001
                console.warn(f"saveNow failed: {exc}")

    def close(self):
        '''
        fields: none
        outputs: nothing

        Cooperatively shuts the session down: stops autosave, performs a
        final synchronous save, and silences any in-flight playback.
        '''
        try:
            self.autoSave.stop()
        finally:
            try:
                self.saveNow()
            finally:
                self.stopPlayback()

    # ---- state observation -----------------------------------------------

    def getDocumentState(self) -> dict:
        '''
        fields: none
        outputs: dict

        Returns a JSON-friendly snapshot for the frontend to render.
        '''
        with self.lock:
            return {
                "workingFilePath": self.workingFilePath,
                "title": self.titleText,
                "noteMap": serializeNoteMap(self.noteMap),
                "instrumentMap": copy.deepcopy(self.instrumentMap),
                "key": self.key,
                "mode": self.mode,
                "tempo": int(self.tempo),
                "beatLength": int(self.beatLength),
                "beatsPerMeasure": int(self.beatsPerMeasure),
                "accidentals": self.accidentals,
                "currentColorIdx": int(self.currentColorIdx),
                "projectMeta": copy.deepcopy(self.projectMeta),
                "playheadHomeTime": float(self.playheadHomeTime),
                "tempDrag": copy.deepcopy(self.tempDragState),
                "debug": {
                    "enabled": self.debugUiEnabled,
                    "showDebugByDefault": self.showDebugByDefault,
                },
            }

    def setStateChangeCallback(self, callback):
        '''
        fields:
            callback (callable | None) - invoked with no args after each mutation
        outputs: nothing
        '''
        self._stateChangeCallback = callback

    def _notifyStateChanged(self):
        '''
        fields: none
        outputs: nothing

        Fires the state-change callback (if any) outside the session lock.
        '''
        callback = self._stateChangeCallback
        if callback is None:
            return
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor session state callback failed: {exc}")

    # ---- transaction snapshot/apply (for ProjectStateManager) -----------

    def snapshotEditorState(self) -> dict:
        '''
        fields: none
        outputs: dict

        Returns the deterministic snapshot the transaction manager replays.
        '''
        return {
            "noteMap": pst.snapshotNoteMapState(self.noteMap),
            "waveMap": copy.deepcopy(self.instrumentMap),
            "tempo": int(self.tempo),
            "beatLength": int(self.beatLength),
            "beatsPerMeasure": int(self.beatsPerMeasure),
            "key": str(self.key),
            "mode": str(self.mode),
            "accidentals": self.accidentals,
            "colorIndex": int(self.currentColorIdx),
        }

    def applyEditorStateToRuntime(self, stateSnapshot: dict):
        '''
        fields:
            stateSnapshot (dict) - snapshot to install
        outputs: nothing

        Restores session state from a transaction-manager snapshot. The
        caller suspends transaction capture for the duration of replay.
        '''
        self.suspendTransactionCapture = True
        try:
            with self.lock:
                self._applyNoteMapSnapshot(stateSnapshot.get("noteMap", {}))
                self.instrumentMap = copy.deepcopy(stateSnapshot.get("waveMap", self.instrumentMap))
                self.tempo = int(stateSnapshot.get("tempo", self.tempo))
                self.beatLength = int(stateSnapshot.get("beatLength", self.beatLength))
                self.beatsPerMeasure = int(stateSnapshot.get("beatsPerMeasure", self.beatsPerMeasure))
                self.key = stateSnapshot.get("key", self.key)
                self.mode = stateSnapshot.get("mode", self.mode)
                self.accidentals = stateSnapshot.get("accidentals", self.accidentals)
                self.currentColorIdx = int(stateSnapshot.get("colorIndex", self.currentColorIdx))
                self._preprocess()
        finally:
            self.suspendTransactionCapture = False

    def _applyNoteMapSnapshot(self, noteMapSnapshot: dict):
        '''
        fields:
            noteMapSnapshot (dict) - serialized note map
        outputs: nothing
        '''
        self.noteMap.clear()
        for colorName in COLOR_NAMES:
            self.noteMap[colorName] = []

        for colorName, notes in noteMapSnapshot.items():
            if colorName not in self.noteMap:
                self.noteMap[colorName] = []
            for noteData in notes:
                self.noteMap[colorName].append(deserializeNote(noteData))

    # ---- preprocessing --------------------------------------------------

    def _preprocess(self):
        '''
        fields: none
        outputs: nothing

        Trims overlapping notes of the same pitch on the same channel and
        drops zero-duration notes. Mirrors `main.py`'s `preprocess()` so
        downstream renderers and exporters see the same canonical shape.
        '''
        from collections import defaultdict

        for color, notes in self.noteMap.items():
            notesByPitch = defaultdict(list)
            for note in notes:
                notesByPitch[note.pitch].append(note)

            for _pitch, pitchNotes in notesByPitch.items():
                pitchNotes.sort(key=lambda n: n.time)
                for i in range(len(pitchNotes) - 1):
                    current = pitchNotes[i]
                    nextNote = pitchNotes[i + 1]
                    currentEnd = current.time + current.duration
                    if nextNote.time < currentEnd:
                        current.duration = max(0, nextNote.time - current.time)

            self.noteMap[color] = [n for n in notes if n.duration != 0]

    # ---- note edits ------------------------------------------------------

    def drawNote(self, color: str, noteData: dict) -> dict:
        '''
        fields:
            color (string) - target color channel
            noteData (dict) - JSON note payload
        outputs: dict

        Adds a single note to a color channel, finalizes a NEW_NOTE
        transaction, and previews audio for the pitch.
        '''
        with self.lock:
            self.psm.beginInteractionTransaction("brush")
            note = deserializeNote(noteData)
            self.noteMap.setdefault(color, []).append(note)
            self._preprocess()
            try:
                self.playNotePreview(note.pitch, color)
            except Exception:  # noqa: BLE001
                pass
            self.psm.finalizeInteractionTransaction()
        self._notifyStateChanged()
        return {"ok": True}

    def eraseNoteAt(self, color: str, time: float, pitch: int) -> dict:
        '''
        fields:
            color (string) - target color channel
            time (number) - time the user erased at
            pitch (number) - pitch the user erased at
        outputs: dict

        Removes any note overlapping the given grid position. Records a
        DELETE_NOTES transaction iff something actually changed.
        '''
        with self.lock:
            self.psm.beginInteractionTransaction("eraser")
            removed = False
            notes = self.noteMap.setdefault(color, [])
            for note in list(notes):
                if note.pitch == pitch and note.time <= time < note.time + note.duration:
                    notes.remove(note)
                    removed = True
            self._preprocess()
            self.psm.finalizeInteractionTransaction()
        if removed:
            self._notifyStateChanged()
        return {"ok": True, "removed": removed}

    def setSelection(self, selection: list) -> dict:
        '''
        fields:
            selection (list) - list of {color, time, pitch} entries to mark selected
        outputs: dict

        Replaces selection markers atomically. Records a SELECT_NOTES /
        UNSELECT_NOTES transaction depending on net change.
        '''
        normalizedSelection = []
        for entry in (selection or []):
            normalizedSelection.append((entry.get("color"), entry.get("time"), entry.get("pitch")))
        selectionKeys = set(normalizedSelection)
        with self.lock:
            self.psm.beginInteractionTransaction("select")
            for colorName, notes in self.noteMap.items():
                for note in notes:
                    key = (colorName, note.time, note.pitch)
                    if key in selectionKeys:
                        note.select()
                    else:
                        note.unselect()
            self.psm.finalizeInteractionTransaction()
        self._notifyStateChanged()
        return {"ok": True}

    def clearSelection(self) -> dict:
        '''
        fields: none
        outputs: dict

        Unselects every note across every channel.
        '''
        with self.lock:
            self.psm.beginInteractionTransaction("select")
            for notes in self.noteMap.values():
                for note in notes:
                    note.unselect()
            self.psm.finalizeInteractionTransaction()
        self._notifyStateChanged()
        return {"ok": True}

    def deleteSelectedNotes(self) -> dict:
        '''
        fields: none
        outputs: dict

        Drops every selected note across every channel and records a
        DELETE_NOTES transaction if anything was removed.
        '''
        with self.lock:
            beforeSnapshot = self.snapshotEditorState()
            for colorName in list(self.noteMap.keys()):
                self.noteMap[colorName] = [n for n in self.noteMap[colorName] if not n.selected]
            self._preprocess()
            afterSnapshot = self.snapshotEditorState()
            changed = beforeSnapshot != afterSnapshot
            if changed:
                self.psm.pushEditorSnapshotTransaction("DELETE_NOTES", "Delete selected notes")
        if changed:
            self._notifyStateChanged()
        return {"ok": True, "changed": changed}

    # ---- metadata / settings --------------------------------------------

    def setAccidentals(self, accidentals: str) -> dict:
        '''
        fields:
            accidentals (string) - "flats" or "sharps"
        outputs: dict
        '''
        accidentals = ACCIDENTAL_SHARPS if accidentals == ACCIDENTAL_SHARPS else ACCIDENTAL_FLATS
        with self.lock:
            if accidentals == self.accidentals:
                return {"ok": True, "changed": False}
            self.accidentals = accidentals
            self.psm.pushEditorSnapshotTransaction("CHANGE_ACCIDENTALS", "Toggle accidentals")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setBeatLength(self, value: int) -> dict:
        '''
        fields:
            value (int) - new beat length
        outputs: dict
        '''
        value = max(1, int(value))
        with self.lock:
            if value == self.beatLength:
                return {"ok": True, "changed": False}
            self.beatLength = value
            self.psm.pushEditorSnapshotTransaction("CHANGE_BEAT_LENGTH", "Change beat length")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setBeatsPerMeasure(self, value: int) -> dict:
        '''
        fields:
            value (int) - new beats per measure
        outputs: dict
        '''
        value = max(1, int(value))
        with self.lock:
            if value == self.beatsPerMeasure:
                return {"ok": True, "changed": False}
            self.beatsPerMeasure = value
            self.psm.pushEditorSnapshotTransaction("CHANGE_BEATS_PER_MEASURE", "Change beats per measure")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setTempo(self, value: int) -> dict:
        '''
        fields:
            value (int) - new tempo in tpm
        outputs: dict
        '''
        value = max(10, int(value))
        with self.lock:
            if value == self.tempo:
                return {"ok": True, "changed": False}
            self.tempo = value
            self.psm.pushEditorSnapshotTransaction("CHANGE_TEMPO", "Change tempo")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setKey(self, key: str) -> dict:
        '''
        fields:
            key (string) - new key name (e.g. "Eb")
        outputs: dict
        '''
        with self.lock:
            if key == self.key:
                return {"ok": True, "changed": False}
            self.key = key
            self.accidentals = ACCIDENTAL_SHARPS if "#" in key else ACCIDENTAL_FLATS
            self.psm.pushEditorSnapshotTransaction("CHANGE_KEY", "Change key")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setMode(self, mode: str) -> dict:
        '''
        fields:
            mode (string) - new mode name
        outputs: dict
        '''
        if mode not in MODES_INTERVALS:
            return {"ok": False, "error": "UnknownMode"}
        with self.lock:
            if mode == self.mode:
                return {"ok": True, "changed": False}
            self.mode = mode
            self.psm.pushEditorSnapshotTransaction("CHANGE_MODE", "Change mode")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setActiveColor(self, colorIdx: int) -> dict:
        '''
        fields:
            colorIdx (int) - 0..6 channel index (6 = all)
        outputs: dict
        '''
        colorIdx = max(0, min(6, int(colorIdx)))
        with self.lock:
            if colorIdx == self.currentColorIdx:
                return {"ok": True, "changed": False}
            self.currentColorIdx = colorIdx
            if colorIdx == 6:
                for notes in self.noteMap.values():
                    for note in notes:
                        note.unselect()
            self.psm.pushEditorSnapshotTransaction("CHANGE_COLOR", "Change color channel")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def setWaveType(self, color: str, waveIdx: int) -> dict:
        '''
        fields:
            color (string) - target channel
            waveIdx (int) - wave/instrument index
        outputs: dict
        '''
        waveIdx = int(waveIdx)
        with self.lock:
            currentValue = self.instrumentMap.get(color)
            if currentValue == waveIdx:
                return {"ok": True, "changed": False}
            self.instrumentMap[color] = waveIdx
            self.psm.pushEditorSnapshotTransaction("CHANGE_WAVE_TYPE", "Change wave type")
        self._notifyStateChanged()
        return {"ok": True, "changed": True}

    def updateProjectMetadata(self, metadata: dict) -> dict:
        '''
        fields:
            metadata (dict) - new file_data metadata payload
        outputs: dict

        Replaces ``meta.file_data`` and persists immediately. Falls back to
        the default schema when fields are missing, matching the existing
        ``update_metadata`` HTTP command behavior.
        '''
        defaultFileData = sl.DEFAULT_META_FIELD["file_data"]
        hasRequiredFields = (
            isinstance(metadata, dict)
            and all(field in metadata for field in defaultFileData.keys())
        )
        savedMetadata = metadata if hasRequiredFields else dict(defaultFileData)
        with self.lock:
            self.projectMeta["file_data"] = savedMetadata
            self.saveNow()
        self._notifyStateChanged()
        return {"ok": True, "metadata": savedMetadata}

    # ---- audio ----------------------------------------------------------

    def playNotePreview(self, pitch: int, color: str = None, durationSeconds: float = 0.2) -> dict:
        '''
        fields:
            pitch (int) - pitch to preview
            color (string | None) - channel to inherit wave type from
            durationSeconds (float) - preview length
        outputs: dict
        '''
        with self.lock:
            if color is None:
                color = self._currentColorName()
            wave = self.instrumentMap.get(color, 0)
        try:
            sp.playNote(note=int(pitch), waves=int(wave), duration=float(durationSeconds))
        except Exception as exc:  # noqa: BLE001
            console.warn(f"playNotePreview failed: {exc}")
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def playPitch(self, pitch: int, durationSeconds: float = 0.2) -> dict:
        '''
        fields:
            pitch (int) - pitch from the pitch list
            durationSeconds (float) - preview length
        outputs: dict

        Convenience wrapper used when the user clicks anywhere in the pitch
        list. Uses the wave configured on the active color channel.
        '''
        return self.playNotePreview(int(pitch), durationSeconds=durationSeconds)

    def playFull(self, options: dict = None) -> dict:
        '''
        fields:
            options (dict) - optional {fromTime, channel, volume}
        outputs: dict

        Starts full playback at the given time and channel, replacing any
        in-flight preview/full playback.
        '''
        options = options or {}
        with self.lock:
            fromTime = float(options.get("fromTime", self.playheadHomeTime))
            channel = options.get("channel")
            if channel is None:
                channel = "all" if self.currentColorIdx == 6 else int(self.currentColorIdx)
            volume = float(options.get("volume", 0.3))
            try:
                self._activePlayObject = sp.playFull(
                    self.noteMap, self.instrumentMap, fromTime,
                    self.tempo, volume=volume, channel=channel,
                )
            except Exception as exc:  # noqa: BLE001
                console.warn(f"playFull failed: {exc}")
                return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def stopPlayback(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        try:
            if self._activePlayObject is not None:
                self._activePlayObject.stop()
        except Exception:  # noqa: BLE001
            pass
        self._activePlayObject = None
        return {"ok": True}

    def setPlayheadHome(self, time: float) -> dict:
        '''
        fields:
            time (float) - new playhead home time
        outputs: dict
        '''
        with self.lock:
            self.playheadHomeTime = float(time)
        self._notifyStateChanged()
        return {"ok": True}

    # ---- transactions ---------------------------------------------------

    def undo(self) -> dict:
        '''
        fields: none
        outputs: dict

        Performs one undo via ProjectStateManager.
        '''
        with self.lock:
            self.psm.performUndo()
        self._notifyStateChanged()
        return {"ok": True}

    def redo(self) -> dict:
        '''
        fields: none
        outputs: dict

        Performs one redo via ProjectStateManager.
        '''
        with self.lock:
            self.psm.performRedo()
        self._notifyStateChanged()
        return {"ok": True}

    # ---- temp drag list -------------------------------------------------

    def beginTempNotes(self, action: str, color: str, originals: list, targetColor: str = None) -> dict:
        '''
        fields:
            action (string) - "move" or "duplicate"
            color (string) - channel originals belong to
            originals (list) - list of {pitch, time, duration, data_fields}
            targetColor (string | None) - destination channel for proposed
                notes; defaults to ``color`` so single-channel drags stay
                backward compatible. Move drags retarget the destination
                channel when the user pressed a channel hotkey mid-drag.
        outputs: dict

        Marks the start of a drag/duplicate gesture. Frontend captures the
        original positions at mouse-down and sends them here so the backend
        can later remove the originals exactly on commit (move only).
        '''
        if action not in ("move", "duplicate"):
            return {"ok": False, "error": "InvalidAction"}
        with self.lock:
            normalizedOriginals = [self._normalizeNotePayload(n) for n in (originals or [])]
            self.tempDragState = {
                "action": action,
                "color": color,
                "targetColor": targetColor if targetColor else color,
                "originals": normalizedOriginals,
                "proposed": list(normalizedOriginals),
            }
        return {"ok": True}

    def appendTempNotes(self, notes: list) -> dict:
        '''
        fields:
            notes (list) - additional proposed notes to merge in
        outputs: dict
        '''
        with self.lock:
            if self.tempDragState is None:
                return {"ok": False, "error": "NoActiveDrag"}
            for note in (notes or []):
                self.tempDragState["proposed"].append(self._normalizeNotePayload(note))
        return {"ok": True}

    def setTempNotes(self, notes: list) -> dict:
        '''
        fields:
            notes (list) - replacement proposed notes
        outputs: dict

        Replaces the proposed positions wholesale. Sent every time the
        user drags so the backend always knows the latest preview.
        '''
        with self.lock:
            if self.tempDragState is None:
                return {"ok": False, "error": "NoActiveDrag"}
            self.tempDragState["proposed"] = [self._normalizeNotePayload(n) for n in (notes or [])]
        return {"ok": True}

    def commitTempNotes(self) -> dict:
        '''
        fields: none
        outputs: dict

        Applies the temp drag list to the document. For "move", originals
        are removed before proposed notes are inserted. For "duplicate",
        originals stay in place. A MOVE_NOTES (or NEW_NOTE) transaction is
        recorded based on net change.
        '''
        with self.lock:
            state = self.tempDragState
            self.tempDragState = None
            if state is None:
                return {"ok": False, "error": "NoActiveDrag"}

            color = state["color"]
            targetColor = state.get("targetColor", color)
            action = state["action"]
            beforeSnapshot = self.snapshotEditorState()

            sourceNotes = self.noteMap.setdefault(color, [])
            if action == "move":
                for original in state["originals"]:
                    self._removeMatchingNote(sourceNotes, original)

            destinationNotes = self.noteMap.setdefault(targetColor, [])
            for proposed in state["proposed"]:
                destinationNotes.append(deserializeNote(proposed))

            self._preprocess()

            afterSnapshot = self.snapshotEditorState()
            if beforeSnapshot != afterSnapshot:
                transactionType = "MOVE_NOTES" if action == "move" else "NEW_NOTE"
                title = "Move selection" if action == "move" else "Duplicate selection"
                self.psm.pushEditorSnapshotTransaction(transactionType, title)

        self._notifyStateChanged()
        return {"ok": True, "action": action}

    def cancelTempNotes(self) -> dict:
        '''
        fields: none
        outputs: dict

        Discards the in-flight drag without applying it.
        '''
        with self.lock:
            existed = self.tempDragState is not None
            self.tempDragState = None
        return {"ok": True, "existed": existed}

    # ---- internal helpers -----------------------------------------------

    def _currentColorName(self) -> str:
        '''
        fields: none
        outputs: string
        '''
        if 0 <= self.currentColorIdx < len(COLOR_NAMES):
            return COLOR_NAMES[self.currentColorIdx]
        return COLOR_NAMES[0]

    def _normalizeNotePayload(self, note: dict) -> dict:
        '''
        fields:
            note (dict) - JSON note payload
        outputs: dict

        Returns a sanitized copy with primitive types and a default
        ``data_fields`` map.
        '''
        return {
            "pitch": int(note["pitch"]),
            "time": float(note["time"]),
            "duration": float(note["duration"]),
            "data_fields": copy.deepcopy(note.get("data_fields", {})),
            "selected": bool(note.get("selected", False)),
        }

    def _removeMatchingNote(self, channelNotes: list, target: dict):
        '''
        fields:
            channelNotes (list) - runtime notes for one color
            target (dict) - normalized note payload to match against
        outputs: nothing

        Removes the first runtime note whose (pitch, time, duration) match
        the target payload exactly. The frontend must capture originals at
        drag start so this lookup is deterministic.
        '''
        for note in list(channelNotes):
            if (note.pitch == target["pitch"]
                    and note.time == target["time"]
                    and note.duration == target["duration"]):
                channelNotes.remove(note)
                return
