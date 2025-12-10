# main.py
# entry point for the program.
###### IMPORT ######

import pygame
from io import BytesIO
import numpy as np
import copy
import cv2
from math import *
import time
import os
import sys
import dill as pkl
from tkinter.filedialog import asksaveasfile #, asksaveasfilename
import json

lastTime = time.time()
START_TIME = lastTime

###### INTERNAL MODULES ######

import console_controls.console_window as cw
import utils.sound_processing as sp
from gui_pygame import *
from console_controls.console import *
import values as v
import utils.state_loading as sl

###### PLATFORM DETECTION ######

if sys.platform.startswith("win"):
    console.log("Running on Windows")
    platform = 'windows'
    CMD_KEY = pygame.K_LCTRL
elif sys.platform == "darwin":
    console.log("Running on macOS")
    platform = 'mac'
    CMD_KEY = pygame.K_LMETA
elif sys.platform.startswith("linux"):
    console.log("Running on Linux")
    platform = 'linux'
    CMD_KEY = pygame.K_LCTRL
else:
    console.warn(f"Running on unknown platform: {sys.platform}")
    platform = 'unknown'
    CMD_KEY = pygame.K_LCTRL

try:
    from ctypes import windll
    myappid = 'nimbial.symphony.editor.v1-0' # arbitrary string
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    console.warn('Error importing windll or setting Unique AppID. You might be running on a non-Windows platform.')
    pass # Not on Windows or ctypes is not available

####### SYSARG HANDLING ######

'''
SET ARGUMENTS:
"main.py" "open" "filename" "folder" [src_folder] [autosave_dir_path] [user_settings_path]: starts program, opening file and establishing autosave bridge. Only 'open' requires autosave_dir_path and user_settings_path.
"main.py" "instantiate" "filename" "folder" [src_folder]: does not start pygame, simply creates the file in the provided folder and exits
"main.py" "retrieve" "filepath" "id" [src_folder] [user_data_path]: gets all information about program and puts it into the json with the id, writes response.json to user_data_path if provided, else to src_folder
"main.py" "export" "filepath" "folder" [src_folder]: exports the file into the provided folder as a .wav
"main.py" "convert" "filepath" "folder" [src_folder]: exports the file into the provided folder as a .mid

"main.py" "filename": opens file with autosave bridge
"main.py": starts program without autosave (NOT RECOMMENDED)

autosave_dir_path: absolute path to the autosave directory.json file (required only for 'open')
user_settings_path: absolute path to the user-settings.json file (required only for 'open')
user_data_path: absolute path to the user data directory (used for retrieve)
'''
def cleanse(string):
    '''
    fields:
        string (string) - the string to cleanse
    outputs: string
    
    removes all non-acceptable characters from a string.
    '''
    stringCopy = string
    for l in range(len(stringCopy)):
        if not stringCopy[l] in 'abcdefghijklmnopqrstuvwxyzABCEDFGHIJKLMNOPQRSTUVWXYZ1234567890-_+(). ':
            stringCopy = stringCopy[:l] + '_' + stringCopy[l+1:]
    return stringCopy

def get_arg_path(arg_index, default_relative):
    '''
    fields:
        arg_index (string) - the index of the sysarg
        default_relative (string) - the relpath to default to
    outputs: string

    gets a number sysarg, if it does not exist returns default's abspath
    '''
    if len(sys.argv) > arg_index:
        return sys.argv[arg_index]
    return os.path.abspath(default_relative)

autoSaveDirectory = None
user_settings_path = None
directory_json_path = None

titleText = 'My Track 1'
process = ''
autoSave = True
globalUUID = 0
sessionID = time.strftime('%Y-%m-%d %H%M%S')
console.log(f'Running with sysargv: {sys.argv}')

process = 'open'

if len(sys.argv) > 7:
    console.error("Wrong usage: Too many arguments!")
    sys.exit(1)
if len(sys.argv) >= 5:
    if sys.argv[1] == 'export' or sys.argv[1] == 'convert':
        process = sys.argv[1]
        workingFile = sys.argv[2]
        destination = sys.argv[3]
    elif sys.argv[1] == 'retrieve':
        process = sys.argv[1]
        workingFile = sys.argv[2]
        globalUUID = sys.argv[3]
    else:
        process = sys.argv[1]
        workingFile = sys.argv[3] + '/' + sys.argv[2] # used to cleanse sysargv 2, but realized this can actually cause errors
        titleText = sys.argv[2][:-9]
        if process == 'open':
            if process == 'open' and user_settings_path:
                autoSave = not json.load(open(user_settings_path))["disable_auto_save"]
            #import threading
elif len(sys.argv) == 2:
    #import threading
    workingFile = sys.argv[1]
    console.warn('You are running Symphony without the Project Manager. This can lead to poor file safety and potential project loss.')
else:
    #import threading
    workingFile = ""
    console.warn('You are running Symphony without the Project Manager. This can lead to poor file safety and potential project loss.')
    console.warn('You are running Symphony without a designated autosave destination. We highly recommend against this.')

if process == 'open' and len(sys.argv) == 7:
    v.source_path = get_arg_path(4, 'assets/directory.json')
    directory_json_path = get_arg_path(5, 'assets/directory.json')
    user_settings_path = get_arg_path(6, 'assets/user-settings.json')
    autoSaveDirectory = json.load(open(directory_json_path))['Symphony Auto-Save'][0]['Auto-Save']

show_console = False
if process == 'open' and user_settings_path:
    show_console = json.load(open(user_settings_path))["show_console"]
    if show_console:
        try:
            userName = json.load(open(user_settings_path))["user_name"].split(sep=' ')[0]
        except Exception:
            userName = 'User'
        console.message(f'Hey, {userName}! This console can be safely closed at any time, and your editor will remain active.')

###### PYGAME & WINDOW INITIALIZE ######

if process in ['instantiate', 'retrieve', 'export', 'convert']:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

