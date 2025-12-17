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
from tkinter.filedialog import asksaveasfile, asksaveasfilename
import json
import traceback

lastTime = time.time()
START_TIME = lastTime

###### INTERNAL MODULES ######

import console_controls.console_window as cw
import utils.sound_processing as sp
import gui.element as gui
import gui.frame as frame
import gui.custom as custom
from console_controls.console import *
import utils.state_loading as sl
import utils.file_io as fio

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
source_path = 'inner/src'

SAMPLE_RATE = 44100

titleText = "My Track 1"
process = ''
autoSave = None
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
    source_path = get_arg_path(4, 'assets/directory.json')
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

###### IMAGES ######

playImage = pygame.image.load(f"{source_path}/assets/play.png")
pauseImage = pygame.image.load(f"{source_path}/assets/pause.png")
headImage = pygame.image.load(f"{source_path}/assets/head.png")
brushImage = pygame.image.load(f"{source_path}/assets/brush.png")
eraserImage = pygame.image.load(f"{source_path}/assets/eraser.png")
negaterImage = pygame.image.load(f"{source_path}/assets/negater.png")

squareWaveImage = pygame.image.load(f"{source_path}/assets/square.png")
sawtoothWaveImage = pygame.image.load(f"{source_path}/assets/sawtooth.png")
triangleWaveImage = pygame.image.load(f"{source_path}/assets/triangle.png")
waveImages = [squareWaveImage, triangleWaveImage, sawtoothWaveImage]

upChevronImage = pygame.image.load(f"{source_path}/assets/up.png")
downChevronImage = pygame.image.load(f"{source_path}/assets/down.png")

###### PYGAME & WINDOW INITIALIZE ######

if process in ['instantiate', 'retrieve', 'export', 'convert']:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

console.log("Initialized Args "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

width, height = (1100, 592)
minWidth, minHeight = (925, 592)
iconPath = f'{source_path}/assets/icon32x32.png'
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
#pygame.display.set_icon(pygame.image.load(f"{source_path}/icon.png"))
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE, pygame.NOFRAME)

if (process == 'instantiate') or (process == 'retrieve'):
    None
else:
    pygame.display.flip()
    pygame.event.pump()
    time.sleep(0.1)

console.log("Initialized Window "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)  # initialize pygame. mixer at module import

clock = pygame.time.Clock()
fps = 60

###### VARIABLE & GUI ELEMENT SETUP ######

worldMessage = ""

key = 0
mode = 0

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected

page = "Editor"
noteMap = {}

tick = 0
saveFrame = 0

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
noteCount = 128 # horizontal count of notes (beats) in the grid
noteRange = 72 # vertical count of notes (keys) in the grid
modesIntervals = [
    ["Lydian",        [0, 2, 4, 6, 7, 9, 11]],
    ["Ionian (maj.)", [0, 2, 4, 5, 7, 9, 11]],
    ["Mixolydian",    [0, 2, 4, 5, 7, 9, 10]],
    ["Dorian",        [0, 2, 3, 5, 7, 9, 10]],
    ["Aeolian (min.)",[0, 2, 3, 5, 7, 8, 10]],
    ["Phrygian",      [0, 1, 3, 5, 7, 8, 10]],
    ["Locrian",       [0, 1, 3, 5, 6, 8, 10]]
]
modes = [item[0] for item in modesIntervals]
modeIntervals = set()
keyIndex = 0
colors = {
    "orange" : (168, 136, 49),
    "purple" : (134, 48, 156),
    "cyan" : (20, 128, 150),
    "lime" : (102, 150, 20),
    "blue" : (61, 80, 156),
    "pink" : (168, 49, 94),
    "all" : (255, 255, 255)
}
colorsInd = {
    "orange" : 0,
    "purple" : 1,
    "cyan" : 2,
    "lime" : 3,
    "blue" : 4,
    "pink" : 5,
    "all" : 6
}
colorsList = colors.items()
justColors = [n[1] for n in colorsList]
justColorNames = [n[0] for n in colorsList]

