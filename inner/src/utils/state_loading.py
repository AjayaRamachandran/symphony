# state_loading.py
# module for handling state saving / loading and backwards compatibility.
###### IMPORT ######

import copy

###### INTERNAL MODULES ######

from console_controls.console import *
#from gui_pygame import Note

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

def toNote(note):#: Note):
    '''
    fields:
        note (gui.Note) - note to update
    outputs: gui.Note

    Function to convert old notes (before color was added) into new color
    '''
    try:
        color = note.color
    except:
        console.warn('Adapting old note to have color \'orange\'.')
        color = "orange"
    #return Note(note.key, note.time, note.lead, color)

def newProgramState(key : str, mode : str, ticksPerTile : int, noteMap : dict, waveMap : dict):
    return {
        "key" : key,
        "mode" : mode,
        "ticksPerTile" : ticksPerTile,
        "noteMap" : noteMap,
        "waveMap" : waveMap
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

        # convert noteMap with backwards-compatibility normalization
        rawNoteMap = getattr(state, "noteMap", {})
        newNoteMap = {}
        for noteKey, noteVal in rawNoteMap.items():
            # ensure key is 3-tuple (very old format might not include color)
            if len(noteKey) != 3:
                noteKey = (*noteKey, "orange")
            newNoteMap[noteKey] = toNote(noteVal)
        # successfully in 1.0 format, now migrate to 1.1
        newNoteMap = noteMap1_0To1_1(newNoteMap)

    elif isinstance(state, dict):
        stateMeta = state.get("meta", DEFAULT_META_FIELD)
        stateKey = state.get("key", "Eb")
        stateMode = state.get("mode", "Lydian")
        stateTicksPerTile = state.get("ticksPerTile", 10)
        stateWaves = state.get("waveMap", DEFAULT_WAVE_MAP)
        newNoteMap = state.get("noteMap", {})
    else:
        raise TypeError("state must be a ProgramState or dict")

    return {
        "meta" : stateMeta,
        "ticksPerTile": stateTicksPerTile,
        "noteMap": newNoteMap,
        "key": stateKey,
        "mode": stateMode,
        "waveMap": stateWaves,
    }


def convertNoteMapToStrikeList(noteMap):
    '''
    fields:
        noteMap (hash map) - note map in standard encoding
    outputs: list

    Converts the noteMap into a list of notes encoded by their duration and time of strike.
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

    Converts the 1.0 noteMap into 1.1 notation (similar to a map of strike lists, but different).
    '''
    newNoteMap = {}
    for color, count in DEFAULT_WAVE_MAP.items():
        strikeList = []
        for el, note in noteMap.items():
            if (note.lead and note.color == color):
                offset = 1
                while (note.key, note.time + offset, color) in noteMap:
                    offset += 1
                strikeList.append({
                    "pitch" : note.key,
                    "time": note.time,
                    "duration": offset,
                    "data_fields": {}
                })
        newNoteMap[color] = strikeList
        
    return newNoteMap