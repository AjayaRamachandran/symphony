###### IMPORT ######

import pygame
from io import BytesIO
import numpy as np
# import random
import ctypes
import copy
import cv2
from math import *
import time
from os import environ, path
#import os
# import json
import sys
import dill as pkl
from tkinter.filedialog import asksaveasfile #, asksaveasfilename
import sys
import json
from pathlib import Path
from soundfile import write as sfwrite

try:
    from ctypes import windll
    myappid = 'nimbial.symphony.editor.v1-0' # arbitrary string
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass # Not on Windows or ctypes is not available

### Handling Arguments
'''
SET ARGUMENTS:
"main.py" "instantiate" "filename" "folder" : does not start pygame, simply creates the file in the provided folder and exits
"main.py" "open" "filename" "folder" : starts program, opening file and establishing autosave bridge
"main.py" "retrieve" "filepath" "id" : gets all information about program and puts it into the json with the id
"main.py" "export" "filepath" "folder" : exports the file into the provided folder as a .wav

"main.py" "filename" : opens file with autosave bridge
"main.py" : starts program without autosave (NOT RECOMMENDED)
'''
def cleanse(string):
    stringCopy = string
    for l in range(len(stringCopy)):
        if not stringCopy[l] in 'abcdefghijklmnopqrstuvwxyzABCEDFGHIJKLMNOPQRSTUVWXYZ1234567890-_+(). ':
            stringCopy = stringCopy[:l] + '_' + stringCopy[l+1:]
    return stringCopy

autoSaveDirectory = json.load(open('src/assets/directory.json'))['Symphony Auto-Save'][0]['Auto-Save']

titleText = 'My Track 1'
process = ''
globalUUID = 0
sessionID = time.strftime('%Y-%m-%d %H%M%S')
print(f'Running with sysargv: {sys.argv}')

if len(sys.argv) > 4:
    print("Wrong usage: Too many arguments!")
    sys.exit(1)
if len(sys.argv) == 4:
    if sys.argv[1] == 'export':
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
elif len(sys.argv) == 2:
    workingFile = sys.argv[1]
else:
    workingFile = ""

###### (PYGAME &) WINDOW INITIALIZE ######

if (process == 'instantiate') or (process == 'retrieve') or (process == 'export'):
    environ["SDL_VIDEODRIVER"] = "dummy"

width, height = (1100, 592)
minWidth, minHeight = (1100, 592)
iconPath = 'inner/assets/icon32x32.png'
if path.exists(iconPath):
    gameIcon = pygame.image.load(iconPath)
    pygame.display.set_icon(gameIcon)
else:
    print(f"Warning: Icon file not found at {iconPath}")

pygame.init()
pygame.display.set_caption(f"{titleText} - Symphony v1.0 Beta")
#pygame.display.set_icon(pygame.image.load("src/assets/icon.png"))
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE, pygame.NOFRAME)

if (process == 'instantiate') or (process == 'retrieve'):
    None
else:
    pygame.display.flip()
    pygame.event.pump()
    time.sleep(0.1)

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected
SAMPLE_RATE = 44100
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)  # initialize pygame mixer at module import
transparentScreen = pygame.Surface((width, height), pygame.SRCALPHA)
otherNotes = pygame.Surface((width, height), pygame.SRCALPHA)
thisNote = pygame.Surface((width, height), pygame.SRCALPHA)
scrOrange = pygame.Surface((width, height), pygame.SRCALPHA)
scrPurple = pygame.Surface((width, height), pygame.SRCALPHA)
scrCyan = pygame.Surface((width, height), pygame.SRCALPHA)
scrLime = pygame.Surface((width, height), pygame.SRCALPHA)
scrBlue = pygame.Surface((width, height), pygame.SRCALPHA)
scrPink = pygame.Surface((width, height), pygame.SRCALPHA)
scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]
clock = pygame.time.Clock()
fps = 60

# imports font styles
TITLE1 = pygame.font.Font("inner/InterVariable.ttf", 60)
HEADING1 = pygame.font.Font("inner/InterVariable.ttf", 24)
SUBHEADING1 = pygame.font.Font("inner/InterVariable.ttf", 14)
BODY = pygame.font.Font("inner/InterVariable.ttf", 14)
SUBSCRIPT1 = pygame.font.Font("inner/InterVariable.ttf", 11)

bytes_io = BytesIO()

###### ASSETS ######

playImage = pygame.image.load("inner/assets/play.png")
pauseImage = pygame.image.load("inner/assets/pause.png")
headImage = pygame.image.load("inner/assets/head.png")
brushImage = pygame.image.load("inner/assets/brush.png")
eraserImage = pygame.image.load("inner/assets/eraser.png")
negaterImage = pygame.image.load("inner/assets/negater.png")
rainbowImage = pygame.image.load("inner/assets/rainbow.png")

squareWaveImage = pygame.image.load("inner/assets/square.png")
sawtoothWaveImage = pygame.image.load("inner/assets/sawtooth.png")
triangleWaveImage = pygame.image.load("inner/assets/triangle.png")
waveImages = [squareWaveImage, triangleWaveImage, sawtoothWaveImage]

upChevronImage = pygame.image.load("inner/assets/up.png")
downChevronImage = pygame.image.load("inner/assets/down.png")

###### VARIABLES INITIALIZE ######

page = "Editor"
noteMap = {}

tick = 0
tickInterval = 10

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
noteCount = 128
noteRange = 60
modesIntervals = [
    ["Lydian",        [0, 2, 4, 6, 7, 9, 11]],
    ["Ionian (maj.)", [0, 2, 4, 5, 7, 9, 11]],
    ["Mixolydian",    [0, 2, 4, 5, 7, 9, 10]],
    ["Dorian",        [0, 2, 3, 5, 7, 9, 10]],
    ["Aeolian (min.)",[0, 2, 3, 5, 7, 8, 10]],
    ["Phrygian",      [0, 1, 3, 5, 7, 8, 10]],
    ["Locrian",       [0, 1, 3, 5, 6, 8, 10]]
]
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
worldMessage = ""

toolbarHeight = 80
leftColumn = 60
innerHeight = height - toolbarHeight
globalVolume = 0.3

