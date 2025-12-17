# file_io.py
# module for working with file saving and loading.
###### IMPORT ######

from tkinter.filedialog import asksaveasfile #, asksaveasfilename
import dill as pkl

import utils.state_loading as sl
from console_controls.console import *

###### FUNCTIONS ######

def dumpToFile(workingFile: str, destFile: str, programState: dict, process: str, autoSave: str = None, titleText: str = "", sessionID: str = ""):
    '''
    fields:
        workingFile (string) - path of the working file\n
        destFile (string) - path of the destination file\n
        programState (dict) - the existing program state to dump\n
        process (string) - the current running process type, most likely 'open'\n
        autoSave (string) - directory to autosave, if null then don't dump to autosave\n
        titleText (string) - the title text to name auto save backups\n
        sessionID (string) - the session ID to name auto save backups
    outputs: nothing

    Saves data to the working file, and also the file dir provided
    '''

    noteMap = programState["noteMap"]
    key = programState["key"]
    mode = programState["mode"]
    waveMap = programState["waveMap"]
    ticksPerTile = programState["ticksPerTile"]

    saveReadyNoteMap = sl.toSavable(noteMap)

    epochSeconds = time.time() # get current time in epoch seconds
    localTime = time.localtime(epochSeconds)
    readableTime = time.strftime('%Y-%m-%d at %H:%M:%S', localTime)

    programState = sl.newProgramState(key, mode, ticksPerTile, saveReadyNoteMap, waveMap)
    pkl.dump(programState, open(workingFile, 'wb'), -1)
    if (autoSave != None) and process == 'open':
        pkl.dump(programState, open(autoSave + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb'), -1)
        open(autoSave + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb').close()
    
    open(workingFile, 'wb').close()
    worldMessage = (f"Last Saved {readableTime} to " + destFile) if (destFile != workingFile) else "You have unsaved changes - Please save to a file on your PC."
    return worldMessage