waveTypes = ['square', 'triangle', 'sawtooth']

waveMap = {}
for index, color in enumerate(colorsList):
    waveMap[color[0]] = 0

accidentals = "flats"
head = False
playing = False
brushType = "brush"

viewRow = 50
viewCol = 0
tileWidth = 10
tileHeight = 10

dx = 0
dy = 0

timeInterval = 4

ticksPerTile = 10

mainFont = f'{source_path}/assets/InterVariable.ttf'

tempo = int(round(3600 / ticksPerTile))
gui.init(source_path)

###### ASSETS ######

if process == 'open':
    bytes_io = BytesIO()
    console.log("Initialized Classes "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
    lastTime = time.time()

console.log("Initialized Assets "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

colorStates = custom.getColorStates(28, 28, source_path)
ColorButton = gui.Button(pos=(width - 345, 40), width=28, height=28, states=colorStates)

KeyButton = gui.Button(pos=(width - 260, 40), width=40, height=28, states=NOTES_FLAT)
ModeButton = gui.Button(pos=(width - 220, 40), width=100, height=28, states=modes)
BrushButton = gui.Button(pos=(width - 93, 40), width=60, height=28, states=[brushImage, eraserImage, 'select'])
WaveButton = gui.Button(pos=(width - 317, 40), width=28, height=28, states=[squareWaveImage, triangleWaveImage, sawtoothWaveImage])
RightToolbar = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                           [KeyButton, ModeButton, BrushButton, WaveButton, ColorButton])


PlayPauseButton = gui.Button(pos=(33, 40), width=60, height=28, states=[playImage, pauseImage])
AccidentalsButton = gui.Button(pos=(120, 40), width=60, height=28, states=["sharps", "flats"])
PlayheadButton = gui.Button(pos=(207, 40), width=60, height=28, states=[headImage])
LeftToolbar = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                           [PlayPauseButton, AccidentalsButton, PlayheadButton])

MeasureLengthDownButton = gui.Button(pos=(width - 420, 40), width=20, height=28, states=[downChevronImage])
MeasureLengthTextBox = gui.TextBox(pos=(width - 400, 40), width=30, height=28, text='4')
MeasureLengthUpButton = gui.Button(pos=(width - 370, 40), width=20, height=28, states=[upChevronImage])
MeasureLengthControls = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                                    [MeasureLengthDownButton, MeasureLengthTextBox, MeasureLengthUpButton])

TempoDownButton = gui.Button(pos=(300, 40), width=20, height=28, states=[downChevronImage])
TempoTextBox = gui.TextBox(pos=(320, 40), width=105, height=28, text='360')
TempoUpButton = gui.Button(pos=(425, 40), width=20, height=28, states=[upChevronImage])
TempoControls = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                            [TempoDownButton, TempoTextBox, TempoUpButton])

ToolBar = frame.Panel((0, 0, width, 80), gui.BG_COLOR,
                          [RightToolbar, LeftToolbar, MeasureLengthControls, TempoControls])

NotePanel = custom.NotePanel(pos=(80, 80), width=width-80, height=height-80)

#PlayHead = Head(0, 1, 0)

MasterPanel = frame.Panel((0, 0, width, height), gui.BG_COLOR, [ToolBar, NotePanel])
###### PROGRAM STATE INITIALIZE ######

