# utils/file_io.py
# module for working with file saving and loading.
###### IMPORT ######

import dill as pkl

###### INTERNAL MODULES ######

import utils.state_loading as sl
from console_controls.console import *

###### FUNCTIONS ######

def dumpToFile(workingFile: str, destFile: str, programState: dict, autoSave: str = None, titleText: str = "", sessionID: str = ""):
    '''
    fields:
        workingFile (string) - path of the working file\n
        destFile (string) - path of the destination file\n
        programState (dict) - the existing program state to dump\n
        autoSave (string) - directory to autosave, if null then don't dump to autosave\n
        titleText (string) - the title text to name auto save backups\n
        sessionID (string) - the session ID to name auto save backups\n
    outputs: string (the updated worldMessage)

    Saves data to the working file, and also the file dir provided
    '''

    noteMap = programState["noteMap"]
    key = programState["key"]
    mode = programState["mode"]
    waveMap = programState["waveMap"]
    tpm = programState["tpm"]
    beatLength = programState["beatLength"]
    beatsPerMeasure = programState["beatsPerMeasure"]

    saveReadyNoteMap = sl.toSavable(noteMap)

    epochSeconds = time.time() # get current time in epoch seconds
    localTime = time.localtime(epochSeconds)
    readableTime = time.strftime('%Y-%m-%d at %H:%M:%S', localTime)

    programState = sl.newProgramState(key, mode, tpm, saveReadyNoteMap, waveMap, beatLength, beatsPerMeasure)

    with open(workingFile, 'wb') as file:
        pkl.dump(programState, file, -1)

    if (autoSave):
        with open(autoSave + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb') as auto_save_file:
            pkl.dump(programState, auto_save_file, -1)
    
    worldMessage = (f"Last Saved {readableTime} to " + destFile) if (destFile != workingFile) else "You have unsaved changes - Please save to a file on your PC."
    return worldMessage

def simpleDump(filePath: str, programState: dict):
    '''
    fields:
        filePath (string) - path of the file\n
        programState (dict) - the existing program state to dump\n
    outputs: nothing

    Saves data to the provided file
    '''

    noteMap = programState["noteMap"]
    key = programState["key"]
    mode = programState["mode"]
    waveMap = programState["waveMap"]
    tpm = programState["tpm"]
    beatLength = programState["beatLength"]
    beatsPerMeasure = programState["beatsPerMeasure"]

    saveReadyNoteMap = sl.toSavable(noteMap)
    programState = sl.newProgramState(key, mode, tpm, saveReadyNoteMap, waveMap, beatLength, beatsPerMeasure)

    with open(filePath, 'wb') as file:
        pkl.dump(programState, file, -1)