viewRow = 50.01
viewColumn = 0.01
#print(innerHeight)
viewScaleX = (width - leftColumn) / 32 # old value = 32
viewScaleY = innerHeight // 32 # old value = 16
dRow = 0
dCol = 0
timeInterval = 4

notes = []
duplicatedNoteMap = {}
currentDraggingKey = 0
initialDraggingTime = 0

mouseTask = False
mouseDownTime = time.time()
mouseWOTask = True
mouseHoldStart = []
lastPlayTime = time.time()

timeOffset = 0
keyOffset = 0
oldKeyOffset = 0

saveFrame = 0

drawSelectBox = False
mouseFirstDown = True

###### CLASSES ######

class TextBox():
    '''Class to contain text boxes, which are used for interactivity.'''

    def __init__(self, pos, width, height, text, textSize = SUBHEADING1):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.selected = False
        self.text = text
        globalTextBoxes.append(self)

    def mouseClicked(self):
        '''Method to return whether the textbox has been clicked'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not mouseTask
    
    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0]

    def draw(self, text):
        '''Method to draw a textbox.'''
        pygame.draw.rect(screen, mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        if self.selected:
            showBar = round(time.time())%2 == 0
            stamp(text + ("|" if showBar else ""), self.textSize, self.x + self.width/2 + showBar*2.5, self.y - showBar*1, 0.4, "center")
        else:
            stamp(text, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
        pygame.draw.rect(screen, (self.selected * 80, self.selected * 80, self.selected * 80), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)

class Button():
    '''Class to contain buttons, which are used for interactivity.'''

    def __init__(self, pos, width, height, textSize = SUBHEADING1, color = (30, 30, 30), colorCycle = None):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.colorCycle = colorCycle
        self.color = colorCycle[0] if colorCycle != None else color
        self.colorIndex = 0

    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0]

    def mouseClicked(self):
        '''Method to return whether the button has been clicked'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not mouseTask
    
    def draw(self, itemToDraw = None):
        '''Method to draw a button.'''
        if self.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

        if self.colorCycle != None:
            pygame.draw.rect(screen, self.color, (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
            stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")
        else:
            pygame.draw.rect(screen, mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
    
        if self.colorCycle == None:
            if type(itemToDraw) == str:
                stamp(itemToDraw, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
            else:
                screen.blit(itemToDraw, (self.x + self.width/2 - 8, self.y - 8))
        else:
            if type(itemToDraw) == pygame.Surface:
                screen.blit(itemToDraw, (self.x + self.width/2 - 14, self.y - 14))
                pygame.draw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
                stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")

    def setColor(self, index):
        '''Sets to given color'''
        self.color = justColors[index]
        self.colorIndex = index

    def nextColor(self):
        '''Switches to next color (color switcher)'''
        nextIndex = (justColors.index(self.color) + 1) % (len(colors.items()))
        self.color = justColors[nextIndex]
        self.colorIndex = (self.colorIndex + 1) % 7

    def getColorName(self):
        '''Returns the color in string form of the Button (used for color switching)'''
        i = justColors.index(self.color)
        return justColorNames[i]

class Head():
    '''Class to contain the playhead, which plays the music.'''

    def __init__(self, speed:int, tick:int, home:int = 0):
        self.speed = speed
        self.tick = tick
        self.home = home # home is the time that the head returns to when restarted (default 0)

    def draw(self, screen, viewRow, viewColumn, leftColW, tileW, drawHead=False): # by default, only draws home
        '''Method to draw the playhead.'''
        if drawHead:
            top = [((((time.time() - lastPlayTime) * 60)/ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [((((time.time() - lastPlayTime) * 60)/ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (0, 255, 255), top, bottom, 1)

        if self.home != 0:
            top = [(self.home * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [(self.home * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (255, 255, 0), top, bottom, 1)

    def play(self):
        '''Method to play the playhead -- contains audio playback'''
        global play_obj
        phases = {}
        finalWave = np.array([], dtype=np.int16)

        for tempTick in range(floor(self.home) + 1, noteCount):
            playingNotes = [
                (note.key, note.lead, note.color)
                for note in noteMap.values()
                if note.time == tempTick and (note.color == colorName or colorName == 'all')
            ]
            chunk, phases = assembleNotes(playingNotes, phases, duration=ticksPerTile/60)
            finalWave = np.concatenate([finalWave, chunk])

        sound = toSound(finalWave)
        play_obj = sound.play()

class Note():
    '''Class to contain the Note, which represents a grid element that *does* have a sound when played.'''

    def __init__(self, key:int, time:int, lead:bool, color:str = "orange"):
        self.key = key
        self.time = time
        self.lead = lead
        self.color = color
        self.originalKey = key
        self.originalTime = time
        self.selected = False
        self.extending = False
        self.SScoords = [0, 0]
    
    def __str__(self):
        '''String representation of Note'''
        return f'''Note object with attrs: [key: {self.key}, time: {self.time}, lead: {self.lead}, selected: {self.selected}, originalKey: {self.originalKey}, originalTime: {self.originalTime}]'''

    def setSScoords(self, x, y):
        '''Sets the screenspace coordinates of a note to the given arguments'''
        self.SScoords = [x, y]

    def draw(self, screen, viewRow, viewColumn, noteMap, transparent = False):
        '''Method to draw the note.'''
        global viewScaleX, viewScaleY

        opacity = 130
        def darkenColor(init, amt):
            return [init[n] - (amt * (n!=3)) for n in range(len(init))] # darkens a tuple by a constant n, if init is a quadtuple with opacity, alpha is untouched.
        if self.color == colorButton.getColorName() or colorButton.getColorName() == "all":
            leadColor = colors[self.color] if not transparent else (*colors[self.color], opacity)
            outlineColor = (255, 255, 255) if not transparent else (0, 0, 0, 0)
            tailsDarkness = 20
        else:
            leadColor = (80, 80, 80) if not transparent else (80, 80, 80, opacity)
            outlineColor = (255, 255, 255) if not transparent else (0, 0, 0, 0)
            tailsDarkness = 5
        tailColor = darkenColor(leadColor, tailsDarkness)
        black = (0, 0, 0) if not transparent else (0, 0, 0, 0)

        numToOffset = 0
        nextKeyNumToOffset = 0
        if colorName == 'all':
            colorsToSearch = justColorNames[:justColorNames.index(self.color)]
            for colorI in colorsToSearch:
                if (self.key, self.time, colorI) in noteMap:
                    numToOffset += 1
                if (self.key, self.time, colorI) in noteMap:
                    nextKeyNumToOffset += 1

        headerY = toolbarHeight + ((viewRow - self.key) * innerHeight/viewScaleY) - numToOffset * 3
        headerX = leftColumn + ((self.time - viewColumn - 1) * (width - leftColumn)/viewScaleX) - numToOffset * 3
        self.setSScoords(headerX + (width - leftColumn)/viewScaleX/2, headerY + innerHeight/viewScaleY/2)

        if self.lead:
            pygame.draw.rect(screen, leadColor,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), border_radius=3)
            pygame.draw.rect(screen, black,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), 1, 3)
            if self.selected:
                pygame.draw.line(screen, outlineColor, # top edge
                         (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                pygame.draw.line(screen, outlineColor, # left edge
                         (headerX - 1, headerY - 1), (headerX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                pygame.draw.line(screen, outlineColor, # bottom edge
                         (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                if not (self.key, self.time + 1, self.color) in noteMap:
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
        else:
            pygame.draw.rect(screen, tailColor,
                         (headerX - 1, headerY, (width - leftColumn)/viewScaleX + 1, innerHeight/viewScaleY))
            pygame.draw.line(screen, black, # top edge
                        (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 1)
            pygame.draw.line(screen, black, # bottom edge
                        (headerX - 1, headerY + floor(innerHeight/viewScaleY)), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + floor(innerHeight/viewScaleY)), 1)
            if (self.key, self.time + 1, self.color) in noteMap and noteMap[(self.key, self.time + 1, self.color)].lead == False:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                if nextKeyNumToOffset < numToOffset:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
            else:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                else:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
        
        if self.extending:
            pygame.draw.line(screen, (0, 255, 0), # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)

def toNote(note: Note):
    '''Function to convert old notes (before color was added) into new color'''
    try:
        color = note.color
    except:
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
        print(f"Updated ProgramState with key {key} and mode {mode}.")

def toProgramState(state : ProgramState):
    '''Maps a (potentially) old program state to a new one for backwards compatibility'''
    try:
        stateMkey = state.key
    except:
        stateMkey = "Eb"

    try:
        statemode = state.mode
    except:
        statemode = "Lydian"

    try:
        stateWaves = state.waveMap
    except:
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


if workingFile == "" or process == 'instantiate': # if the workingfile is not provided or we are creating a new file, initialize a new program state
    ps = ProgramState(10, noteMap, "Eb", "Lydian", waveMap)
else:
    ps = toProgramState(pkl.load(open(workingFile, "rb")))

if process == 'retrieve':
    print('DUMPING INTO RESPONSE.JSON')
    responseLoc = open('inner/src/response.json', 'w')
    print(ps.noteMap)
    json.dump({ 'fileInfo' : {
                  'Key' : ps.key,
                  'Mode' : ps.mode,
                  'Tempo (tpm)' : round(3600 / ps.ticksPerTile, 2),
                  'Empty?' : (ps.noteMap == {}),
                  }, 'id': globalUUID
               }, responseLoc)
    responseLoc.close()
    sys.exit()

noteMap = ps.noteMap
ticksPerTile = ps.ticksPerTile
waveMap = ps.waveMap
key = ps.key
if "b" in key:
    keyIndex = NOTES_FLAT.index(key)
    accidentals = "flats"
else:
    keyIndex = NOTES_SHARP.index(key)
    accidentals = "sharps"
mode = ps.mode
modeIntervals = set(modesIntervals[0][1])

globalTextBoxes = []

playPauseButton = Button(pos=(33, 40), width=60, height=28)
accidentalsButton = Button(pos=(120, 40), width=60, height=28)
playheadButton = Button(pos=(207, 40), width=60, height=28)
keyButton = Button(pos=(width - 260, 40), width=40, height=28)
modeButton = Button(pos=(width - 220, 40), width=100, height=28)
brushButton = Button(pos=(width - 93, 40), width=60, height=28)
colorButton = Button(pos=(width - 345, 40), width=28, height=28, colorCycle=justColors)
waveButton = Button(pos=(width - 317, 40), width=28, height=28)

timeSigDownButton = Button(pos=(width - 420, 40), width=20, height=28)
timeSigTextBox = TextBox(pos=(width - 400, 40), width=30, height=28, text='4')
timeSigUpButton = Button(pos=(width - 370, 40), width=20, height=28)
tempoDownButton = Button(pos=(300, 40), width=20, height=28)
tempoTextBox = TextBox(pos=(320, 40), width=105, height=28, text='360')
tempoUpButton = Button(pos=(425, 40), width=20, height=28)

###### FUNCTIONS ######

def dumpToFile(file, directory):
    '''Saves data to the working file, used in many places in the code'''
    global worldMessage

    # when saving, repair any discrepancies between hashmap key and obj data (rare but fatal)
    delQ, addQ = [], []
    for thing in noteMap.items():
        if (thing[1].key, thing[1].time, thing[1].color) != thing[0]:
            print("A discrepancy was found between hashmap and obj data. Repairing (prioritizing obj data) now...")
            print(f"Discrepancy details -- HM Key: {thing[0]}, Obj Data: {(thing[1].key, thing[1].time, thing[1].color)}")
            addQ.append([(thing[1].key, thing[1].time, thing[1].color), thing[1]])
            delQ.append(thing[0])
        
        if (thing[1].key < 2):
            delQ.append(thing[0])
    for item in delQ:
        del noteMap[item]
    for item in addQ:
        noteMap[item[0]] = item[1]

    epochSeconds = time.time() # get current time in epoch seconds
    localTime = time.localtime(epochSeconds)
    readableTime = time.strftime('%Y-%m-%d at %H:%M:%S', localTime)

    ps.updateAttributes(noteMap, ticksPerTile, key, mode, waveMap)
    pkl.dump(ps, file, -1)
    pkl.dump(ps, open(autoSaveDirectory + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb'), -1)

    worldMessage = (f"Last Saved {readableTime} to " + directory) if directory != "inner/assets/workingfile.symphony" else "You have unsaved changes - Please save to a file on your PC."

if process == 'instantiate':
    dumpToFile(open(workingFile, 'wb'), workingFile)
    sys.exit()

def inBounds(coords1, coords2, point) -> bool:
    '''Returns whether a point is within the bounds of two other points. order is arbitrary.'''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def processImage(imageBytes):
    '''Takes in an image bytes and blurs it'''
    image = cv2.imdecode(np.frombuffer(imageBytes, np.uint8), cv2.IMREAD_COLOR)
    blurredImage = cv2.GaussianBlur(image, (51, 51), 0) # apply a heavy blur to the image
    
    height, width = blurredImage.shape[:2]
    croppedImage = blurredImage[:, :300]
    
    _, buffer = cv2.imencode('.jpg', croppedImage) # encode the image to a BytesIO object
    imageIO = BytesIO(buffer)
    return imageIO

def notesToFreq(notes):
    '''Converts a set of notes (as ints from C2) to frequencies'''
    freqs = []
    C2 = 65.41
    ratio = 1.05946309436
    for note in notes:
        noteFreq = C2 * (ratio ** (note - 1))
        freqs.append(noteFreq)
    return freqs

def toSound(array_1d: np.ndarray, returnType='Sound'):# -> pygame.mixer.Sound:
    '''Convert a 1-D int16 numpy array into a 2-D array matching mixer channels, then wrap into a Sound.'''
    freq, fmt, nchan = pygame.mixer.get_init()
    if nchan == 1:
        arr2d = array_1d.reshape(-1, 1)
    else:
        # duplicate mono into both LR for stereo
        arr2d = np.column_stack([array_1d] * nchan)
    return pygame.sndarray.make_sound(arr2d) if returnType == 'Sound' else arr2d

def exportToWav(arr2d: np.ndarray, filename: str, sample_rate: int = 44100): # filename is actually the filepath
    '''Take a 2-D array and write it to a WAV file using soundfile library. If file exists, appends an incrementing number to the filename.'''
    base, ext = path.splitext(filename)
    candidate = filename
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    sfwrite(candidate, arr2d, sample_rate, subtype='PCM_16')

def playNotes(notes, duration=1, waves=0, volume=0.2, sample_rate=SAMPLE_RATE):
    '''Single set of notes playback, does not keep track of phase.'''
    global play_obj
    try:
        freqs = notesToFreq(notes)
        counts = {}
        for f in freqs:
            counts[f] = counts.get(f, 0) + 1

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.zeros_like(t)

        for freq, mag in counts.items():
            if waves == 0:
                part = np.sign(np.sin(2 * np.pi * freq * t)) * mag
            elif waves == 1:
                part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t)) * mag
            else:
                part = 2 * (t * freq - np.floor(0.5 + t * freq)) * mag
            wave += part

        # normalize + volume
        wave = wave/np.max(np.abs(wave)) - (0.6*wave/(np.max(np.abs(wave))**2))
        wave *= volume * globalVolume

        audio = (wave * 32767).astype(np.int16)
        sound = toSound(audio)
        play_obj = sound.play()
    except Exception as e:
        print(f"NoteError: {e}")

def assembleNotes(notes, phases, duration=1, volume=0.2, sample_rate=SAMPLE_RATE):
    '''Compound notes playback, tracks phase to keep continuous notes'''
    freqs = notesToFreq([n[0] for n in notes])
    inColors = [n[2] for n in notes]

    counts = {}
    for idx, f in enumerate(freqs):
        typ = waveMap[inColors[idx]]
        counts[(f, typ)] = counts.get((f, typ), 0) + 1

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    newPhases = {}
    wave = np.zeros_like(t)
    #seen = set()

    phasesOfFreqs = {}

    for idx, freq in enumerate(freqs):
        typ = waveMap[inColors[idx]]
        phase = phases.get(freq, 0.0)
        if notes[idx][1]:
            phase += pi
        if freq in phasesOfFreqs:
            phase = phasesOfFreqs[freq]
        else:
            phasesOfFreqs[freq] = phase
        #if (freq, typ) in seen:
            #continue

        if typ == 0: # square wave
            part = np.sign(np.sin(2 * np.pi * freq * t + phase)) * counts[(freq, typ)]
        elif typ == 1: # triangle wave
            part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t + phase)) * counts[(freq, typ)]
        else: # sawtooth wave
            part = 2 * (t * freq + (phase / (2 * pi)) - np.floor(0.5 + t * freq + (phase / (2 * pi)))) * counts[(freq, typ)]

        wave += part
        #seen.add((freq, typ))
        newPhases[freq] = (phase + 2 * np.pi * freq * duration) % (2 * np.pi) # increments phase to keep it continuous

    # normalize + volume
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
    wave *= volume * globalVolume

    audio = (wave * 32767).astype(np.int16)
    return audio, newPhases

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
        chunk, phases = assembleNotes(playingNotes, phases, duration=ticksPerTile/60)
        finalWave = np.concatenate([finalWave, chunk])

    arr2d = toSound(finalWave, returnType='2DArray')
    exportToWav(arr2d, destination + '/' + path.splitext(path.basename(workingFile))[0] + '.wav', sample_rate=44100)
    sys.exit()

def stamp(text, style, x, y, luminance, justification = "left"):
    '''Function to draw text to the screen abstracted, makes text drawing easy.'''
    text = style.render(text, True, (round(luminance*255), round(luminance*255), round(luminance*255)))
    if justification == "left":
        textRect = (x, y, text.get_rect()[2], text.get_rect()[3])
    elif justification == "right":
        textRect = (x - text.get_rect()[2], y, text.get_rect()[2], text.get_rect()[3])
    else:
        textRect = (x - (text.get_rect()[2]/2), y - (text.get_rect()[3]/2), text.get_rect()[2], text.get_rect()[3])
    screen.blit(text, textRect)

def mouseFunction(rect):
    '''Function that returns (2 things) whether or not the mouse is in the bounding box, as well as a color.'''
    isInside = rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]
    return isInside, ((20, 20, 20) if isInside and pygame.mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

def reevaluateLeads():
    '''Recalculates which notes are considered lead notes.'''
    for note in noteMap.items():
        if colorName == note[1].color:
            if not ((note[0][0], note[0][1] - 1, colorName) in noteMap):
                noteMap[note[0]].lead = True

def unselectTextBoxes():
    '''Loops through all text boxes and unselects them.'''
    for tb in globalTextBoxes:
        tb.selected = False

def sameNoteMaps(noteMap1, noteMap2):
    '''Compares two notemaps by value (not reference), used for change history (Ctrl+Z)'''
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

###### MAINLOOP ######
running = True
playHead = Head(0, 1, 0)
tempo = int(round(3600 / ps.ticksPerTile))
lastNoteTime = 0
ctrlZTime = 59
noteMapVersionTracker = []
noteMapFutureVersionTracker = []

while running:
    saveFrame += 60 * (1 / fps)
    if saveFrame > 1200: # Saves every 20 seconds
        saveFrame = 0
        myPath = open(workingFile if workingFile != "" else "inner/assets/workingfile.symphony", "wb")
        dumpToFile(myPath, workingFile if workingFile != "" else "inner/assets/workingfile.symphony")
        myPath.close()
    # checks if new changes have been made, if so adds them to the version history for Ctrl+Z
    ctrlZTime += 1
    if ctrlZTime > 60:
        for note in noteMap.items():
            lastNoteTime = max(lastNoteTime, note[1].time)
            noteCount = max(noteCount, lastNoteTime + 20)

        if not pygame.mouse.get_pressed()[0]:
            if noteMapVersionTracker == [] or not any(sameNoteMaps(noteMapVersionTracker[-i], noteMap) for i in range(1, len(noteMapVersionTracker) + 1)):
                noteMapVersionTracker.append(copy.deepcopy(noteMap))
                noteMapFutureVersionTracker = []
            if len(noteMapVersionTracker) > 32:
                noteMapVersionTracker.pop(0)
            ctrlZTime = 0
    screen.fill((0, 0, 0))
    transparentScreen.fill((0, 0, 0, 0))

    colorName = colorButton.getColorName()

    for row in range(ceil(viewScaleY) + 1):
        headerY = row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/viewScaleY) - innerHeight/viewScaleY
        headerX = leftColumn - (viewColumn%1 * (width - leftColumn)/viewScaleX) - (width - leftColumn)/viewScaleX
        for column in range(ceil(viewScaleX) + 2):
            cm = (floor((column+viewColumn)%timeInterval) == 0) * 8
            pygame.draw.rect(screen, ((28 + cm, 28 + cm, 28 + cm) if not (-(floor(row - viewRow) + keyIndex + 1) % 12) in modeIntervals else (43 + cm, 43 + cm, 43 + cm)),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), 1, 3)
            headerX += (width - leftColumn)/viewScaleX

            ##### BRUSH CONTROLS #####
            if mouseFunction((headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY))[0] and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)):
                touchedKey, touchedTime = floor(viewRow - row + 1), floor(column + viewColumn + 1)
                if not mouseTask:
                    mouseDownTime = time.time() # sets mouse start down time

                ## Head - means that selecting time stamp
                if head:
                    if not mouseTask:
                        playHead.home = (touchedTime - 1)
                        mouseTask = True
                ## Brush - unconditionally adds notes to the track
                elif brushType == "brush" and colorName != 'all':
                    if not mouseTask and not (touchedKey, touchedTime, colorName) in noteMap:
                        playNotes([touchedKey], duration=0.25, waves=waveMap[colorName])
                        noteMap[(touchedKey, touchedTime, colorName)] = Note(touchedKey, touchedTime, True, color=colorName)
                        currentDraggingKey = touchedKey
                        initialDraggingTime = touchedTime
                    #reevaluateLeads()
                    mouseTask = True
                    if (not (currentDraggingKey, touchedTime, colorName) in noteMap) and touchedTime > initialDraggingTime:
                        noteMap[(currentDraggingKey, touchedTime, colorName)] = Note(currentDraggingKey, touchedTime, False, color=colorName)
                        tempOffsetTime = touchedTime - 1
                        while (not (tempOffsetTime, touchedTime, colorName) in noteMap) and tempOffsetTime > initialDraggingTime + 1:
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
                            #print("mouseCellStart not defined -- a selection was not initialized.")
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
                                    if mouseTask and numSelected:# and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((pygame.mouse.get_pos()[d] - mouseHoldStart[d]) / 
                                                                    (((width-leftColumn)/viewScaleX),(-innerHeight/viewScaleY))[d])
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
                                            playNotes([addQ[0][0][0]], duration=0.07, waves=waveMap[colorName])
                                else:
                                    numSelected = False
                                    for note in noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                    if mouseTask and numSelected and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((pygame.mouse.get_pos()[d] - mouseHoldStart[d]) / 
                                                                    (((width-leftColumn)/viewScaleX),(-innerHeight/viewScaleY))[d])
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
                                            playNotes([addQ[0][0][0]], duration=0.07, waves=waveMap[colorName])
                mouseWOTask = False
                mouseTask = True

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
    for note in noteMap.items():
        if note[1].key > viewRow - viewScaleY and note[1].key < viewRow + 1:
            if note[1].time > viewColumn and note[1].time < viewColumn + viewScaleX + 1:
                if colorName == 'all':
                    if not (note[1].color in scrUsed):
                        scrUsed.add(scrList[colorsInd[note[1].color]])
                    #note[1].draw(screen, viewRow, viewColumn, noteMap)
                    note[1].draw(scrList[colorsInd[note[1].color]], viewRow, viewColumn, noteMap)
                else:
                    if note[1].color == colorName:
                        note[1].draw(thisNote, viewRow, viewColumn, noteMap)
                    else:
                        note[1].draw(otherNotes, viewRow, viewColumn, noteMap)
    
    if colorName == 'all':
        # render notes in order of stack
        for scr in scrList:
            if scr in scrUsed:
                screen.blit(scr, scr.get_rect())
    else:
        # always renders current color on top of gray ones
        screen.blit(otherNotes, otherNotes.get_rect())
        screen.blit(thisNote, thisNote.get_rect())
     
    for note in duplicatedNoteMap.items():
        if note[1].key > viewRow - viewScaleY and note[1].key < viewRow + 1:
            if note[1].time > viewColumn and note[1].time < viewColumn + viewScaleX + 1:
                note[1].draw(transparentScreen, viewRow, viewColumn, duplicatedNoteMap, transparent=True)

    if drawSelectBox:
        pygame.draw.rect(screen, (255, 255, 255), (min(mouseHoldStart[0], pygame.mouse.get_pos()[0]),
                                                                       min(mouseHoldStart[1], pygame.mouse.get_pos()[1]),
                                                                       abs(pygame.mouse.get_pos()[0] - mouseHoldStart[0]),
                                                                       abs(pygame.mouse.get_pos()[1] - mouseHoldStart[1])), 1)

    # functionality to move playhead and draw it when it is moving
    if playing:
        playHead.tick += 1 * 60/fps
        playHead.draw(screen, viewRow, viewColumn, leftColumn, (width - leftColumn)/viewScaleX, drawHead=True)
    else:
        playHead.draw(screen, viewRow, viewColumn, leftColumn, (width - leftColumn)/viewScaleX)

    for row in range(ceil(viewScaleY) + 1):
        headerX, headerY = 0, row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/viewScaleY) - innerHeight/viewScaleY
        note = f"{(NOTES_SHARP if accidentals == 'sharps' else NOTES_FLAT)[floor((viewRow - row) % 12)]} {floor((viewRow - row) / 12) + 2}"
        pygame.draw.rect(screen, ((43, 43, 43) if floor((row - viewRow)%2) == 0 else (51, 51, 51)),
                         (headerX, headerY, leftColumn, innerHeight/viewScaleY), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0),
                         (headerX, headerY, leftColumn, innerHeight/viewScaleY), 1, 3)
        stamp(note, SUBHEADING1, headerX + 5, headerY + 5, 0.4)

        if mouseFunction((0, headerY, leftColumn, innerHeight/viewScaleY))[0] and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)) and not mouseTask:
            # mouse is clicking the note labels
            mouseTask = True
            playNotes([floor(viewRow - row + 1)], duration=0.25, waves=waveMap[colorName])

    def renderScrollBar():
        '''Function to draw the bottom scroll bar on the screen for navigating horizontally.'''
        global viewColumn
        scrollBarHeight = 15
        scrollBarColor = (100, 100, 100)
        progressLeft = viewColumn / noteCount
        progressRight = (viewColumn + viewScaleX) / noteCount
        mouseDel = pygame.mouse.get_rel()[0]/(width - leftColumn) * noteCount

        if pygame.mouse.get_pos()[1] > height - 80:
            if ((width - leftColumn) * progressLeft) + leftColumn < pygame.mouse.get_pos()[0] < ((width - leftColumn) * progressRight) + leftColumn and pygame.mouse.get_pos()[1] > height - scrollBarHeight - 15:
                # mouse is touching scroll bar
                if pygame.mouse.get_pressed()[0]:
                    # mouse is dragging scroll bar
                    scrollBarColor = (255, 255, 255)
                    if not mouseTask:
                        viewColumn += mouseDel
                else:
                    scrollBarColor = (150, 150, 150)
            else:
                # mouse is close to screen bottom
                scrollBarColor = (100, 100, 100)
        else:
            scrollBarHeight = 10

        pygame.draw.rect(screen, scrollBarColor, (((width - leftColumn) * progressLeft) + leftColumn,
                                                  height - scrollBarHeight - 3,
                                                  (width - leftColumn) * (progressRight - progressLeft),
                                                  scrollBarHeight), 1, 3)

    def renderToolBar():
        '''Renders the top toolbar, and all of the elements inside of it.'''
        global accidentals, mouseTask, playing, head, brushType, key, keyIndex, mode, modeIntervals, lastPlayTime, timeInterval, ticksPerTile, tempo
        pygame.draw.rect(screen, (43, 43, 43), (0, 0, width, toolbarHeight))
        pygame.draw.line(screen, (0, 0, 0), (0, toolbarHeight), (width, toolbarHeight))
        pygame.draw.line(screen, (30, 30, 30), (0, toolbarHeight - 1), (width, toolbarHeight - 1))
        pygame.draw.line(screen, (49, 49, 49), (0, toolbarHeight - 2), (width, toolbarHeight - 2))
        pygame.draw.line(screen, (45, 45, 45), (0, toolbarHeight - 3), (width, toolbarHeight - 3))

        ### TRACK TITLE BAR
        pygame.draw.rect(screen, (0, 0, 0), (width/2 - 80, toolbarHeight/2 - 14, 160, 28), 1, 3)
        stamp(titleText, SUBHEADING1, width/2, 40, 0.4, "center")
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        ### PLAY/PAUSE BUTTON
        playPauseButton.x = 33
        if playPauseButton.mouseClicked():
            playing = not playing
            if playing:
                playHead.play()
                lastPlayTime = time.time()
            else:
                play_obj.stop()
            mouseTask = True
            playHead.tick = playHead.home
        playPauseButton.draw(pauseImage if playing else playImage)

        ### ACCIDENTALS BUTTON
        accidentalsButton.x = 120
        if accidentalsButton.mouseClicked():
            keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
            key = (NOTES_FLAT if accidentals == "sharps" else NOTES_SHARP)[keyIndex]
            accidentals = ("sharps" if accidentals == "flats" else "flats")
            mouseTask = True
        accidentalsButton.draw(accidentals)
        
        ### PLAYHEAD BUTTON
        playheadButton.x = 207
        if playheadButton.mouseClicked():
            head = not head
            mouseTask = True
        playheadButton.draw(headImage)

        ### COLOR BUTTON
        colorButton.x = width - 345
        if colorButton.mouseClicked():
            colorButton.nextColor()
            mouseTask = True
        if colorButton.getColorName() == "all":
            colorButton.draw(rainbowImage)
        else:
            colorButton.draw()

        ### WAVE BUTTON
        waveButton.x = width - 317
        if waveButton.mouseClicked():
            waveMap[colorName] = (waveMap[colorName] + 1) % len(waveTypes)
            mouseTask = True
        if colorName != 'all': # doesn't render the wave type for 'all' since it is irrelevant
            waveButton.draw(waveImages[waveMap[colorName]])

        ### KEY BUTTON
        keyButton.x = width - 260
        if keyButton.mouseClicked():
            keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
            key = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT)[keyIndex + 1 if keyIndex != 11 else 0]
            keyIndex = keyIndex + 1 if keyIndex != 11 else 0
            mouseTask = True
        keyButton.draw(key)

        ### MODE BUTTON
        modeButton.x = width - 220
        if modeButton.mouseClicked():
            modeIndex = next(i for i, (x, _) in enumerate(modesIntervals) if x == mode)
            mode = modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][0]
            modeIntervals = set(modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][1])
            mouseTask = True
        modeButton.draw(mode)

        ### BRUSH/ERASER/NEGATER BUTTON
        brushButton.x = width - 93
        if brushButton.mouseClicked():
            if brushType == "brush":
                brushType = "eraser"
            elif brushType == "eraser":
                brushType = "select"
            else:
                brushType = "brush"
                for note in noteMap.items():
                    note[1].selected = False
            mouseTask = True
        brushButton.draw("select" if brushType == "select" else brushImage if brushType == "brush" else eraserImage)

        ### TIME SIGNATURE CONTROLS
        timeSigUpButton.x = width - 395
        timeSigUpButton.draw(upChevronImage)
        if timeSigUpButton.mouseClicked():
            timeInterval += 1
            mouseTask = True
        timeSigTextBox.x = width - 425
        if timeSigTextBox.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        if timeSigTextBox.mouseClicked():
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
                unselectTextBoxes()
            timeSigTextBox.selected = True
        timeSigTextBox.draw(str(timeSigTextBox.text))
        if timeSigTextBox.selected:
            timeInterval = 1 if (timeSigTextBox.text == '' or int(timeSigTextBox.text) == 0) else int(timeSigTextBox.text)
        else:
            timeSigTextBox.text = str(timeInterval)

        timeSigDownButton.x = width - 445
        timeSigDownButton.draw(downChevronImage)
        if timeSigDownButton.mouseClicked():
            timeInterval = max(1, timeInterval - 1)
            mouseTask = True

        ### TEMPO CONTROLS
        tempoUpButton.x = 425
        tempoUpButton.draw(upChevronImage)
        if tempoUpButton.mouseClicked():
            tempo += 1
            mouseTask = True

        tempoTextBox.x = 320
        if tempoTextBox.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        if tempoTextBox.mouseClicked():
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
                unselectTextBoxes()
            tempoTextBox.text = ''
            tempoTextBox.selected = True
        if tempoTextBox.selected:
            ticksPerTile = 3600 / tempo
            tempo = 1 if (tempoTextBox.text == '' or int(tempoTextBox.text) == 0) else int(tempoTextBox.text)
        else:
            tempoTextBox.text = str(tempo)
        tempoTextBox.draw(str(tempoTextBox.text) + ' tpm')

        tempoDownButton.x = 300
        tempoDownButton.draw(downChevronImage)
        if tempoDownButton.mouseClicked():
            tempo = max(1, tempo - 1)
            mouseTask = True

    renderScrollBar()
    renderToolBar()
            
    tick += 1 - (tick == tickInterval - 1) * tickInterval
    if tick == tickInterval - 1:
        None

    def selectConnected(key, time):
        '''Function to take in a key and time and select all connected notes, and return whether a note exists at that key and time'''
        noteExists = False
        deviation = 0
        while (key, time + deviation, colorName) in noteMap:
            noteExists = True
            noteMap[(key, time + deviation, colorName)].selected = True
            if noteMap[(key, time + deviation, colorName)].lead == True:
                noteMap[(key, time + deviation, colorName)].selected = True
                break
            deviation -= 1
        deviation = 1
        while (key, time + deviation, colorName) in noteMap:
            noteExists = True
            if noteMap[(key, time + deviation, colorName)].lead == True:
                break
            noteMap[(key, time + deviation, colorName)].selected = True
            deviation += 1
        return noteExists

    if not pygame.mouse.get_pressed()[0] and not mouseWOTask:
        reevaluateLeads()
        ### Unclicked
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        if head:
            head = False
        try:
            mouseCellStart
        except NameError:
            #print("mouseCellStart not defined -- a selection was not initialized.")
            None
        else:
            if (mouseHoldStart != pygame.mouse.get_pos()) and brushType == "select":
                ### Drag Selected
                for note in noteMap.items():
                    if inBounds(mouseHoldStart, pygame.mouse.get_pos(), note[1].SScoords) and note[1].color == colorName:
                        note[1].selected = True
                        selectConnected(note[0][0], note[0][1])
        if (time.time() - mouseDownTime) < 0.2 and brushType == "select":
            timeOffset = 0
            keyOffset = 0
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # if shift is not held, unselect all elements.
                for note in noteMap.items():
                    note[1].selected = False
            
            # selected from mouse selection, opposite of dragging, only happens once mouse is lifted.
            noteExists = selectConnected(touchedKey, touchedTime)
            if noteExists:
                playNotes([touchedKey], duration=0.25, waves=waveMap[colorName])
            mouseTask = True
        mouseWOTask = True

    if worldMessage != "": # Renders the world message if it isn't an empty string
        worldMessageRender = stamp(worldMessage, SUBSCRIPT1, width/2, 8, 0.5, "center")

    dRow *= 0.9
    dCol *= 0.9

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            print("Pygame was quit")
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(event.w, minWidth), max(event.h, minHeight)), pygame.RESIZABLE)
            width, height = (max(event.w, minWidth), max(event.h, minHeight))
            transparentScreen = pygame.Surface((width, height), pygame.SRCALPHA)
            thisNote = pygame.Surface((width, height), pygame.SRCALPHA)
            otherNotes = pygame.Surface((width, height), pygame.SRCALPHA)

            scrOrange = pygame.Surface((width, height), pygame.SRCALPHA)
            scrPurple = pygame.Surface((width, height), pygame.SRCALPHA)
            scrCyan = pygame.Surface((width, height), pygame.SRCALPHA)
            scrLime = pygame.Surface((width, height), pygame.SRCALPHA)
            scrBlue = pygame.Surface((width, height), pygame.SRCALPHA)
            scrPink = pygame.Surface((width, height), pygame.SRCALPHA)

            scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]

            viewScaleX = (width - leftColumn) / ((1100 - leftColumn) // 32) # keeps the box consistent width even when the window is resized
            viewScaleY = (height - toolbarHeight) / ((592 - toolbarHeight) / 16) # keeps the box consistent height even when the window is resized
            innerHeight = height - toolbarHeight

        elif event.type == pygame.KEYDOWN:
            ### Typing in textbox
            if any(textBox.selected for textBox in globalTextBoxes):
                selectedTextBoxes = [filter(lambda x : x.selected == True, globalTextBoxes)][0]
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
                    for note in duplicatedNoteMap.items():
                        newNote = copy.deepcopy(note[1])
                        newNote.color = colorButton.color
                        delQ.append((note[0]))
                        addQ.append(((note[0][0], note[0][1], colorButton.color), newNote))
                    for d in delQ:
                        del duplicatedNoteMap[d]
                    for a in addQ:
                        duplicatedNoteMap[a[0]] = a[1]

            elif event.key == pygame.K_UP: # Scroll up
                dRow += 0.16
            elif event.key == pygame.K_DOWN: # Scroll down
                dRow -= 0.16
            elif event.key == pygame.K_RIGHT: # Scrub right
                dCol += 0.16
            elif event.key == pygame.K_LEFT: # Scrub left
                dCol -= 0.16
            elif event.key == pygame.K_LCTRL: # Switch to eraser momentarily
                brushType = "eraser"
            elif event.key == pygame.K_LSHIFT: # Switch to select permanently
                brushType = "select"
            elif event.key == pygame.K_SPACE: # Play / pause
                playing = not playing
                if playing:
                    playHead.play()
                    lastPlayTime = time.time()
                else:
                    play_obj.stop()
                playHead.tick = playHead.home
            elif event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE: # Delete selected note
                delQ = []
                for index, note in noteMap.items():
                    if note.selected:
                        delQ.append(index)
                for q in delQ:
                    del noteMap[q]
            elif event.key == pygame.K_s:
                if pygame.key.get_pressed()[pygame.K_LCTRL]: # if the user presses Ctrl+S (to save)
                    if workingFile == "": # file dialog to show up if the user's workspace is not attached to a file
                        filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
                        if filename != None:
                            filestring = filename.name
                            myPath = open("inner/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, directory=filestring)
                            myPath = open("inner/assets/workingfile.symphony", "rb")

                            pathBytes = bytearray(myPath.read())
                            filename.write(pathBytes)
                            filename.close()
                            workingFile = filestring
                        else:
                            myPath = open("inner/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, "inner/assets/workingfile.symphony")
                    else: # save to workspace file
                        myPath = open(workingFile, "wb")
                        dumpToFile(myPath, workingFile)
                    saveFrame = 0
            elif event.key == pygame.K_z:
                if pygame.key.get_pressed()[pygame.K_LCTRL]:
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]: # user wishes to redo (Ctrl+Shift+Z)
                        try:
                            noteMapVersionTracker.append(copy.deepcopy(noteMapFutureVersionTracker.pop()))
                        except Exception as e:
                            print("Cannot redo further")
                        if len(noteMapFutureVersionTracker) > 0:
                            noteMap = copy.deepcopy(noteMapFutureVersionTracker[-1])
                    else: # user wishes to undo (Ctrl+Z)
                        try:
                            noteMapFutureVersionTracker.append(copy.deepcopy(noteMapVersionTracker.pop()))
                        except Exception as e:
                            print("Cannot undo further")
                        if len(noteMapVersionTracker) > 0:
                            noteMap = copy.deepcopy(noteMapVersionTracker[-1])
            elif event.key == pygame.K_PERIOD:
                addQ = []
                for note in noteMap.items():
                    if note[1].selected:
                        if not ((note[1].key, note[1].time + 1, note[1].color) in noteMap) or noteMap[(note[1].key, note[1].time + 1, note[1].color)].lead:
                            el = Note(note[1].key, note[1].time + 1, False, note[1].color)
                            el.selected = True
                            addQ.append(((note[1].key, note[1].time + 1, note[1].color), el))
                for a in addQ:
                    noteMap[a[0]] = a[1]
                    selectConnected(a[0][0], a[0][1])
            elif event.key == pygame.K_COMMA:
                delQ = []
                for note in noteMap.items():
                    if note[1].selected:
                        if not ((note[1].key, note[1].time + 1, note[1].color) in noteMap) or noteMap[(note[1].key, note[1].time + 1, note[1].color)].lead:
                            delQ.append(note[0])
                for d in delQ:
                    del noteMap[d]
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LCTRL: # Switches away from eraser when Ctrl is let go
                brushType = "brush"
                for note in noteMap.items():
                    note[1].selected = False
            if event.key == pygame.K_LALT: # Duplicates selection
                for note in duplicatedNoteMap.items():
                    noteMap[note[0]] = copy.deepcopy(note[1])
                duplicatedNoteMap.clear()
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0: # Scroll up
                dRow += 0.06
            if event.y < 0: # Scroll down
                dRow -= 0.06
            if event.x > 0: # Scrub right
                dCol += 0.06
            if event.x < 0: # Scrub left
                dCol -= 0.06
    viewRow = max(min(viewRow + dRow, noteRange + 0.01), viewScaleY - 0.01) # prevents overscroll
    viewColumn = max(min(viewColumn + dCol, (noteCount - viewScaleX)), 0.01) # prevents overscrub

    oldKeyOffset = keyOffset
    drawSelectBox = False

    screen.blit(transparentScreen, transparentScreen.get_rect()) # duplicated components to drag

    if not pygame.mouse.get_pressed()[0]:
        mouseTask = False
    clock.tick(fps)
    pygame.display.flip()  # Update the display

if workingFile == "": # file dialog to show up if the user has unsaved changes (they have not attached the workspace to a file)
    filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
    if filename != None:
        myPath = open("inner/assets/workingfile.symphony", "wb")

        dumpToFile(myPath, directory="inner/assets/workingfile.symphony")
        myPath = open("inner/assets/workingfile.symphony", "rb")

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()
else: # save all changes upon closing that have happened since the last autosave
    myPath = open(workingFile, "wb")
    dumpToFile(myPath, directory=workingFile)
    
# quit loop
pygame.quit()