if workingFile == "" or process == 'instantiate': # if the workingfile is not provided or we are creating a new file, initialize a new program state
    ps = sl.newProgramState("Eb", "Lydian", 10, noteMap, waveMap)
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
        #console.log(ps["noteMap"])
        tpm = round(3600 / ps["ticksPerTile"], 2)
        tiles = int((max(ps["noteMap"].items(), key=lambda x : x[0][1]))[0][1]) if (len(ps["noteMap"].items()) > 0) else 0
        json.dump({ 'fileInfo' : {
                    'Key' : ps["key"],
                    'Mode' : ps["mode"],
                    'Tempo (tpm)' : tpm,
                    #'Empty?' : (ps["noteMap"] == {}),
                    'Length (tiles)' : tiles,
                    'Duration' : ("0" if len(str(floor(tiles / tpm))) == 1 else '') + str(floor(tiles / tpm)) + ':' + ("0" if len(str(round(((tiles / tpm) % 1) * 60))) == 1 else '') + str(round(((tiles / tpm) % 1) * 60))
                    }, 'id': globalUUID
                }, f)
        f.close()
    sys.exit()

console.log("Initialized ProgramState "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

noteMap = ps["noteMap"]
ticksPerTile = ps["ticksPerTile"]
waveMap = ps["waveMap"]
key = ps["key"]
if "b" in key:
    keyIndex = NOTES_FLAT.index(key)
    accidentals = "flats"
else:
    keyIndex = NOTES_SHARP.index(key)
    accidentals = "sharps"
mode = ps["mode"]

modeIntervals = set(modesIntervals[0][1])

###### GUI LOGIC ######

# Key, Mode
KeyButton.setCurrentState(keyIndex)
ModeButton.setCurrentState(modes.index(mode))

# Tempo, MeasureLength Restrictions
TempoTextBox.setInputRestrictions('numeric')
TempoTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) > 0))

MeasureLengthTextBox.setInputRestrictions('numeric')
MeasureLengthTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) > 0))

# Tempo Controls
def tempoUp():
    global ticksPerTile, tempo
    tempo += 1
    ticksPerTile = round(3600 / tempo)
    TempoTextBox.setText(tempo)

    TempoControls.render(screen)

def tempoDown():
    global ticksPerTile, tempo
    tempo = max(10, tempo - 1)
    ticksPerTile = round(3600 / tempo)
    TempoTextBox.setText(tempo)

    TempoControls.render(screen)

TempoUpButton.onMouseClick(tempoUp)
TempoDownButton.onMouseClick(tempoDown)

# Measure Length Controls
def measureLengthUp():
    global timeInterval
    timeInterval += 1
    MeasureLengthTextBox.setText(timeInterval)

    MeasureLengthControls.render(screen)

def measureLengthDown():
    global timeInterval
    timeInterval = max(1, timeInterval - 1)
    MeasureLengthTextBox.setText(timeInterval)

    MeasureLengthControls.render(screen)

MeasureLengthUpButton.onMouseClick(measureLengthUp)
MeasureLengthDownButton.onMouseClick(measureLengthDown)

MasterPanel.render(screen)

###### FUNCTIONS ######

if process == 'instantiate':
    worldMessage = fio.dumpToFile(workingFile,
                                  workingFile,
                                  sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap),
                                  process,
                                  autoSave,
                                  titleText,
                                  sessionID)
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

if process == 'export':
    phases = {}
    finalWave = np.array([], dtype=np.int16)

    lastNoteTime = 0
    for note in noteMap.items():
        lastNoteTime = max(lastNoteTime, note[1].time)

    for tempTick in range(1, lastNoteTime + 2):
        playingNotes = [
            (note.key, note.lead, note.color)
            for note in noteMap.values()
            if note.time == tempTick
        ]
        chunk, phases = sp.assembleNotes(playingNotes, phases, waveMap, duration=ticksPerTile/60)
        finalWave = np.concatenate([finalWave, chunk])

    arr2d = sp.toSound(finalWave, returnType='2DArray')
    sp.exportToWav(arr2d, destination + '/' + os.path.splitext(os.path.basename(workingFile))[0] + '.wav', sample_rate=44100)
    sys.exit()
        
if process == 'convert':
    sp.createMidiFromNotes(sl.convertNoteMapToStrikeList(noteMap), destination)
    sys.exit()

    
