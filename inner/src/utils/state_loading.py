# utils/state_loading.py
# module for handling state saving / loading and backwards compatibility.
###### IMPORT ######

import copy

###### INTERNAL MODULES ######

from console_controls.console import *
from gui.custom import Note

###### INITIALIZE ######

DEFAULT_WAVE_MAP = {
    "orange": 0,
    "purple": 0,
    "cyan": 0,
    "lime": 0,
    "blue": 0,
    "pink": 0,
    "all": 0,
}

###### METHODS / CLASSES ######

class ProgramState():
    '''
    LEGACY
    Class to contain the entire editor's state, with all relevant fields for opening and saving.
    '''

    def __init__(self, ticksPerTile, noteMap, key, mode, waves):
        self.ticksPerTile = ticksPerTile
        self.noteMap = noteMap
        self.key = key
        self.mode = mode
        self.waveMap = waves

    def updateAttributes(self, noteMap, ticksPerTile, key, mode, waves):
        self.noteMap = copy.deepcopy(noteMap)
        self.ticksPerTile = ticksPerTile
        self.key = key
        self.mode = mode
        self.waveMap = waves
        console.log(f"Updated ProgramState with key {key} and mode {mode}.")

def newProgramState(key : str, mode : str, ticksPerTile : int, noteMap : dict, waveMap : dict, beatLength : int, beatsPerMeasure : int):
    return {
        "key" : key,
        "mode" : mode,
        "ticksPerTile" : ticksPerTile,
        "noteMap" : noteMap,
        "waveMap" : waveMap,
        "beatLength" : beatLength,
        "beatsPerMeasure" : beatsPerMeasure,
    }

def toProgramState(state):
    '''
    fields:
        state (ProgramState | dict) - potentially old program state
    outputs: dict

    Maps a (potentially) old program state to a new one for backwards compatibility.
    1.1 and beyond use a map for the program state because it is more extensible than a ProgramState object
    Older ProgramState objects (and future objects) are converted into a dict, so all code can now treat them as such
    '''

    DEFAULT_META_FIELD = {
        "version" : "1.1",
        "plugins" : []
    }

    if isinstance(state, ProgramState):
        # ProgramState is older than the "meta" field -- no need to check here
        stateMeta = DEFAULT_META_FIELD
        stateKey = getattr(state, "key", "Eb")
        stateMode = getattr(state, "mode", "Lydian")
        stateWaves = state.get("waveMap", state.get("wavemap", DEFAULT_WAVE_MAP))
        stateTicksPerTile = getattr(state, "ticksPerTile", 10)
        stateBeatLength = 4 # ProgramState is also older than BeatLength being stored in the file
        stateBeatsPerMeasure = 4 # ProgramState is also older than BeatsPerMeasure being stored in the file

        # convert noteMap with backwards-compatibility normalization
        rawNoteMap = getattr(state, "noteMap", {})
        newNoteMap = {}
        for noteKey, noteVal in rawNoteMap.items():
            # ensure key is 3-tuple (not necessary anymore, but we keep because it works)
            if len(noteKey) != 3:
                noteKey = (*noteKey, "orange")
            newNoteMap[noteKey] = noteVal
            # used to be toNote(noteVal), but we removed Note() object, so REALLY old beta files might not work
            # however, I don't even think such beta files exist on any computer of mine
            # so we could potentially remove "<1.0 to 1.0" conversion and just keep 1.0->1.1 migration

        # successfully in 1.0 format, now migrate to 1.1
        newNoteMap = noteMap1_0To1_1(newNoteMap)

    elif isinstance(state, dict):
        stateMeta = state.get("meta", DEFAULT_META_FIELD)
        stateKey = state.get("key", "Eb")
        stateMode = state.get("mode", "Lydian")
        stateTicksPerTile = state.get("ticksPerTile", 10)
        stateWaves = state.get("waveMap", DEFAULT_WAVE_MAP)
        newNoteMap = state.get("noteMap", {})
        stateBeatLength = state.get("beatLength", 4)
        stateBeatsPerMeasure = state.get("beatsPerMeasure", 4)
    else:
        raise TypeError("state must be a ProgramState or dict")

    return {
        "meta" : stateMeta,
        "ticksPerTile": stateTicksPerTile,
        "noteMap": newNoteMap,
        "key": stateKey,
        "mode": stateMode,
        "waveMap": stateWaves,
        "beatLength": stateBeatLength,
        "beatsPerMeasure": stateBeatsPerMeasure,
    }


def convertNoteMapToStrikeList(noteMap):
    '''
    ### Legacy -- do not use with new (1.1+) noteMap encoding.

    fields:
        noteMap (hash map) - note map in 1.0 encoding
    outputs: list

    Converts the legacy noteMap into a list of notes encoded by their duration and time of strike.
    '''
    strikeList = []
    for el, note in noteMap.items():
        if note.lead:
            offset = 1
            while (note.key, note.time + offset, note.color) in noteMap:
                offset += 1
            strikeList.append({"pitch": note.key + 23, "startTime": ((note.time - 1) / 4), "duration": (offset / 4)})
    
    return strikeList


def noteMap1_0To1_1(noteMap : dict):
    '''
    fields:
        noteMap (hash map) - note map in 1.0 encoding
    outputs: hash map

    Converts the 1.0 noteMap into 1.1 format.
    '''
    newNoteMap = {}
    for color, count in DEFAULT_WAVE_MAP.items():
        strikeList = []
        for el, note in noteMap.items():
            if (note.lead and note.color == color):
                offset = 1
                while (note.key, note.time + offset, color) in noteMap:
                    offset += 1
                strikeList.append(Note({
                    "pitch" : note.key,
                    "time": note.time,
                    "duration": offset,
                    "data_fields": {}
                }))
        newNoteMap[color] = strikeList
        
    return newNoteMap

def toSavable(noteMap: dict):
    '''
    fields:
        noteMap (dict) - note map in 1.1 notation
    
    Converts an active noteMap into save-ready format (Note -> dict).
    Note: this method is repeat-safe; if input is already save-ready, nothing should break.
    '''
    output = {}
    for color, notes in noteMap.items():
        channel = []
        for note in notes:
            if isinstance(note, Note):
                channel.append(note.getData())
            elif isinstance(note, dict):
                channel.append(note)
            else:
                raise ValueError('invalid note type')
        output[color] = channel
    return output