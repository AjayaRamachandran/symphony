# editor/editor_api.py
# pywebview js_api surface for the editor window.
#
# All methods here are reachable from JavaScript as
# ``window.pywebview.api.<name>``. The thin shim in
# ``src/editor/editor-bridge.js`` re-exposes these on
# ``window.editorAPI`` for the React stub to call.
#
# Each method delegates to ``EditorSession``; this class only
# adapts the call surface and adds window-control helpers
# matching the project manager's ``Api`` so the editor frontend
# can use the same drag/resize/maximize primitives.
###### IMPORT ######

import sys
import webbrowser

###### INTERNAL MODULES ######

from console_controls.console import *

###### CLASSES ######

class EditorApi:
    '''
    pywebview js_api surface for the editor window. Methods that mutate
    document state delegate to ``EditorSession``; window controls reuse
    ``winman`` the same way the project manager's ``Api`` does.
    '''

    def __init__(self, session, getWindow, winmanModule):
        '''
        fields:
            session (EditorSession) - active editor document session
            getWindow (callable) - returns the active webview.Window or None
            winmanModule (module) - platform winman facade (or null stub)
        outputs: nothing
        '''
        self.session = session
        self._getWindow = getWindow
        self.winman = winmanModule

    # ---- platform / window controls -------------------------------------

    def getPlatform(self) -> str:
        '''
        fields: none
        outputs: string

        Returns the legacy Electron-style platform identifier so frontend
        code can branch the same way the project manager does.
        '''
        if sys.platform == "win32":
            return "win32"
        if sys.platform == "darwin":
            return "darwin"
        return "linux"

    def minimize(self) -> None:
        '''
        fields: none
        outputs: nothing
        '''
        window = self._getWindow()
        if window:
            window.minimize()

    def maximize(self) -> None:
        '''
        fields: none
        outputs: nothing

        Toggles maximize, preferring the platform-native path through
        ``winman`` to avoid covering the taskbar/dock.
        '''
        window = self._getWindow()
        if not window:
            return
        if sys.platform in ("win32", "darwin"):
            try:
                maximized = self.winman.toggle_native_maximize(window)
                if maximized is None:
                    window.maximize()
                return
            except Exception as exc:  # noqa: BLE001
                console.warn(f"editor maximize via winman failed: {exc}")
        try:
            if getattr(window, "maximized", False):
                window.restore()
            else:
                window.maximize()
        except Exception:  # noqa: BLE001
            window.maximize()

    def close(self) -> None:
        '''
        fields: none
        outputs: nothing
        '''
        window = self._getWindow()
        if window:
            window.destroy()

    def toggleDevtools(self) -> None:
        '''
        fields: none
        outputs: nothing
        '''
        if getattr(sys, "frozen", False):
            return
        window = self._getWindow()
        if not window:
            return
        try:
            window.show_inspector()
        except Exception:  # noqa: BLE001
            pass

    def openExternalUrl(self, url: str) -> bool:
        '''
        fields:
            url (string) - external URL to open in the user's browser
        outputs: boolean
        '''
        try:
            return bool(webbrowser.open(str(url)))
        except Exception as exc:  # noqa: BLE001
            console.warn(f"openExternalUrl failed: {exc}")
            return False

    def startWindowResize(self, edge: str) -> bool:
        '''
        fields:
            edge (string) - resize edge name from the JS handle
        outputs: boolean
        '''
        window = self._getWindow()
        if not window:
            return False
        try:
            return bool(self.winman.start_resize(window, edge))
        except Exception as exc:  # noqa: BLE001
            console.warn(f"startWindowResize failed: {exc}")
            return False

    def beginManualWindowResize(self, edge: str, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            edge (string) - resize edge name
            screen_x (int) - initial pointer X in screen coords
            screen_y (int) - initial pointer Y in screen coords
        outputs: boolean
        '''
        window = self._getWindow()
        if not window:
            return False
        try:
            return bool(self.winman.begin_manual_resize(window, edge, screen_x, screen_y))
        except Exception as exc:  # noqa: BLE001
            console.warn(f"beginManualWindowResize failed: {exc}")
            return False

    def updateManualWindowResize(self, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            screen_x (int) - pointer X in screen coords
            screen_y (int) - pointer Y in screen coords
        outputs: boolean
        '''
        window = self._getWindow()
        if not window:
            return False
        try:
            return bool(self.winman.update_manual_resize(window, screen_x, screen_y))
        except Exception as exc:  # noqa: BLE001
            console.warn(f"updateManualWindowResize failed: {exc}")
            return False

    def endManualWindowResize(self) -> None:
        '''
        fields: none
        outputs: nothing
        '''
        window = self._getWindow()
        if not window:
            return
        try:
            self.winman.end_manual_resize(window)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"endManualWindowResize failed: {exc}")

    # ---- document state -------------------------------------------------

    def getDocumentState(self) -> dict:
        '''
        fields: none
        outputs: dict

        Returns a JSON-friendly editor snapshot.
        '''
        return self.session.getDocumentState()

    def saveNow(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        self.session.saveNow()
        return {"ok": True}

    # ---- note edits -----------------------------------------------------

    def drawNote(self, color: str, note: dict) -> dict:
        '''
        fields:
            color (string) - target channel
            note (dict) - note payload
        outputs: dict
        '''
        return self.session.drawNote(color, note)

    def eraseNoteAt(self, color: str, time, pitch: int) -> dict:
        '''
        fields:
            color (string) - target channel
            time (number) - grid time
            pitch (int) - grid pitch
        outputs: dict
        '''
        return self.session.eraseNoteAt(color, time, pitch)

    def setSelection(self, selection: list) -> dict:
        '''
        fields:
            selection (list) - {color, time, pitch} entries
        outputs: dict
        '''
        return self.session.setSelection(selection)

    def clearSelection(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.clearSelection()

    def deleteSelectedNotes(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.deleteSelectedNotes()

    # ---- metadata / settings -------------------------------------------

    def setAccidentals(self, mode: str) -> dict:
        '''
        fields:
            mode (string) - "flats" or "sharps"
        outputs: dict
        '''
        return self.session.setAccidentals(mode)

    def setBeatLength(self, value: int) -> dict:
        '''
        fields:
            value (int)
        outputs: dict
        '''
        return self.session.setBeatLength(value)

    def setBeatsPerMeasure(self, value: int) -> dict:
        '''
        fields:
            value (int)
        outputs: dict
        '''
        return self.session.setBeatsPerMeasure(value)

    def setTempo(self, value: int) -> dict:
        '''
        fields:
            value (int)
        outputs: dict
        '''
        return self.session.setTempo(value)

    def setKey(self, key: str) -> dict:
        '''
        fields:
            key (string)
        outputs: dict
        '''
        return self.session.setKey(key)

    def setMode(self, mode: str) -> dict:
        '''
        fields:
            mode (string)
        outputs: dict
        '''
        return self.session.setMode(mode)

    def setActiveColor(self, colorIdx: int) -> dict:
        '''
        fields:
            colorIdx (int)
        outputs: dict
        '''
        return self.session.setActiveColor(colorIdx)

    def setWaveType(self, color: str, waveIdx: int) -> dict:
        '''
        fields:
            color (string)
            waveIdx (int)
        outputs: dict
        '''
        return self.session.setWaveType(color, waveIdx)

    def updateProjectMetadata(self, metadata: dict) -> dict:
        '''
        fields:
            metadata (dict)
        outputs: dict
        '''
        return self.session.updateProjectMetadata(metadata)

    # ---- audio ----------------------------------------------------------

    def playNotePreview(self, pitch: int, color: str = None, durationSeconds: float = 0.2) -> dict:
        '''
        fields:
            pitch (int)
            color (string | None)
            durationSeconds (float)
        outputs: dict
        '''
        return self.session.playNotePreview(pitch, color, durationSeconds)

    def playPitch(self, pitch: int, durationSeconds: float = 0.2) -> dict:
        '''
        fields:
            pitch (int)
            durationSeconds (float)
        outputs: dict
        '''
        return self.session.playPitch(pitch, durationSeconds)

    def playFull(self, options: dict = None) -> dict:
        '''
        fields:
            options (dict | None)
        outputs: dict
        '''
        return self.session.playFull(options)

    def stopPlayback(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.stopPlayback()

    def setPlayheadHome(self, time) -> dict:
        '''
        fields:
            time (number)
        outputs: dict
        '''
        return self.session.setPlayheadHome(time)

    # ---- transactions ---------------------------------------------------

    def undo(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.undo()

    def redo(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.redo()

    # ---- temp drag list -------------------------------------------------

    def beginTempNotes(self, action: str, color: str, originals: list, targetColor: str = None) -> dict:
        '''
        fields:
            action (string)
            color (string)
            originals (list)
            targetColor (string | None)
        outputs: dict
        '''
        return self.session.beginTempNotes(action, color, originals, targetColor)

    def appendTempNotes(self, notes: list) -> dict:
        '''
        fields:
            notes (list)
        outputs: dict
        '''
        return self.session.appendTempNotes(notes)

    def setTempNotes(self, notes: list) -> dict:
        '''
        fields:
            notes (list)
        outputs: dict
        '''
        return self.session.setTempNotes(notes)

    def commitTempNotes(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.commitTempNotes()

    def cancelTempNotes(self) -> dict:
        '''
        fields: none
        outputs: dict
        '''
        return self.session.cancelTempNotes()