console.log("Initialized Functions "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
console.log("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')

###### MAINLOOP ######
running = True
tempo = int(round(3600 / ps["ticksPerTile"]))
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
            root = cw.ConsoleWindow(consoleMessages, source_path)
        except Exception as e:
            console.error(f"Failed to open console window: {e}")
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
            console.error(f"[Console closed or failed: {e}]")
            root = None  # Fully disable Tkinter from now on

    saveFrame += 60 * (1 / fps)
    if saveFrame > 1200: # Saves every 20 seconds
        saveFrame = 0
        myPath = workingFile if workingFile != "" else f"{source_path}/assets/workingfile.symphony"
        worldMessage = fio.dumpToFile(
                                myPath,
                                myPath,
                                sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap),
                                process,
                                autoSave,
                                titleText,
                                sessionID)

    '''
    for row in range(ceil(viewScaleY) + 1):
        headerY = row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight / viewScaleY) - innerHeight/viewScaleY
        headerX = leftColumn - (viewColumn%1 * (width - leftColumn)/viewScaleX) - (width - leftColumn)/viewScaleX
        for column in range(ceil(viewScaleX) + 2):
            cm = (floor((column+viewColumn)%timeInterval) == 1) * 8
            pygame.draw.rect(screen, ((28 + cm, 28 + cm, 28 + cm) if not (-(floor(row - viewRow) + keyIndex + 1) % 12) in modeIntervals else (43 + cm, 43 + cm, 43 + cm)),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), 1, 3)
            headerX += (width - leftColumn)/viewScaleX

            ##### BRUSH CONTROLS #####
            if mouseBounds((headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY)) and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)):
                touchedKey, touchedTime = floor(viewRow - row + 1), floor(column + viewColumn + 1)
                if not mouseTask:
                    mouseDownTime = time.time() # sets mouse start down time

                ## Head - means that selecting time stamp
                if head:
                    if not mouseTask:
                        #playHead.home = (touchedTime - 1)
                        mouseTask = True
                ## Brush - unconditionally adds notes to the track
                elif brushType == "brush" and colorName != 'all':
                    if not mouseTask and not (touchedKey, touchedTime, colorName) in noteMap:
                        play_obj = sp.playNotes([touchedKey], duration=0.25, waves=waveMap[colorName])
                        noteMap[(touchedKey, touchedTime, colorName)] = Note(touchedKey, touchedTime, True, color=colorName)
                        currentDraggingKey = touchedKey
                        initialDraggingTime = touchedTime
                    #reevaluateLeads()
                    mouseTask = True
                    if (not (currentDraggingKey, touchedTime, colorName) in noteMap) and touchedTime > initialDraggingTime:
                        noteMap[(currentDraggingKey, touchedTime, colorName)] = Note(currentDraggingKey, touchedTime, False, color=colorName)
                        tempOffsetTime = touchedTime - 1
                        while tempOffsetTime > initialDraggingTime + 1:
                            tempOffsetTime -= 1
                            noteMap[(currentDraggingKey, tempOffsetTime, colorName)] = Note(currentDraggingKey, tempOffsetTime, False, color=colorName)
            
                ## Eraser - unconditionally removes notes from the track
                elif brushType == "eraser" and colorName != 'all':
                    toDelete = []
                    for note in noteMap.items():
                        if (note[1].key, note[1].time, note[1].color) == (touchedKey, touchedTime, colorName):
                            toDelete.append((touchedKey, touchedTime, colorName))
                        if (note[1].key, note[1].time - 1, note[1].color) == (touchedKey, touchedTime, colorName) and not note[1].lead:
                            note[1].lead = True
                    for itemToDelete in toDelete:
                        del noteMap[itemToDelete]
                    mouseTask = True

                ## Selecter - when statically pressed, selects the note. When dragged moves the note.
                # if there is a previously selected note, it is unselected unless shift is pressed while selecting

                # Dragging moves the note UNLESS the drag is done from the very tail end of the note, in which case
                # all selected notes are lengthened or shortened by the drag amount.
                
                elif brushType == "select" and colorName != 'all':
                    if not mouseTask: # mouse was just clicked
                        for note in noteMap.items():
                            noteMap[note[0]].originalKey = noteMap[note[0]].key
                            noteMap[note[0]].originalTime = noteMap[note[0]].time
                        mouseHoldStart = pygame.mouse.get_pos()
                        mouseCellStart = (touchedKey, touchedTime, colorName)
                        mouseTask = True
                    else:
                        try:
                            mouseCellStart
                        except NameError:
                            #console.log("mouseCellStart not defined -- a selection was not initialized.")
                            None
                        else:
                            if (not mouseCellStart in noteMap) and (timeOffset, keyOffset) == (0,0):
                                drawSelectBox = True
                            else:
                                if pygame.key.get_pressed()[pygame.K_LALT]:
                                    numSelected = False
                                    duplicatedNoteMap = {}
                                    for note in noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                            duplicatedNoteMap[note[0]] = copy.deepcopy(note[1]) # adds the selected notemap to the duplicated notemap until alt is let go
                                            duplicatedNoteMap[note[0]].color = colorName
                                    if mouseTask and numSelected:# and dist(pygame..mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((pygame.mouse.get_pos()[d] - mouseHoldStart[d]) / 
                                                                    (((width - leftColumn) / viewScaleX),(-innerHeight / viewScaleY))[d])
                                                                    for d in range(2) )
                                        delQ = []
                                        addQ = []
                                        refreshQ = False
                                        consistentKey = 0
                                        for note in duplicatedNoteMap.items():
                                            if duplicatedNoteMap[note[0]].selected:
                                                if consistentKey != 0 and consistentKey != duplicatedNoteMap[note[0]].key:
                                                    consistentKey = -1
                                                else:
                                                    consistentKey = duplicatedNoteMap[note[0]].key
                                                if duplicatedNoteMap[note[0]].key != duplicatedNoteMap[note[0]].originalKey + keyOffset or duplicatedNoteMap[note[0]].time != duplicatedNoteMap[note[0]].originalTime + timeOffset:
                                                    refreshQ = True
                                                duplicatedNoteMap[note[0]].key = duplicatedNoteMap[note[0]].originalKey + keyOffset
                                                duplicatedNoteMap[note[0]].time = duplicatedNoteMap[note[0]].originalTime + timeOffset
                                                delQ.append(note[0])
                                                addQ.append(((duplicatedNoteMap[note[0]].originalKey + keyOffset,
                                                            duplicatedNoteMap[note[0]].originalTime + timeOffset, colorName), note[1]))
                                        for delete in delQ:
                                            del duplicatedNoteMap[delete]
                                        for add in addQ:
                                            duplicatedNoteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if oldKeyOffset != keyOffset and consistentKey != -1 and consistentKey != 0:
                                            play_obj = sp.playNotes([addQ[0][0][0]], duration=0.07, waves=waveMap[colorName])
                                else:
                                    numSelected = False
                                    for note in noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                    if mouseTask and numSelected and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((pygame.mouse.get_pos()[d] - mouseHoldStart[d]) / 
                                                                    (((width - leftColumn) / viewScaleX),(-innerHeight / viewScaleY))[d])
                                                                    for d in range(2) )
                                        delQ = []
                                        addQ = []
                                        refreshQ = False
                                        consistentKey = 0
                                        for note in noteMap.items():
                                            if noteMap[note[0]].selected:
                                                if consistentKey != 0 and consistentKey != noteMap[note[0]].key:
                                                    consistentKey = -1
                                                else:
                                                    consistentKey = noteMap[note[0]].key
                                                if noteMap[note[0]].key != noteMap[note[0]].originalKey + keyOffset or noteMap[note[0]].time != noteMap[note[0]].originalTime + timeOffset:
                                                    refreshQ = True
                                                noteMap[note[0]].key = noteMap[note[0]].originalKey + keyOffset
                                                noteMap[note[0]].time = noteMap[note[0]].originalTime + timeOffset
                                                delQ.append(note[0])
                                                addQ.append(((noteMap[note[0]].originalKey + keyOffset,
                                                            noteMap[note[0]].originalTime + timeOffset, colorName), note[1]))
                                        for delete in delQ:
                                            del noteMap[delete]
                                        for add in addQ:
                                            noteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if oldKeyOffset != keyOffset and consistentKey != -1 and consistentKey != 0:
                                            play_obj = sp.playNotes([addQ[0][0][0]], duration=0.07, waves=waveMap[colorName])
                mouseWOTask = False
                mouseTask = True
    
    '''

    try:
        MasterPanel.update(screen)
    except pygame.error as e:
        traceback.print_exc()
        console.log('Pygame was likely quit outside of the main module. Handling and closing properly...\nIf this was unexpected, investigate.')
        running = False
        break
        

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            console.warn("Pygame was quit")
            
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(event.w, minWidth), max(event.h, minHeight)), pygame.RESIZABLE)
            width, height = (max(event.w, minWidth), max(event.h, minHeight))
        elif event.type == pygame.KEYDOWN:
            if event.key == CMD_KEY: # Switch to eraser momentarily
                brushType = "eraser"
                BrushButton.render(screen)
            elif event.key == pygame.K_LSHIFT: # Switch to select permanently
                brushType = "select"
                BrushButton.render(screen)
            elif event.key == pygame.K_SPACE: # Play / pause
                playing = not playing
                PlayPauseButton.render(screen)
                if playing:
                    #playHead.play()
                    lastPlayTime = time.time()
                else:
                    play_obj.stop()
                #playHead.tick = playHead.home
            elif event.key == pygame.K_s:
                if pygame.key.get_pressed()[CMD_KEY]: # if the user presses Ctrl+S (to save)
                    if workingFile == "": # file dialog to show up if the user's workspace is not attached to a file
                        filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
                        if filename != None:
                            filestring = filename.name
                            myPath = f"{source_path}/assets/workingfile.symphony"

                            worldMessage = fio.dumpToFile(filestring,
                                                        myPath,
                                                        sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap),
                                                        process,
                                                        autoSave,
                                                        titleText,
                                                        sessionID)

                            pathBytes = bytearray(myPath.read())
                            filename.write(pathBytes)
                            filename.close()
                            workingFile = filestring
                        else:
                            myPath = f"{source_path}/assets/workingfile.symphony"
                            worldMessage = fio.dumpToFile(myPath, myPath, sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap), process, autoSave, titleText, sessionID)
                    else: # save to workspace file
                        worldMessage = fio.dumpToFile(workingFile, myPath, sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap), process, autoSave, titleText, sessionID)
                    saveFrame = 0
        elif event.type == pygame.KEYUP:
            if event.key == CMD_KEY: # Switches away from eraser when Ctrl is let go
                brushType = "brush"
                BrushButton.render()
                for colorChannel in noteMap.items():
                    for note in colorChannel:
                        note.selected = False
                NotePanel.render()

    clock.tick(fps)
    pygame.display.flip()  # Update the display

if workingFile == "": # file dialog to show up if the user has unsaved changes (they have not attached the workspace to a file)
    filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
    if filename != None:
        filestring = filename.name
        myPath = f"{source_path}/assets/workingfile.symphony"

        worldMessage = fio.dumpToFile(filestring, myPath, sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap), process, autoSave, titleText, sessionID)

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()
        workingFile = filestring
    else:
        myPath = f"{source_path}/assets/workingfile.symphony"
        worldMessage = fio.dumpToFile(myPath, myPath, sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap), process, autoSave, titleText, sessionID)
else: # save all changes upon closing that have happened since the last autosave
    worldMessage = fio.dumpToFile(workingFile, workingFile, sl.newProgramState(key, mode, ticksPerTile, noteMap, waveMap), process, autoSave, titleText, sessionID)
    
# quit loop
pygame.quit()
sys.exit()