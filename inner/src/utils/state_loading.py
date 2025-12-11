# state_loading.py
# module for handling state saving / loading and backwards compatibility.
###### IMPORT ######

import copy

###### INTERNAL MODULES ######

from console_controls.console import *
from gui_pygame import Note
import values as v

###### METHODS / CLASSES ######

def toNote(note: Note):
    '''Function to convert old notes (before color was added) into new color'''
    try:
        color = note.color
    except:
        console.warn('Adapting old note to have color \'orange\'.')
        color = "orange"
    return Note(note.key, note.time, note.lead, color)

class ProgramState():
    '''Class to contain the entire editor's state, with all relevant fields for opening and saving.'''

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

def toProgramState(state : ProgramState):
    '''Maps a (potentially) old program state to a new one for backwards compatibility'''
    try:
        stateMkey = state.key
    except:
        console.warn('Adapting old file format to have key Eb.')
        stateMkey = "Eb"

    try:
        statemode = state.mode
    except:
        console.warn('Adapting old file format to have mode Lydian.')
        statemode = "Lydian"

    try:
        stateWaves = state.waveMap
    except:
        console.warn('Adapting old file format to have waveMap.')
        stateWaves = {
            "orange" : 0,
            "purple" : 0,
            "cyan" : 0,
            "lime" : 0,
            "blue" : 0,
            "pink" : 0,
            "all" : 0
        }

    newNoteMap = {}
    for statekey, stateval in state.noteMap.items():
        newKey = statekey
        if len(statekey) != 3:
            newKey = (*statekey, "orange")
        newNoteMap[newKey] = toNote(stateval)

    return ProgramState(state.ticksPerTile, newNoteMap, stateMkey, statemode, stateWaves)

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
            strikeList.append({"pitch": note.key + 35, "startTime": ((note.time - 1) / 4), "duration": (offset / 4)})
    
    return strikeList

def migrate_to_1_1(ProgramState):
    None