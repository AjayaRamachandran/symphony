# file_io.py
# module for working with file saving and loading.
###### IMPORT ######

from tkinter.filedialog import asksaveasfile #, asksaveasfilename
import dill as pkl

import values as v
from console_controls.console import *

###### FUNCTIONS ######

def dumpToFile(file, directory):
    '''
    fields:
        file (string) - path of the working file
        directory (string) - path of the destination file
    outputs: nothing

    Saves data to the working file, used in many places in the code
    '''

    # when saving, repair any discrepancies between hashmap key and obj data (rare but fatal)
    delQ, addQ = [], []
    for thing in v.noteMap.items():
        if (thing[1].key, thing[1].time, thing[1].color) != thing[0]:
            console.log("A discrepancy was found between hashmap and obj data. Repairing (prioritizing obj data) now...")
            console.log(f"Discrepancy details -- HM Key: {thing[0]}, Obj Data: {(thing[1].key, thing[1].time, thing[1].color)}")
            addQ.append([(thing[1].key, thing[1].time, thing[1].color), thing[1]])
            delQ.append(thing[0])
        
        if (thing[1].key < 2):
            delQ.append(thing[0])
    for item in delQ:
        del v.noteMap[item]
    for item in addQ:
        v.noteMap[item[0]] = item[1]

    epochSeconds = time.time() # get current time in epoch seconds
    localTime = time.localtime(epochSeconds)
    readableTime = time.strftime('%Y-%m-%d at %H:%M:%S', localTime)

    v.ps.updateAttributes(v.noteMap, v.ticksPerTile, v.key, v.mode, v.waveMap)
    pkl.dump(v.ps, file, -1)
    if v.autoSave and v.process == 'open' and (v.autoSaveDirectory != None):
        pkl.dump(v.ps, open(v.autoSaveDirectory + '/' + v.titleText + ' Backup ' + v.sessionID + '.symphony', 'wb'), -1)

    v.worldMessage = (f"Last Saved {readableTime} to " + directory) if directory != f"{v.source_path}/assets/workingfile.symphony" else "You have unsaved changes - Please save to a file on your PC."


def promptSave():
    '''
    fields: none
    outputs: nothing

    Prompts the user to save their work
    '''

    filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
    if filename != None:
        myPath = open(f"{v.source_path}/assets/workingfile.symphony", "wb")

        dumpToFile(myPath, directory=f"{v.source_path}/assets/workingfile.symphony")
        myPath = open(f"{v.source_path}/assets/workingfile.symphony", "rb")

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()