console.log("Initialized Args "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

minWidth, minHeight = (925, 592)
iconPath = f'{v.source_path}/assets/icon32x32.png'
if os.path.exists(iconPath):
    gameIcon = pygame.image.load(iconPath)
    pygame.display.set_icon(gameIcon)
else:
    console.warn(f"Warning: Icon file not found at {iconPath}")

console.log("Initialized Icon Path "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

pygame.display.init()
pygame.font.init()
pygame.mixer.init()

console.log("Initialized Pygame "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

pygame.display.set_caption(f"{titleText} - Symphony v1.0 Beta")
#pygame.display.set_icon(pygame.image.load(f"{v.source_path}/icon.png"))
v.screen = pygame.display.set_mode((v.width, v.height), pygame.RESIZABLE, pygame.NOFRAME)

if (process == 'instantiate') or (process == 'retrieve'):
    None
else:
    pygame.display.flip()
    pygame.event.pump()
    time.sleep(0.1)

console.log("Initialized Window "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

pygame.mixer.init(frequency=v.SAMPLE_RATE, size=-16, channels=2)  # initialize pygame. mixer at module import

transparentScreen = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
otherNotes = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
thisNote = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrOrange = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrPurple = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrCyan = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrLime = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrBlue = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrPink = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]
clock = pygame.time.Clock()
fps = 60

###### ASSETS ######

if process == 'open':

    bytes_io = BytesIO()

    console.log("Initialized Classes "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
    lastTime = time.time()


    playImage = pygame.image.load(f"{v.source_path}/assets/play.png")
    pauseImage = pygame.image.load(f"{v.source_path}/assets/pause.png")
    headImage = pygame.image.load(f"{v.source_path}/assets/head.png")
    brushImage = pygame.image.load(f"{v.source_path}/assets/brush.png")
    eraserImage = pygame.image.load(f"{v.source_path}/assets/eraser.png")
    negaterImage = pygame.image.load(f"{v.source_path}/assets/negater.png")
    rainbowImage = pygame.image.load(f"{v.source_path}/assets/rainbow.png")

    squareWaveImage = pygame.image.load(f"{v.source_path}/assets/square.png")
    sawtoothWaveImage = pygame.image.load(f"{v.source_path}/assets/sawtooth.png")
    triangleWaveImage = pygame.image.load(f"{v.source_path}/assets/triangle.png")
    waveImages = [squareWaveImage, triangleWaveImage, sawtoothWaveImage]

    upChevronImage = pygame.image.load(f"{v.source_path}/assets/up.png")
    downChevronImage = pygame.image.load(f"{v.source_path}/assets/down.png")
else:
    v.TITLE1 = ''
    v.HEADING1 = ''
    v.SUBHEADING1 = ''
    v.BODY = ''
    v.SUBSCRIPT1 = ''

console.log("Initialized Assets "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PROGRAM STATE INITIALIZE ######

if workingFile == "" or process == 'instantiate': # if the workingfile is not provided or we are creating a new file, initialize a new program state
    ps = sl.ProgramState(10, v.noteMap, "Eb", "Lydian", v.waveMap)
    console.log('Creating new programState...')
else:
    ps = sl.toProgramState(pkl.load(open(workingFile, "rb")))
    console.log('Loading existing programState...')

if process == 'retrieve' and len(sys.argv) >= 5:
    filepath = sys.argv[2]
    id_val = sys.argv[3]
    src_folder = sys.argv[4]
    user_data_path = sys.argv[5] if len(sys.argv) >= 6 else None

    response_path = os.path.join(user_data_path if user_data_path else src_folder, 'response.json')
    with open(response_path, 'w') as f:
        console.log('DUMPING INTO RESPONSE.JSON')
        console.log(os.path.join(user_data_path, 'response.json'))
        #console.log(ps.noteMap)
        tpm = round(3600 / ps.ticksPerTile, 2)
        tiles = int((max(ps.noteMap.items(), key=lambda x : x[0][1]))[0][1]) if (len(ps.noteMap.items()) > 0) else 0
        json.dump({ 'fileInfo' : {
                    'Key' : ps.key,
                    'Mode' : ps.mode,
                    'Tempo (tpm)' : tpm,
                    #'Empty?' : (ps.noteMap == {}),
                    'Length (tiles)' : tiles,
                    'Duration' : ("0" if len(str(floor(tiles / tpm))) == 1 else '') + str(floor(tiles / tpm)) + ':' + ("0" if len(str(round(((tiles / tpm) % 1) * 60))) == 1 else '') + str(round(((tiles / tpm) % 1) * 60))
                    }, 'id': globalUUID
                }, f)
        f.close()
    sys.exit()

console.log("Initialized ProgramState "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### VARIABLE & GUI ELEMENT SETUP ######

v.noteMap = ps.noteMap
v.ticksPerTile = ps.ticksPerTile
v.waveMap = ps.waveMap
key = ps.key
if "b" in key:
    keyIndex = v.NOTES_FLAT.index(key)
    v.accidentals = "flats"
else:
    keyIndex = v.NOTES_SHARP.index(key)
    v.accidentals = "sharps"
mode = ps.mode
modeIntervals = set(v.modesIntervals[0][1])

playPauseButton = Button(pos=(33, 40), width=60, height=28)
accidentalsButton = Button(pos=(120, 40), width=60, height=28)
playheadButton = Button(pos=(207, 40), width=60, height=28)
keyButton = Button(pos=(v.width - 260, 40), width=40, height=28)
modeButton = Button(pos=(v.width - 220, 40), width=100, height=28)
brushButton = Button(pos=(v.width - 93, 40), width=60, height=28)
waveButton = Button(pos=(v.width - 317, 40), width=28, height=28)

timeSigDownButton = Button(pos=(v.width - 420, 40), width=20, height=28)
timeSigTextBox = TextBox(pos=(v.width - 400, 40), width=30, height=28, text='4')
timeSigUpButton = Button(pos=(v.width - 370, 40), width=20, height=28)
tempoDownButton = Button(pos=(300, 40), width=20, height=28)
tempoTextBox = TextBox(pos=(320, 40), width=105, height=28, text='360', endBarOffset=4)
tempoUpButton = Button(pos=(425, 40), width=20, height=28)

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

    ps.updateAttributes(v.noteMap, v.ticksPerTile, key, mode, v.waveMap)
    pkl.dump(ps, file, -1)
    if autoSave and process == 'open' and (autoSaveDirectory != None):
        pkl.dump(ps, open(autoSaveDirectory + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb'), -1)

    v.worldMessage = (f"Last Saved {readableTime} to " + directory) if directory != f"{v.source_path}/assets/workingfile.symphony" else "You have unsaved changes - Please save to a file on your PC."

if process == 'instantiate':
    dumpToFile(open(workingFile, 'wb'), workingFile)
    sys.exit()

def inBounds(coords1, coords2, point) -> bool:
    '''
    fields:
        coords1 (pair[number]) - first coordinate
        coords2 (pair[number]) - second coordinate
        point (pair[number]) - point to check
    outputs: boolean

    Returns whether a point is within the bounds of two other points. order of coords is arbitrary.
    '''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def processImage(imageBytes):
    '''
    fields:
        imageBytes (buffer) - input image
    output: BytesIO object/buffer

    Takes in an image bytes and blurs it.
    '''
    image = cv2.imdecode(np.frombuffer(imageBytes, np.uint8), cv2.IMREAD_COLOR)
    blurredImage = cv2.GaussianBlur(image, (51, 51), 0) # apply a heavy blur to the image
    
    v.height, v.width = blurredImage.shape[:2]
    croppedImage = blurredImage[:, :300]
    
    _, buffer = cv2.imencode('.jpg', croppedImage) # encode the image to a BytesIO object
    imageIO = BytesIO(buffer)
    return imageIO

if process == 'export':
    phases = {}
    finalWave = np.array([], dtype=np.int16)

    lastNoteTime = 0
    for note in v.noteMap.items():
        lastNoteTime = max(lastNoteTime, note[1].time)

    for tempTick in range(1, lastNoteTime + 2):
        playingNotes = [
            (note.key, note.lead, note.color)
            for note in v.noteMap.values()
            if note.time == tempTick
        ]
        chunk, phases = sp.assembleNotes(playingNotes, phases, duration=v.ticksPerTile/60)
        finalWave = np.concatenate([finalWave, chunk])

    arr2d = sp.toSound(finalWave, returnType='2DArray')
    sp.exportToWav(arr2d, destination + '/' + os.path.splitext(os.path.basename(workingFile))[0] + '.wav', sample_rate=44100)
    sys.exit()

def convertNoteMapToStrikeList():
    '''
    fields: none
    outputs: nothing

    Converts the noteMap into a list of notes encoded by their duration and time of strike.
    '''
    strikeList = []
    for el, note in v.noteMap.items():
        if note.lead:
            offset = 1
            while (note.key, note.time + offset, note.color) in v.noteMap:
                offset += 1
            strikeList.append({"pitch": note.key + 35, "startTime": ((note.time - 1) / 4), "duration": (offset / 4)})
    
    return strikeList
        
if process == 'convert':
    sp.createMidiFromNotes(convertNoteMapToStrikeList(), destination)
    sys.exit()

def mouseBounds(rect):
    '''
    fields:
        rect (rect) - 4-coordinate x, y, dx, dy representing the bounds
    outputs: boolean

    Returns whether the mouse is within a rect-formatted bounding box.
    '''
    return rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]

def reevaluateLeads():
    '''
    fields: none
    outputs: nothing

    Recalculates which notes are considered lead notes.
    '''
    for note in v.noteMap.items():
        if v.colorName == note[1].color:
            if not ((note[0][0], note[0][1] - 1, v.colorName) in v.noteMap):
                v.noteMap[note[0]].lead = True

def unselectTextBoxes():
    '''
    fields: none
    outputs: nothing

    Loops through all text boxes and unselects them.
    '''
    for tb in v.globalTextBoxes:
        tb.selected = False

def sameNoteMaps(noteMap1, noteMap2):
    '''
    fields:
        noteMap1 (hashmap) - first note map
        noteMap2 (hashmap) - second note map
    outputs: boolean

    Compares two notemaps by value (not reference), used for change history (Ctrl+Z)
    '''
    try:
        longerNoteMap = noteMap1 if len(noteMap1.items()) >= len(noteMap2.items()) else noteMap2
        shorterNoteMap = noteMap1 if longerNoteMap == noteMap2 else noteMap2

        for hashkey, note1 in longerNoteMap.items():
            note2 = shorterNoteMap[hashkey]
            if note1.key == note2.key and note1.time == note2.time and note1.lead == note2.lead and note1.color == note2.color:
                None
            else:
                return False
        return True
    except:
        return False
    
console.log("Initialized Functions "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
console.log("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')

###### MAINLOOP ######
running = True
playHead = Head(0, 1, 0)
v.tempo = int(round(3600 / ps.ticksPerTile))
lastNoteTime = 0
ctrlZTime = 59
noteMapVersionTracker = []
noteMapFutureVersionTracker = []

root = None
last_update = time.time()

# Setup Tkinter console window (only if setting allows it)
if (process == 'open' and len(sys.argv) == 7) or (len(sys.argv) == 1):
    if (len(sys.argv) == 1) or json.load(open(user_settings_path))["show_console"]:
        try:
            root = cw.ConsoleWindow(consoleMessages)
        except Exception as e:
            print(f"Failed to open console window: {e}")
            root = None

while running:
    # Tkinter GUI updates
    if root is not None:
        try:
            now = time.time()
            if now - last_update > 0.05:  # Limit updates
                root.update()
                root.update_console()
                last_update = now
        except Exception as e:
            print(f"[Console closed or failed: {e}]")
            root = None  # Fully disable Tkinter from now on

    v.saveFrame += 60 * (1 / fps)
    if v.saveFrame > 1200: # Saves every 20 seconds
        v.saveFrame = 0
        myPath = open(workingFile if workingFile != "" else f"{v.source_path}/assets/workingfile.symphony", "wb")
        dumpToFile(myPath, workingFile if workingFile != "" else f"{v.source_path}/assets/workingfile.symphony")
        myPath.close()
    # checks if new changes have been made, if so adds them to the version history for Ctrl+Z
    ctrlZTime += 1
    if ctrlZTime > 60:
        for note in v.noteMap.items():
            lastNoteTime = max(lastNoteTime, note[1].time)
            v.noteCount = max(v.noteCount, lastNoteTime + 20)

        if not pygame.mouse.get_pressed()[0]:
            if noteMapVersionTracker == [] or not any(sameNoteMaps(noteMapVersionTracker[-i], v.noteMap) for i in range(1, len(noteMapVersionTracker) + 1)):
                noteMapVersionTracker.append(copy.deepcopy(v.noteMap))
                noteMapFutureVersionTracker = []
            if len(noteMapVersionTracker) > 32:
                noteMapVersionTracker.pop(0)
            ctrlZTime = 0
    v.screen.fill((0, 0, 0))
    transparentScreen.fill((0, 0, 0, 0))

    v.colorName = colorButton.getColorName()

    for row in range(ceil(v.viewScaleY) + 1):
        headerY = row * v.innerHeight / v.viewScaleY + v.toolbarHeight + (v.viewRow%1 * v.innerHeight / v.viewScaleY) - v.innerHeight/v.viewScaleY
        headerX = v.leftColumn - (v.viewColumn%1 * (v.width - v.leftColumn)/v.viewScaleX) - (v.width - v.leftColumn)/v.viewScaleX
        for column in range(ceil(v.viewScaleX) + 2):
            cm = (floor((column+v.viewColumn)%v.timeInterval) == 1) * 8
            pygame.draw.rect(v.screen, ((28 + cm, 28 + cm, 28 + cm) if not (-(floor(row - v.viewRow) + keyIndex + 1) % 12) in modeIntervals else (43 + cm, 43 + cm, 43 + cm)),
                         (headerX, headerY, (v.width - v.leftColumn)/v.viewScaleX, v.innerHeight/v.viewScaleY), border_radius=3)
            pygame.draw.rect(v.screen, (0, 0, 0),
                         (headerX, headerY, (v.width - v.leftColumn)/v.viewScaleX, v.innerHeight/v.viewScaleY), 1, 3)
            headerX += (v.width - v.leftColumn)/v.viewScaleX

            ##### BRUSH CONTROLS #####
            if mouseBounds((headerX, headerY, (v.width - v.leftColumn)/v.viewScaleX, v.innerHeight/v.viewScaleY)) and (pygame.mouse.get_pressed()[0]) and (v.toolbarHeight < pygame.mouse.get_pos()[1] < (v.height - 50)):
                touchedKey, touchedTime = floor(v.viewRow - row + 1), floor(column + v.viewColumn + 1)
                if not v.mouseTask:
                    v.mouseDownTime = time.time() # sets mouse start down time

                ## Head - means that selecting time stamp
                if v.head:
                    if not v.mouseTask:
                        playHead.home = (touchedTime - 1)
                        v.mouseTask = True
                ## Brush - unconditionally adds notes to the track
                elif v.brushType == "brush" and v.colorName != 'all':
                    if not v.mouseTask and not (touchedKey, touchedTime, v.colorName) in v.noteMap:
                        sp.playNotes([touchedKey], duration=0.25, waves=v.waveMap[v.colorName])
                        v.noteMap[(touchedKey, touchedTime, v.colorName)] = Note(touchedKey, touchedTime, True, color=v.colorName)
                        v.currentDraggingKey = touchedKey
                        v.initialDraggingTime = touchedTime
                    #reevaluateLeads()
                    v.mouseTask = True
                    if (not (v.currentDraggingKey, touchedTime, v.colorName) in v.noteMap) and touchedTime > v.initialDraggingTime:
                        v.noteMap[(v.currentDraggingKey, touchedTime, v.colorName)] = Note(v.currentDraggingKey, touchedTime, False, color=v.colorName)
                        tempOffsetTime = touchedTime - 1
                        while tempOffsetTime > v.initialDraggingTime + 1:
                            tempOffsetTime -= 1
                            v.noteMap[(v.currentDraggingKey, tempOffsetTime, v.colorName)] = Note(v.currentDraggingKey, tempOffsetTime, False, color=v.colorName)
            
                ## Eraser - unconditionally removes notes from the track
                elif v.brushType == "eraser" and v.colorName != 'all':
                    toDelete = []
                    for note in v.noteMap.items():
                        if (note[1].key, note[1].time, note[1].color) == (touchedKey, touchedTime, v.colorName):
                            toDelete.append((touchedKey, touchedTime, v.colorName))
                        if (note[1].key, note[1].time - 1, note[1].color) == (touchedKey, touchedTime, v.colorName) and not note[1].lead:
                            note[1].lead = True
                    for itemToDelete in toDelete:
                        del v.noteMap[itemToDelete]
                    v.mouseTask = True

                ## Selecter - when statically pressed, selects the note. When dragged moves the note.
                # if there is a previously selected note, it is unselected unless shift is pressed while selecting

                # Dragging moves the note UNLESS the drag is done from the very tail end of the note, in which case
                # all selected notes are lengthened or shortened by the drag amount.
                
                elif v.brushType == "select" and v.colorName != 'all':
                    if not v.mouseTask: # mouse was just clicked
                        for note in v.noteMap.items():
                            v.noteMap[note[0]].originalKey = v.noteMap[note[0]].key
                            v.noteMap[note[0]].originalTime = v.noteMap[note[0]].time
                        v.mouseHoldStart = pygame.mouse.get_pos()
                        mouseCellStart = (touchedKey, touchedTime, v.colorName)
                        v.mouseTask = True
                    else:
                        try:
                            mouseCellStart
                        except NameError:
                            #console.log("mouseCellStart not defined -- a selection was not initialized.")
                            None
                        else:
                            if (not mouseCellStart in v.noteMap) and (v.timeOffset, v.keyOffset) == (0,0):
                                v.drawSelectBox = True
                            else:
                                if pygame.key.get_pressed()[pygame.K_LALT]:
                                    numSelected = False
                                    v.duplicatedNoteMap = {}
                                    for note in v.noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                            v.duplicatedNoteMap[note[0]] = copy.deepcopy(note[1]) # adds the selected notemap to the duplicated notemap until alt is let go
                                            v.duplicatedNoteMap[note[0]].color = v.colorName
                                    if v.mouseTask and numSelected:# and dist(pygame..mouse.get_pos(), v.mouseHoldStart) > 10:
                                        ### Dragging
                                        (v.timeOffset, v.keyOffset) = (int((pygame.mouse.get_pos()[d] - v.mouseHoldStart[d]) / 
                                                                    (((v.width - v.leftColumn) / v.viewScaleX),(-v.innerHeight / v.viewScaleY))[d])
                                                                    for d in range(2) )
                                        delQ = []
                                        addQ = []
                                        refreshQ = False
                                        consistentKey = 0
                                        for note in v.duplicatedNoteMap.items():
                                            if v.duplicatedNoteMap[note[0]].selected:
                                                if consistentKey != 0 and consistentKey != v.duplicatedNoteMap[note[0]].key:
                                                    consistentKey = -1
                                                else:
                                                    consistentKey = v.duplicatedNoteMap[note[0]].key
                                                if v.duplicatedNoteMap[note[0]].key != v.duplicatedNoteMap[note[0]].originalKey + v.keyOffset or v.duplicatedNoteMap[note[0]].time != v.duplicatedNoteMap[note[0]].originalTime + v.timeOffset:
                                                    refreshQ = True
                                                v.duplicatedNoteMap[note[0]].key = v.duplicatedNoteMap[note[0]].originalKey + v.keyOffset
                                                v.duplicatedNoteMap[note[0]].time = v.duplicatedNoteMap[note[0]].originalTime + v.timeOffset
                                                delQ.append(note[0])
                                                addQ.append(((v.duplicatedNoteMap[note[0]].originalKey + v.keyOffset,
                                                            v.duplicatedNoteMap[note[0]].originalTime + v.timeOffset, v.colorName), note[1]))
                                        for delete in delQ:
                                            del v.duplicatedNoteMap[delete]
                                        for add in addQ:
                                            v.duplicatedNoteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if v.oldKeyOffset != v.keyOffset and consistentKey != -1 and consistentKey != 0:
                                            sp.playNotes([addQ[0][0][0]], duration=0.07, waves=v.waveMap[v.colorName])
                                else:
                                    numSelected = False
                                    for note in v.noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                    if v.mouseTask and numSelected and dist(pygame.mouse.get_pos(), v.mouseHoldStart) > 10:
                                        ### Dragging
                                        (v.timeOffset, v.keyOffset) = (int((pygame.mouse.get_pos()[d] - v.mouseHoldStart[d]) / 
                                                                    (((v.width - v.leftColumn) / v.viewScaleX),(-v.innerHeight / v.viewScaleY))[d])
                                                                    for d in range(2) )
                                        delQ = []
                                        addQ = []
                                        refreshQ = False
                                        consistentKey = 0
                                        for note in v.noteMap.items():
                                            if v.noteMap[note[0]].selected:
                                                if consistentKey != 0 and consistentKey != v.noteMap[note[0]].key:
                                                    consistentKey = -1
                                                else:
                                                    consistentKey = v.noteMap[note[0]].key
                                                if v.noteMap[note[0]].key != v.noteMap[note[0]].originalKey + v.keyOffset or v.noteMap[note[0]].time != v.noteMap[note[0]].originalTime + v.timeOffset:
                                                    refreshQ = True
                                                v.noteMap[note[0]].key = v.noteMap[note[0]].originalKey + v.keyOffset
                                                v.noteMap[note[0]].time = v.noteMap[note[0]].originalTime + v.timeOffset
                                                delQ.append(note[0])
                                                addQ.append(((v.noteMap[note[0]].originalKey + v.keyOffset,
                                                            v.noteMap[note[0]].originalTime + v.timeOffset, v.colorName), note[1]))
                                        for delete in delQ:
                                            del v.noteMap[delete]
                                        for add in addQ:
                                            v.noteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if v.oldKeyOffset != v.keyOffset and consistentKey != -1 and consistentKey != 0:
                                            sp.playNotes([addQ[0][0][0]], duration=0.07, waves=v.waveMap[v.colorName])
                v.mouseWOTask = False
                v.mouseTask = True

    scrOrange.fill((0, 0, 0, 0))
    scrPurple.fill((0, 0, 0, 0))
    scrLime.fill((0, 0, 0, 0))
    scrCyan.fill((0, 0, 0, 0))
    scrBlue.fill((0, 0, 0, 0))
    scrPink.fill((0, 0, 0, 0))

    thisNote.fill((0, 0, 0, 0))
    otherNotes.fill((0, 0, 0, 0))
    
    scrUsed = set()
    ### Renders noteMap to screen, based on color or "all" color
    for note in v.noteMap.items():
        if note[1].key > v.viewRow - v.viewScaleY and note[1].key < v.viewRow + 1:
            if note[1].time > v.viewColumn and note[1].time < v.viewColumn + v.viewScaleX + 1:
                if v.colorName == 'all':
                    if not (note[1].color in scrUsed):
                        scrUsed.add(scrList[v.colorsInd[note[1].color]])
                    #note[1].draw(screen, v.viewRow, v.viewColumn, noteMap)
                    note[1].draw(scrList[v.colorsInd[note[1].color]], v.viewRow, v.viewColumn, v.noteMap)
                else:
                    if note[1].color == v.colorName:
                        note[1].draw(thisNote, v.viewRow, v.viewColumn, v.noteMap)
                    else:
                        note[1].draw(otherNotes, v.viewRow, v.viewColumn, v.noteMap)
    
    if v.colorName == 'all':
        # render notes in order of stack
        for scr in scrList:
            if scr in scrUsed:
                v.screen.blit(scr, scr.get_rect())
    else:
        # always renders current color on top of gray ones
        v.screen.blit(otherNotes, otherNotes.get_rect())
        v.screen.blit(thisNote, thisNote.get_rect())
     
    for note in v.duplicatedNoteMap.items():
        if note[1].key > v.viewRow - v.viewScaleY and note[1].key < v.viewRow + 1:
            if note[1].time > v.viewColumn and note[1].time < v.viewColumn + v.viewScaleX + 1:
                note[1].draw(transparentScreen, v.viewRow, v.viewColumn, v.duplicatedNoteMap, transparent=True)

    if v.drawSelectBox:
        pygame.draw.rect(v.screen, (255, 255, 255), (min(v.mouseHoldStart[0], pygame.mouse.get_pos()[0]),
                                                                       min(v.mouseHoldStart[1], pygame.mouse.get_pos()[1]),
                                                                       abs(pygame.mouse.get_pos()[0] - v.mouseHoldStart[0]),
                                                                       abs(pygame.mouse.get_pos()[1] - v.mouseHoldStart[1])), 1)

    # functionality to move playhead and draw it when it is moving
    if v.playing:
        playHead.tick += 1 * 60/fps
        playHead.draw(v.screen, v.viewRow, v.viewColumn, v.leftColumn, (v.width - v.leftColumn) / v.viewScaleX, drawHead=True)
    else:
        playHead.draw(v.screen, v.viewRow, v.viewColumn, v.leftColumn, (v.width - v.leftColumn) / v.viewScaleX)

    ### LEFT COLUMN
    for row in range(ceil(v.viewScaleY) + 1):
        headerX, headerY = 0, row * v.innerHeight / v.viewScaleY + v.toolbarHeight + (v.viewRow%1 * v.innerHeight / v.viewScaleY) - v.innerHeight / v.viewScaleY
        note = f"{(v.NOTES_SHARP if v.accidentals == 'sharps' else v.NOTES_FLAT)[floor((v.viewRow - row) % 12)]} {floor((v.viewRow - row) / 12) + 1}"
        pygame.draw.rect(v.screen, ((26, 26, 26) if not (-(floor(row - v.viewRow) + keyIndex + 1) % 12) in modeIntervals else (34, 34, 34)),
                         (headerX, headerY, v.leftColumn, v.innerHeight / v.viewScaleY), border_radius=3)
        pygame.draw.rect(v.screen, (0, 0, 0),
                         (headerX, headerY, v.leftColumn, v.innerHeight / v.viewScaleY), 1, 3)
        stamp(note, v.SUBHEADING1, headerX + 5, headerY + 5, 0.4)

        if mouseBounds((0, headerY, v.leftColumn, v.innerHeight/v.viewScaleY)) and (pygame.mouse.get_pressed()[0]) and (v.toolbarHeight < pygame.mouse.get_pos()[1] < (v.height - 50)) and not v.mouseTask:
            # mouse is clicking the note labels
            v.mouseTask = True
            sp.playNotes([floor(v.viewRow - row + 1)], duration=0.25, waves=v.waveMap[v.colorName])

    def renderScrollBar():
        '''
        fields: none
        outputs: nothing

        Function to draw the bottom scroll bar on the screen for navigating horizontally.
        '''
        scrollBarHeight = 15
        scrollBarColor = (100, 100, 100)
        progressLeft = v.viewColumn / v.noteCount
        progressRight = (v.viewColumn + v.viewScaleX) / v.noteCount
        mouseDel = pygame.mouse.get_rel()[0]/(v.width - v.leftColumn) * v.noteCount

        if pygame.mouse.get_pos()[1] > v.height - 80:
            if ((v.width - v.leftColumn) * progressLeft) + v.leftColumn < pygame.mouse.get_pos()[0] < ((v.width - v.leftColumn) * progressRight) + v.leftColumn and pygame.mouse.get_pos()[1] > v.height - scrollBarHeight - 15:
                # mouse is touching scroll bar
                if pygame.mouse.get_pressed()[0]:
                    # mouse is dragging scroll bar
                    scrollBarColor = (255, 255, 255)
                    if not v.mouseTask:
                        v.viewColumn += mouseDel
                else:
                    scrollBarColor = (150, 150, 150)
            else:
                # mouse is close to screen bottom
                scrollBarColor = (100, 100, 100)
        else:
            scrollBarHeight = 10

        pygame.draw.rect(v.screen, scrollBarColor, (((v.width - v.leftColumn) * progressLeft) + v.leftColumn,
                                                  v.height - scrollBarHeight - 3,
                                                  (v.width - v.leftColumn) * (progressRight - progressLeft),
                                                  scrollBarHeight), 1, 3)

    def renderToolBar():
        '''
        fields: none
        outputs: nothing

        Renders the top toolbar, and all of the elements inside of it.
        '''
        global key, keyIndex, mode, modeIntervals
        pygame.draw.rect(v.screen, (43, 43, 43), (0, 0, v.width, v.toolbarHeight))
        pygame.draw.line(v.screen, (0, 0, 0), (0, v.toolbarHeight), (v.width, v.toolbarHeight))
        pygame.draw.line(v.screen, (30, 30, 30), (0, v.toolbarHeight - 1), (v.width, v.toolbarHeight - 1))
        pygame.draw.line(v.screen, (49, 49, 49), (0, v.toolbarHeight - 2), (v.width, v.toolbarHeight - 2))
        pygame.draw.line(v.screen, (45, 45, 45), (0, v.toolbarHeight - 3), (v.width, v.toolbarHeight - 3))

        ### TRACK TITLE BAR
        if (v.width >= 1100):
            pygame.draw.rect(v.screen, (0, 0, 0), (475, v.toolbarHeight/2 - 14, v.width - 950, 28), 1, 3)
            if len(titleText) < (v.width - 950) / 10:
                stamp(titleText, v.SUBHEADING1, v.width/2, 40, 0.4, "center")
            else:
                stamp(titleText[:int((v.width - 950) / 10)] + '...', v.SUBHEADING1, v.width/2, 40, 0.4, "center")
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        ### PLAY/PAUSE BUTTON
        playPauseButton.x = 33
        if playPauseButton.mouseClicked():
            v.playing = not v.playing
            if v.playing:
                playHead.play()
                v.lastPlayTime = time.time()
            else:
                v.play_obj.stop()
            v.mouseTask = True
            playHead.tick = playHead.home
        playPauseButton.draw(pauseImage if v.playing else playImage)

        ### ACCIDENTALS BUTTON
        accidentalsButton.x = 120
        if accidentalsButton.mouseClicked():
            keyIndex = (v.NOTES_SHARP if v.accidentals == "sharps" else v.NOTES_FLAT).index(key)
            key = (v.NOTES_FLAT if v.accidentals == "sharps" else v.NOTES_SHARP)[keyIndex]
            v.accidentals = ("sharps" if v.accidentals == "flats" else "flats")
            v.mouseTask = True
        accidentalsButton.draw(v.accidentals)
        
        ### PLAYHEAD BUTTON
        playheadButton.x = 207
        if playheadButton.mouseClicked():
            v.head = not v.head
            v.mouseTask = True
        if v.head:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
            playheadButton.draw(headImage, overrideDark=True)
        else:
            playheadButton.draw(headImage)

        ### COLOR BUTTON
        colorButton.x = v.width - 345
        if colorButton.mouseClicked():
            colorButton.nextColor()
            v.mouseTask = True
        if colorButton.getColorName() == "all":
            colorButton.draw(rainbowImage)
        else:
           colorButton.draw()

        ### WAVE BUTTON
        waveButton.x = v.width - 317
        if waveButton.mouseClicked():
            v.waveMap[v.colorName] = (v.waveMap[v.colorName] + 1) % len(v.waveTypes)
            v.mouseTask = True
        if v.colorName != 'all': # doesn't render the wave type for 'all' since it is irrelevant
            waveButton.draw(waveImages[v.waveMap[v.colorName]])

        ### KEY BUTTON
        keyButton.x = v.width - 260
        if keyButton.mouseClicked():
            keyIndex = (v.NOTES_SHARP if v.accidentals == "sharps" else v.NOTES_FLAT).index(key)
            key = (v.NOTES_SHARP if v.accidentals == "sharps" else v.NOTES_FLAT)[keyIndex + 1 if keyIndex != 11 else 0]
            keyIndex = keyIndex + 1 if keyIndex != 11 else 0
            v.mouseTask = True
        keyButton.draw(key)

        ### MODE BUTTON
        modeButton.x = v.width - 220
        if modeButton.mouseClicked():
            modeIndex = next(i for i, (x, _) in enumerate(v.modesIntervals) if x == mode)
            mode = v.modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][0]
            modeIntervals = set(v.modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][1])
            v.mouseTask = True
        modeButton.draw(mode)

        ### BRUSH/ERASER/NEGATER BUTTON
        brushButton.x = v.width - 93
        if brushButton.mouseClicked():
            if v.brushType == "brush":
                v.brushType = "eraser"
            elif v.brushType == "eraser":
                v.brushType = "select"
            else:
                v.brushType = "brush"
                for note in v.noteMap.items():
                    note[1].selected = False
            v.mouseTask = True
        brushButton.draw("select" if v.brushType == "select" else brushImage if v.brushType == "brush" else eraserImage)

        ### TIME SIGNATURE CONTROLS
        timeSigUpButton.x = v.width - 395
        timeSigUpButton.draw(upChevronImage)
        if timeSigUpButton.mouseClicked():
            v.timeInterval += 1
            v.mouseTask = True
        timeSigTextBox.x = v.width - 425
        if timeSigTextBox.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        if timeSigTextBox.mouseClicked():
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
                unselectTextBoxes()
            timeSigTextBox.selected = True
        timeSigTextBox.draw(str(timeSigTextBox.text))
        if timeSigTextBox.selected:
            v.timeInterval = 1 if (timeSigTextBox.text == '' or int(timeSigTextBox.text) == 0) else int(timeSigTextBox.text)
        else:
            timeSigTextBox.text = str(v.timeInterval)

        timeSigDownButton.x = v.width - 445
        timeSigDownButton.draw(downChevronImage)
        if timeSigDownButton.mouseClicked():
            v.timeInterval = max(1, v.timeInterval - 1)
            v.mouseTask = True

        ### TEMPO CONTROLS
        tempoUpButton.x = 425
        tempoUpButton.draw(upChevronImage)
        if tempoUpButton.mouseClicked():
            v.tempo += 1
            v.mouseTask = True

        tempoTextBox.x = 320
        if tempoTextBox.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        if tempoTextBox.mouseClicked():
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
                unselectTextBoxes()
            tempoTextBox.text = ''
            tempoTextBox.selected = True
        if tempoTextBox.selected:
            v.ticksPerTile = 3600 / v.tempo
            v.tempo = 1 if (tempoTextBox.text == '' or int(tempoTextBox.text) == 0) else int(tempoTextBox.text)
        else:
            tempoTextBox.text = str(v.tempo)
        tempoTextBox.draw(str(tempoTextBox.text) + ' tpm')

        tempoDownButton.x = 300
        tempoDownButton.draw(downChevronImage)
        if tempoDownButton.mouseClicked():
            v.tempo = max(1, v.tempo - 1)
            v.mouseTask = True

    renderScrollBar()
    renderToolBar()
            
    v.tick += 1 - (v.tick == v.tickInterval - 1) * v.tickInterval
    if v.tick == v.tickInterval - 1:
        None

    def selectConnected(key, time):
        '''
        fields:
            key (number) - the key (pitch) of the note
            time (number) - the time (beat) of the note
        outputs: nothing

        Function to take in a key and time and select all connected notes, and return whether a note exists at that key and time.
        '''
        noteExists = False
        deviation = 0
        while (key, time + deviation, v.colorName) in v.noteMap:
            noteExists = True
            v.noteMap[(key, time + deviation, v.colorName)].selected = True
            if v.noteMap[(key, time + deviation, v.colorName)].lead == True:
                v.noteMap[(key, time + deviation, v.colorName)].selected = True
                break
            deviation -= 1
        deviation = 1
        while (key, time + deviation, v.colorName) in v.noteMap:
            noteExists = True
            if v.noteMap[(key, time + deviation, v.colorName)].lead == True:
                break
            v.noteMap[(key, time + deviation, v.colorName)].selected = True
            deviation += 1
        return noteExists

    if not pygame.mouse.get_pressed()[0] and not v.mouseWOTask:
        reevaluateLeads()
        ### Unclicked
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        if v.head:
            v.head = False
        try:
            mouseCellStart
        except NameError:
            #console.log("mouseCellStart not defined -- a selection was not initialized.")
            None
        else:
            if (v.mouseHoldStart != pygame.mouse.get_pos()) and v.brushType == "select":
                ### Drag Selected
                for note in v.noteMap.items():
                    if inBounds(v.mouseHoldStart, pygame.mouse.get_pos(), note[1].SScoords) and note[1].color == v.colorName:
                        note[1].selected = True
                        selectConnected(note[0][0], note[0][1])
        if (time.time() - v.mouseDownTime) < 0.2 and v.brushType == "select":
            v.timeOffset = 0
            v.keyOffset = 0
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # if shift is not held, unselect all elements.
                for note in v.noteMap.items():
                    note[1].selected = False
            
            # selected from mouse selection, opposite of dragging, only happens once mouse is lifted.
            noteExists = selectConnected(touchedKey, touchedTime)
            if noteExists:
                sp.playNotes([touchedKey], duration=0.25, waves=v.waveMap[v.colorName])
            v.mouseTask = True
        v.mouseWOTask = True

    if v.worldMessage != "": # Renders the world message if it isn't an empty string
        worldMessageRender = stamp(v.worldMessage, v.SUBSCRIPT1, v.width/2, 8, 0.5, "center")

    v.dRow *= 0.9
    v.dCol *= 0.9

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            console.warn("Pygame was quit")
        elif event.type == pygame.VIDEORESIZE:
            v.screen = pygame.display.set_mode((max(event.w, minWidth), max(event.h, minHeight)), pygame.RESIZABLE)
            v.width, v.height = (max(event.w, minWidth), max(event.h, minHeight))
            transparentScreen = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            thisNote = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            otherNotes = pygame.Surface((v.width, v.height), pygame.SRCALPHA)

            scrOrange = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            scrPurple = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            scrCyan = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            scrLime = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            scrBlue = pygame.Surface((v.width, v.height), pygame.SRCALPHA)
            scrPink = pygame.Surface((v.width, v.height), pygame.SRCALPHA)

            scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]

            v.viewScaleX = (v.width - v.leftColumn) / ((1100 - v.leftColumn) // 32) # keeps the box consistent v.width even when the window is resized
            v.viewScaleY = (v.height - v.toolbarHeight) / ((592 - v.toolbarHeight) / 16) # keeps the box consistent v.height even when the window is resized
            v.innerHeight = v.height - v.toolbarHeight

        elif event.type == pygame.KEYDOWN:
            ### Typing in textbox
            if any(textBox.selected for textBox in v.globalTextBoxes):
                selectedTextBoxes = [filter(lambda x : x.selected == True, v.globalTextBoxes)][0]
                pressedKeys = [pygame.key.get_pressed()[possKey] for possKey in [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_BACKSPACE, pygame.K_RETURN]]
                if pressedKeys[10]:
                    for textBox in selectedTextBoxes:
                        textBox.text = textBox.text[:-1]
                if pressedKeys[11]:
                    unselectTextBoxes()
                else:
                    for textBox in selectedTextBoxes:
                        if True in pressedKeys:
                            textBox.text = textBox.text + str(pressedKeys.index(True))
            elif any(pygame.key.get_pressed()[possKey] for possKey in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]):
                colorButton.setColor([pygame.key.get_pressed()[possKey] for possKey in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]].index(True))
                if pygame.key.get_pressed()[pygame.K_LALT]:
                    delQ = []
                    addQ = []
                    for note in v.duplicatedNoteMap.items():
                        newNote = copy.deepcopy(note[1])
                        newNote.color = colorButton.color
                        delQ.append((note[0]))
                        addQ.append(((note[0][0], note[0][1], colorButton.color), newNote))
                    for d in delQ:
                        del v.duplicatedNoteMap[d]
                    for a in addQ:
                        v.duplicatedNoteMap[a[0]] = a[1]

            elif event.key == pygame.K_UP: # Scroll up
                v.dRow += 0.16
            elif event.key == pygame.K_DOWN: # Scroll down
                v.dRow -= 0.16
            elif event.key == pygame.K_RIGHT: # Scrub right
                v.dCol += 0.16
            elif event.key == pygame.K_LEFT: # Scrub left
                v.dCol -= 0.16
            elif event.key == CMD_KEY: # Switch to eraser momentarily
                v.brushType = "eraser"
            elif event.key == pygame.K_LSHIFT: # Switch to select permanently
                v.brushType = "select"
            elif event.key == pygame.K_SPACE: # Play / pause
                v.playing = not v.playing
                if v.playing:
                    playHead.play()
                    v.lastPlayTime = time.time()
                else:
                    v.play_obj.stop()
                playHead.tick = playHead.home
            elif event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE: # Delete selected note
                delQ = []
                for index, note in v.noteMap.items():
                    if note.selected:
                        delQ.append(index)
                for q in delQ:
                    del v.noteMap[q]
            elif event.key == pygame.K_s:
                if pygame.key.get_pressed()[CMD_KEY]: # if the user presses Ctrl+S (to save)
                    if workingFile == "": # file dialog to show up if the user's workspace is not attached to a file
                        filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
                        if filename != None:
                            filestring = filename.name
                            myPath = open(f"{v.source_path}/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, directory=filestring)
                            myPath = open(f"{v.source_path}/assets/workingfile.symphony", "rb")

                            pathBytes = bytearray(myPath.read())
                            filename.write(pathBytes)
                            filename.close()
                            workingFile = filestring
                        else:
                            myPath = open(f"{v.source_path}/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, f"{v.source_path}/assets/workingfile.symphony")
                    else: # save to workspace file
                        myPath = open(workingFile, "wb")
                        dumpToFile(myPath, workingFile)
                    v.saveFrame = 0
            elif event.key == pygame.K_z or event.key == pygame.K_y:
                if pygame.key.get_pressed()[CMD_KEY]:
                    if (pygame.key.get_pressed()[pygame.K_LSHIFT] and event.key == pygame.K_z) or event.key == pygame.K_y: # user wishes to redo (Ctrl+Shift+Z or Ctrl+Y)
                        try:
                            noteMapVersionTracker.append(copy.deepcopy(noteMapFutureVersionTracker.pop()))
                        except Exception as e:
                            console.warn("Cannot redo further")
                        if len(noteMapFutureVersionTracker) > 0:
                            v.noteMap = copy.deepcopy(noteMapFutureVersionTracker[-1])
                    elif event.key == pygame.K_z: # user wishes to undo (Ctrl+Z)
                        try:
                            noteMapFutureVersionTracker.append(copy.deepcopy(noteMapVersionTracker.pop()))
                        except Exception as e:
                            console.warn("Cannot undo further")
                        if len(noteMapVersionTracker) > 0:
                            v.noteMap = copy.deepcopy(noteMapVersionTracker[-1])
            elif event.key == pygame.K_PERIOD:
                addQ = []
                for note in v.noteMap.items():
                    if note[1].selected:
                        if not ((note[1].key, note[1].time + 1, note[1].color) in v.noteMap) or v.noteMap[(note[1].key, note[1].time + 1, note[1].color)].lead:
                            el = Note(note[1].key, note[1].time + 1, False, note[1].color)
                            el.selected = True
                            addQ.append(((note[1].key, note[1].time + 1, note[1].color), el))
                for a in addQ:
                    v.noteMap[a[0]] = a[1]
                    selectConnected(a[0][0], a[0][1])
            elif event.key == pygame.K_COMMA:
                delQ = []
                for note in v.noteMap.items():
                    if note[1].selected:
                        if not ((note[1].key, note[1].time + 1, note[1].color) in v.noteMap) or v.noteMap[(note[1].key, note[1].time + 1, note[1].color)].lead:
                            delQ.append(note[0])
                for d in delQ:
                    del v.noteMap[d]
        elif event.type == pygame.KEYUP:
            if event.key == CMD_KEY: # Switches away from eraser when Ctrl is let go
                v.brushType = "brush"
                for note in v.noteMap.items():
                    note[1].selected = False
            if event.key == pygame.K_LALT: # Duplicates selection
                for note in v.duplicatedNoteMap.items():
                    v.noteMap[note[0]] = copy.deepcopy(note[1])
                v.duplicatedNoteMap.clear()
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0: # Scroll up
                v.dRow += 0.06
            if event.y < 0: # Scroll down
                v.dRow -= 0.06
            if event.x > 0: # Scrub right
                v.dCol += 0.06
            if event.x < 0: # Scrub left
                v.dCol -= 0.06
    v.viewRow = max(min(v.viewRow + v.dRow, v.noteRange + 0.01), v.viewScaleY - 0.01) # prevents overscroll
    v.viewColumn = max(min(v.viewColumn + v.dCol, (v.noteCount - v.viewScaleX)), 0.01) # prevents overscrub

    v.oldKeyOffset = v.keyOffset
    v.drawSelectBox = False

    v.screen.blit(transparentScreen, transparentScreen.get_rect()) # duplicated components to drag

    if not pygame.mouse.get_pressed()[0]:
        v.mouseTask = False
    clock.tick(fps)
    pygame.display.flip()  # Update the display

if workingFile == "": # file dialog to show up if the user has unsaved changes (they have not attached the workspace to a file)
    filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
    if filename != None:
        myPath = open(f"{v.source_path}/assets/workingfile.symphony", "wb")

        dumpToFile(myPath, directory=f"{v.source_path}/assets/workingfile.symphony")
        myPath = open(f"{v.source_path}/assets/workingfile.symphony", "rb")

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()
else: # save all changes upon closing that have happened since the last autosave
    myPath = open(workingFile, "wb")
    dumpToFile(myPath, directory=workingFile)
    
# quit loop
pygame.quit()
sys.exit()