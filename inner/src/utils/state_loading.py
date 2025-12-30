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

DEFAULT_META_FIELD = {
    "version" : "1.1",
    "plugins" : []
}

###### METHODS / CLASSES ######

def newProgramState(key : str, mode : str, tpm : int, noteMap : dict, waveMap : dict, beatLength : int, beatsPerMeasure : int):
    return {
        "meta" : DEFAULT_META_FIELD,
        "key" : key,
        "mode" : mode,
        "tpm" : tpm,
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

    if isinstance(state, dict):
        stateMeta = state.get("meta", DEFAULT_META_FIELD)
        stateKey = state.get("key", "Eb")
        stateMode = state.get("mode", "Lydian")
        stateTpm = state.get("tpm", 360)
        stateWaves = state.get("waveMap", DEFAULT_WAVE_MAP)
        newNoteMap = fromSavable(state.get("noteMap", {})) # load from dict back into note format
        stateBeatLength = state.get("beatLength", 4)
        stateBeatsPerMeasure = state.get("beatsPerMeasure", 4)
    else:
        # ProgramState is older than the "meta" field -- no need to check here
        stateMeta = DEFAULT_META_FIELD
        stateKey = getattr(state, "key", "Eb")
        stateMode = getattr(state, "mode", "Lydian")
        stateWaves = getattr(state, "waveMap", getattr(state, "wavemap", DEFAULT_WAVE_MAP))
        stateTpm = 3600 / getattr(state, "ticksPerTile", 10) # Migration of ticksPerTile to tpm storage in 1.1+
        stateBeatLength = 4 # ProgramState is also older than BeatLength being stored in the file
        stateBeatsPerMeasure = 4 # ProgramState is also older than BeatsPerMeasure being stored in the file

        newNoteMap = getattr(state, "noteMap", {})
        newNoteMap = noteMap1_0To1_1(newNoteMap)

    return {
        "meta" : stateMeta,
        "tpm": stateTpm,
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
                    if noteMap[(note.key, note.time + offset, color)].lead: # if a new note starts, stop incrementing
                        break
                    offset += 1
                strikeList.append(Note({
                    "pitch" : note.key,
                    "time": note.time - 1,
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

def fromSavable(noteMap: dict):
    '''
    fields:
        noteMap (dict) - note map in pickle-ready 1.1 notation
    
    Converts an active noteMap FROM save-ready format (dict -> Note).
    Note: this method is repeat-safe; if input is already Note-format, nothing should break.
    '''
    output = {}
    for color, notes in noteMap.items():
        channel = []
        for note in notes:
            if isinstance(note, Note):
                channel.append(note)
            elif isinstance(note, dict):
                channel.append(Note(note))
            else:
                raise ValueError('invalid note type')
        output[color] = channel
    return output