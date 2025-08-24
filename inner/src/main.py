###### IMPORT ######

from pygame import display as pygamedisplay, font as pygamefont, mixer as pygamemixer, image as pygameimage, event as pygameevent, time as pygametime, draw as pygamedraw, key as pygamekey, Surface as pygameSurface, mouse, quit, RESIZABLE, NOFRAME, SRCALPHA, SYSTEM_CURSOR_HAND, sndarray, K_LALT, SYSTEM_CURSOR_ARROW, SYSTEM_CURSOR_IBEAM, K_LSHIFT, KEYDOWN, QUIT, VIDEORESIZE, K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_BACKSPACE, K_RETURN, K_UP, K_DOWN, K_RIGHT, K_LEFT, K_LCTRL, K_LMETA, K_SPACE, K_DELETE, K_PERIOD, K_COMMA, KEYUP, MOUSEWHEEL, K_s, K_z, K_y
from io import BytesIO
import numpy as np
# import random
import tkinter as tk
import copy
import cv2
from math import *
import time
lastTime = time.time()
START_TIME = lastTime

from os import environ, path
# import json
import sys
import dill as pkl
from tkinter.filedialog import asksaveasfile #, asksaveasfilename
import json
from pathlib import Path
from soundfile import write as sfwrite
import pretty_midi

consoleMessages = []

class console:
    @staticmethod
    def log(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Symphony] ' + str(message)
        print(_msg)
        consoleMessages.append(((_msg), "gray"))

    @staticmethod
    def message(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Message] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "magenta"))

    @staticmethod
    def warn(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Warning] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "yellow"))

    @staticmethod
    def error(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Error] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "red"))

if sys.platform.startswith("win"):
    console.log("Running on Windows")
    platform = 'windows'
    CMD_KEY = K_LCTRL
elif sys.platform == "darwin":
    console.log("Running on macOS")
    platform = 'mac'
    CMD_KEY = K_LMETA
elif sys.platform.startswith("linux"):
    console.log("Running on Linux")
    platform = 'linux'
    CMD_KEY = K_LCTRL
else:
    console.warn(f"Running on unknown platform: {sys.platform}")
    platform = 'unknown'
    CMD_KEY = K_LCTRL

try:
    from ctypes import windll
    myappid = 'nimbial.symphony.editor.v1-0' # arbitrary string
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    console.warn('Error importing windll or setting Unique AppID. You might be running on a non-Windows platform.')
    pass # Not on Windows or ctypes is not available

### Handling Arguments
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
    stringCopy = string
    for l in range(len(stringCopy)):
        if not stringCopy[l] in 'abcdefghijklmnopqrstuvwxyzABCEDFGHIJKLMNOPQRSTUVWXYZ1234567890-_+(). ':
            stringCopy = stringCopy[:l] + '_' + stringCopy[l+1:]
    return stringCopy

def get_arg_path(arg_index, default_relative):
    import os
    if len(sys.argv) > arg_index:
        return sys.argv[arg_index]
    return os.path.abspath(default_relative)

autoSaveDirectory = None
user_settings_path = None
directory_json_path = None
source_path = None

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
    source_path = get_arg_path(4, 'assets/directory.json')
    directory_json_path = get_arg_path(5, 'assets/directory.json')
    user_settings_path = get_arg_path(6, 'assets/user-settings.json')
    autoSaveDirectory = json.load(open(directory_json_path))['Symphony Auto-Save'][0]['Auto-Save']

###### TK CONSOLE INITIALIZE ######
class ConsoleWindow(tk.Tk):
    def __init__(self, lines, font="Consolas 10"):
        super().__init__()
        icon = tk.PhotoImage(file=f"{source_path}/assets/terminal-icon.png")
        self.iconphoto(True, icon)
        self.title("Symphony: Console")
        self.geometry("800x400")
        self.resizable(False, False)
        self.configure(bg="black")
        self.lines = lines
        self.font = font

        self.text = tk.Text(self, bg="black", font=font, wrap="word", state="disabled")
        self.scroll = tk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)

        self.text.tag_config("gray", foreground="gray")
        self.text.tag_config("yellow", foreground="yellow")
        self.text.tag_config("red", foreground="red")
        self.text.tag_config("magenta", foreground="magenta")

        self.text.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self._last_len = 0

    def update_console(self):
        if len(self.lines) != self._last_len:
            self._last_len = len(self.lines)
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            for message, tag in self.lines:
                self.text.insert("end", message + "\n", tag)
            self.text.see("end")
            self.text.configure(state="disabled")

show_console = False
if process == 'open' and user_settings_path:
    show_console = json.load(open(user_settings_path))["show_console"]
    if show_console:
        try:
            userName = json.load(open(user_settings_path))["user_name"].split(sep=' ')[0]
        except Exception:
            userName = 'User'
        console.message(f'Hey, {userName}! This console can be safely closed at any time, and your editor will remain active.')

###### (PYGAME &) WINDOW INITIALIZE ######

if process in ['instantiate', 'retrieve', 'export', 'convert']:
    environ["SDL_VIDEODRIVER"] = "dummy"

console.log("Initialized Args "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

width, height = (1100, 592)
minWidth, minHeight = (925, 592)
iconPath = f'{source_path}/assets/icon32x32.png'
if path.exists(iconPath):
    gameIcon = pygameimage.load(iconPath)
    pygamedisplay.set_icon(gameIcon)
else:
    console.warn(f"Warning: Icon file not found at {iconPath}")

console.log("Initialized Icon Path "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

#pygame.init()
pygamedisplay.init()
pygamefont.init()
pygamemixer.init()

console.log("Initialized Pygame "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

pygamedisplay.set_caption(f"{titleText} - Symphony v1.0 Beta")
#pygamedisplay.set_icon(pygame.image.load(f"{source_path}/icon.png"))
screen = pygamedisplay.set_mode((width, height), RESIZABLE, NOFRAME)

if (process == 'instantiate') or (process == 'retrieve'):
    None
else:
    pygamedisplay.flip()
    pygameevent.pump()
    time.sleep(0.1)

console.log("Initialized Window "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected
SAMPLE_RATE = 44100
pygamemixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)  # initialize pygame mixer at module import
transparentScreen = pygameSurface((width, height), SRCALPHA)
otherNotes = pygameSurface((width, height), SRCALPHA)
thisNote = pygameSurface((width, height), SRCALPHA)
scrOrange = pygameSurface((width, height), SRCALPHA)
scrPurple = pygameSurface((width, height), SRCALPHA)
scrCyan = pygameSurface((width, height), SRCALPHA)
scrLime = pygameSurface((width, height), SRCALPHA)
scrBlue = pygameSurface((width, height), SRCALPHA)
scrPink = pygameSurface((width, height), SRCALPHA)
scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]
clock = pygametime.Clock()
fps = 60

# imports font styles
if process == 'open':
    mainFont = f'{source_path}/assets/InterVariable.ttf'
    TITLE1 = pygamefont.Font(mainFont, 60)
    HEADING1 = pygamefont.Font(mainFont, 24)
    SUBHEADING1 = pygamefont.Font(mainFont, 14)
    BODY = pygamefont.Font(mainFont, 14)
    SUBSCRIPT1 = pygamefont.Font(mainFont, 11)

    bytes_io = BytesIO()

    ###### ASSETS ######

    playImage = pygameimage.load(f"{source_path}/assets/play.png")
    pauseImage = pygameimage.load(f"{source_path}/assets/pause.png")
    headImage = pygameimage.load(f"{source_path}/assets/head.png")
    brushImage = pygameimage.load(f"{source_path}/assets/brush.png")
    eraserImage = pygameimage.load(f"{source_path}/assets/eraser.png")
    negaterImage = pygameimage.load(f"{source_path}/assets/negater.png")
    rainbowImage = pygameimage.load(f"{source_path}/assets/rainbow.png")

    squareWaveImage = pygameimage.load(f"{source_path}/assets/square.png")
    sawtoothWaveImage = pygameimage.load(f"{source_path}/assets/sawtooth.png")
    triangleWaveImage = pygameimage.load(f"{source_path}/assets/triangle.png")
    waveImages = [squareWaveImage, triangleWaveImage, sawtoothWaveImage]

    upChevronImage = pygameimage.load(f"{source_path}/assets/up.png")
    downChevronImage = pygameimage.load(f"{source_path}/assets/down.png")
else:
    TITLE1 = ''
    HEADING1 = ''
    SUBHEADING1 = ''
    BODY = ''
    SUBSCRIPT1 = ''

console.log("Initialized Assets "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

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
#console.log(innerHeight)
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

console.log("Initialized Variables "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### CLASSES ######

class TextBox():
    '''Class to contain text boxes, which are used for interactivity.'''

    def __init__(self, pos, width, height, text, textSize = SUBHEADING1, endBarOffset=0):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.selected = False
        self.text = text
        self.endBarOffset = endBarOffset
        globalTextBoxes.append(self)

    def mouseClicked(self):
        '''Method to return whether the textbox has been clicked'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and mouse.get_pressed()[0] and not mouseTask
    
    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0]

    def draw(self, text):
        '''Method to draw a textbox.'''
        pygamedraw.rect(screen, mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        if self.selected:
            showBar = round(time.time())%2 == 0 #  + showBar*2.5 for xOffset
            stamp((text[:(-self.endBarOffset)] if self.endBarOffset != 0 else text) + ("|" if showBar else " ") + (text[-self.endBarOffset+1:] if self.endBarOffset != 0 else ''), self.textSize, self.x + self.width/2, self.y - showBar*1, 0.4, "center")
        else:
            stamp(text, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
        pygamedraw.rect(screen, (self.selected * 80, self.selected * 80, self.selected * 80), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)

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
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and mouse.get_pressed()[0] and not mouseTask
    
    def draw(self, itemToDraw = None, overrideDark = False):
        '''Method to draw a button.'''
        if self.mouseBounds():
            mouse.set_cursor(SYSTEM_CURSOR_HAND)

        if self.colorCycle != None:
            pygamedraw.rect(screen, self.color, (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
            stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")
        else:
            pygamedraw.rect(screen, (25, 25, 25) if overrideDark else mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        pygamedraw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
    
        if self.colorCycle == None:
            if type(itemToDraw) == str:
                stamp(itemToDraw, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
            else:
                screen.blit(itemToDraw, (self.x + self.width/2 - 8, self.y - 8))
        else:
            if type(itemToDraw) == pygameSurface:
                screen.blit(itemToDraw, (self.x + self.width/2 - 14, self.y - 14))
                pygamedraw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
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

            pygamedraw.line(screen, (0, 255, 255), top, bottom, 1)

        if self.home != 0:
            top = [(self.home * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [(self.home * tileW) - (viewColumn * tileW) + leftColW, height]

            pygamedraw.line(screen, (255, 255, 0), top, bottom, 1)

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
            pygamedraw.rect(screen, leadColor,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), border_radius=3)
            pygamedraw.rect(screen, black,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), 1, 3)
            if self.selected:
                pygamedraw.line(screen, outlineColor, # top edge
                         (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                pygamedraw.line(screen, outlineColor, # left edge
                         (headerX - 1, headerY - 1), (headerX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                pygamedraw.line(screen, outlineColor, # bottom edge
                         (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                if not (self.key, self.time + 1, self.color) in noteMap:
                    pygamedraw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
        else:
            pygamedraw.rect(screen, tailColor,
                         (headerX - 1, headerY, (width - leftColumn)/viewScaleX + 1, innerHeight/viewScaleY))
            pygamedraw.line(screen, black, # top edge
                        (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 1)
            pygamedraw.line(screen, black, # bottom edge
                        (headerX - 1, headerY + floor(innerHeight/viewScaleY)), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + floor(innerHeight/viewScaleY)), 1)
            if (self.key, self.time + 1, self.color) in noteMap and noteMap[(self.key, self.time + 1, self.color)].lead == False:
                if self.selected:
                    pygamedraw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 2)
                    pygamedraw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                if nextKeyNumToOffset < numToOffset:
                    pygamedraw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
            else:
                if self.selected:
                    pygamedraw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                    pygamedraw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
                    pygamedraw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                else:
                    pygamedraw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
        
        if self.extending:
            pygamedraw.line(screen, (0, 255, 0), # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)

console.log("Initialized Classes "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

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


if workingFile == "" or process == 'instantiate': # if the workingfile is not provided or we are creating a new file, initialize a new program state
    ps = ProgramState(10, noteMap, "Eb", "Lydian", waveMap)
    console.log('Creating new programState...')
else:
    ps = toProgramState(pkl.load(open(workingFile, "rb")))
    console.log('Loading existing programState...')

if process == 'retrieve' and len(sys.argv) >= 5:
    filepath = sys.argv[2]
    id_val = sys.argv[3]
    src_folder = sys.argv[4]
    user_data_path = sys.argv[5] if len(sys.argv) >= 6 else None


    response_path = path.join(user_data_path if user_data_path else src_folder, 'response.json')
    with open(response_path, 'w') as f:
        console.log('DUMPING INTO RESPONSE.JSON')
        console.log(path.join(user_data_path, 'response.json'))
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
tempoTextBox = TextBox(pos=(320, 40), width=105, height=28, text='360', endBarOffset=4)
tempoUpButton = Button(pos=(425, 40), width=20, height=28)

###### FUNCTIONS ######

def dumpToFile(file, directory):
    '''Saves data to the working file, used in many places in the code'''
    global worldMessage

    # when saving, repair any discrepancies between hashmap key and obj data (rare but fatal)
    delQ, addQ = [], []
    for thing in noteMap.items():
        if (thing[1].key, thing[1].time, thing[1].color) != thing[0]:
            console.log("A discrepancy was found between hashmap and obj data. Repairing (prioritizing obj data) now...")
            console.log(f"Discrepancy details -- HM Key: {thing[0]}, Obj Data: {(thing[1].key, thing[1].time, thing[1].color)}")
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
    if autoSave and process == 'open':
      pkl.dump(ps, open(autoSaveDirectory + '/' + titleText + ' Backup ' + sessionID + '.symphony', 'wb'), -1)

    worldMessage = (f"Last Saved {readableTime} to " + directory) if directory != f"{source_path}/assets/workingfile.symphony" else "You have unsaved changes - Please save to a file on your PC."

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
    freq, fmt, nchan = pygamemixer.get_init()
    if nchan == 1:
        arr2d = array_1d.reshape(-1, 1)
    else:
        # duplicate mono into both LR for stereo
        arr2d = np.column_stack([array_1d] * nchan)
    return sndarray.make_sound(arr2d) if returnType == 'Sound' else arr2d

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
        console.error(f"NoteError: {e}")

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

def createMidiFromNotes(noteData, outputFolderPath, instrumentName="Acoustic Grand Piano"):
    global tpm
    baseName = path.splitext(path.basename(workingFile))[0]
    ext = ".mid"
    candidate = path.join(outputFolderPath, baseName + ext)
    # Resolve name conflicts
    counter = 1
    while path.exists(candidate):
        candidate = path.join(outputFolderPath, f"{baseName} ({counter}){ext}")
        counter += 1
    
    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instrumentName))

    for note in noteData:
        pitch = note["pitch"]
        start = note["startTime"]
        end = start + note["duration"]
        velocity = note.get("velocity", 127)

        midiNote = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
        instrument.notes.append(midiNote)

    midi.instruments.append(instrument)
    midi.write(candidate)

def convertNoteMapToStrikeList():
    strikeList = []
    for el, note in noteMap.items():
        if note.lead:
            offset = 1
            while (note.key, note.time + offset, note.color) in noteMap:
                offset += 1
            strikeList.append({"pitch": note.key + 35, "startTime": ((note.time - 1) / 4), "duration": (offset / 4)})
    
    return strikeList
        
if process == 'convert':
    createMidiFromNotes(convertNoteMapToStrikeList(), destination)
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
    isInside = rect[0] < mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < mouse.get_pos()[1] < rect[1] + rect[3]
    return isInside, ((20, 20, 20) if isInside and mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

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
    
console.log("Initialized Functions "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
console.log("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')

###### MAINLOOP ######
running = True
playHead = Head(0, 1, 0)
tempo = int(round(3600 / ps.ticksPerTile))
lastNoteTime = 0
ctrlZTime = 59
noteMapVersionTracker = []
noteMapFutureVersionTracker = []

root = None
last_update = time.time()

# Setup Tkinter console window (only if setting allows it)
if process == 'open' and len(sys.argv) == 7:
    if json.load(open(user_settings_path))["show_console"]:
        try:
            root = ConsoleWindow(consoleMessages)
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

    saveFrame += 60 * (1 / fps)
    if saveFrame > 1200: # Saves every 20 seconds
        saveFrame = 0
        myPath = open(workingFile if workingFile != "" else f"{source_path}/assets/workingfile.symphony", "wb")
        dumpToFile(myPath, workingFile if workingFile != "" else f"{source_path}/assets/workingfile.symphony")
        myPath.close()
    # checks if new changes have been made, if so adds them to the version history for Ctrl+Z
    ctrlZTime += 1
    if ctrlZTime > 60:
        for note in noteMap.items():
            lastNoteTime = max(lastNoteTime, note[1].time)
            noteCount = max(noteCount, lastNoteTime + 20)

        if not mouse.get_pressed()[0]:
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
            cm = (floor((column+viewColumn)%timeInterval) == 1) * 8
            pygamedraw.rect(screen, ((28 + cm, 28 + cm, 28 + cm) if not (-(floor(row - viewRow) + keyIndex + 1) % 12) in modeIntervals else (43 + cm, 43 + cm, 43 + cm)),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), border_radius=3)
            pygamedraw.rect(screen, (0, 0, 0),
                         (headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY), 1, 3)
            headerX += (width - leftColumn)/viewScaleX

            ##### BRUSH CONTROLS #####
            if mouseFunction((headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY))[0] and (mouse.get_pressed()[0]) and (toolbarHeight < mouse.get_pos()[1] < (height - 50)):
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
                        mouseHoldStart = mouse.get_pos()
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
                                if pygamekey.get_pressed()[K_LALT]:
                                    numSelected = False
                                    duplicatedNoteMap = {}
                                    for note in noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                            duplicatedNoteMap[note[0]] = copy.deepcopy(note[1]) # adds the selected notemap to the duplicated notemap until alt is let go
                                            duplicatedNoteMap[note[0]].color = colorName
                                    if mouseTask and numSelected:# and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((mouse.get_pos()[d] - mouseHoldStart[d]) / 
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
                                    if mouseTask and numSelected and dist(mouse.get_pos(), mouseHoldStart) > 10:
                                        ### Dragging
                                        (timeOffset, keyOffset) = (int((mouse.get_pos()[d] - mouseHoldStart[d]) / 
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
        pygamedraw.rect(screen, (255, 255, 255), (min(mouseHoldStart[0], mouse.get_pos()[0]),
                                                                       min(mouseHoldStart[1], mouse.get_pos()[1]),
                                                                       abs(mouse.get_pos()[0] - mouseHoldStart[0]),
                                                                       abs(mouse.get_pos()[1] - mouseHoldStart[1])), 1)

    # functionality to move playhead and draw it when it is moving
    if playing:
        playHead.tick += 1 * 60/fps
        playHead.draw(screen, viewRow, viewColumn, leftColumn, (width - leftColumn)/viewScaleX, drawHead=True)
    else:
        playHead.draw(screen, viewRow, viewColumn, leftColumn, (width - leftColumn)/viewScaleX)

    for row in range(ceil(viewScaleY) + 1):
        headerX, headerY = 0, row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/viewScaleY) - innerHeight/viewScaleY
        note = f"{(NOTES_SHARP if accidentals == 'sharps' else NOTES_FLAT)[floor((viewRow - row) % 12)]} {floor((viewRow - row) / 12) + 2}"
        pygamedraw.rect(screen, ((26, 26, 26) if not (-(floor(row - viewRow) + keyIndex + 1) % 12) in modeIntervals else (34, 34, 34)),
                         (headerX, headerY, leftColumn, innerHeight/viewScaleY), border_radius=3)
        pygamedraw.rect(screen, (0, 0, 0),
                         (headerX, headerY, leftColumn, innerHeight/viewScaleY), 1, 3)
        stamp(note, SUBHEADING1, headerX + 5, headerY + 5, 0.4)

        if mouseFunction((0, headerY, leftColumn, innerHeight/viewScaleY))[0] and (mouse.get_pressed()[0]) and (toolbarHeight < mouse.get_pos()[1] < (height - 50)) and not mouseTask:
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
        mouseDel = mouse.get_rel()[0]/(width - leftColumn) * noteCount

        if mouse.get_pos()[1] > height - 80:
            if ((width - leftColumn) * progressLeft) + leftColumn < mouse.get_pos()[0] < ((width - leftColumn) * progressRight) + leftColumn and mouse.get_pos()[1] > height - scrollBarHeight - 15:
                # mouse is touching scroll bar
                if mouse.get_pressed()[0]:
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

        pygamedraw.rect(screen, scrollBarColor, (((width - leftColumn) * progressLeft) + leftColumn,
                                                  height - scrollBarHeight - 3,
                                                  (width - leftColumn) * (progressRight - progressLeft),
                                                  scrollBarHeight), 1, 3)

    def renderToolBar():
        '''Renders the top toolbar, and all of the elements inside of it.'''
        global accidentals, mouseTask, playing, head, brushType, key, keyIndex, mode, modeIntervals, lastPlayTime, timeInterval, ticksPerTile, tempo
        pygamedraw.rect(screen, (43, 43, 43), (0, 0, width, toolbarHeight))
        pygamedraw.line(screen, (0, 0, 0), (0, toolbarHeight), (width, toolbarHeight))
        pygamedraw.line(screen, (30, 30, 30), (0, toolbarHeight - 1), (width, toolbarHeight - 1))
        pygamedraw.line(screen, (49, 49, 49), (0, toolbarHeight - 2), (width, toolbarHeight - 2))
        pygamedraw.line(screen, (45, 45, 45), (0, toolbarHeight - 3), (width, toolbarHeight - 3))

        ### TRACK TITLE BAR
        if (width >= 1100):
            pygamedraw.rect(screen, (0, 0, 0), (475, toolbarHeight/2 - 14, width - 950, 28), 1, 3)
            if len(titleText) < (width - 950) / 10:
                stamp(titleText, SUBHEADING1, width/2, 40, 0.4, "center")
            else:
                stamp(titleText[:int((width - 950) / 10)] + '...', SUBHEADING1, width/2, 40, 0.4, "center")
        mouse.set_cursor(SYSTEM_CURSOR_ARROW)

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
        if head:
            mouse.set_cursor(SYSTEM_CURSOR_IBEAM)
            playheadButton.draw(headImage, overrideDark=True)
        else:
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
            mouse.set_cursor(SYSTEM_CURSOR_IBEAM)
        if timeSigTextBox.mouseClicked():
            if not pygamekey.get_pressed()[K_LSHIFT]:
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
            mouse.set_cursor(SYSTEM_CURSOR_IBEAM)
        if tempoTextBox.mouseClicked():
            if not pygamekey.get_pressed()[K_LSHIFT]:
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

    if not mouse.get_pressed()[0] and not mouseWOTask:
        reevaluateLeads()
        ### Unclicked
        mouse.set_cursor(SYSTEM_CURSOR_ARROW)
        if head:
            head = False
        try:
            mouseCellStart
        except NameError:
            #console.log("mouseCellStart not defined -- a selection was not initialized.")
            None
        else:
            if (mouseHoldStart != mouse.get_pos()) and brushType == "select":
                ### Drag Selected
                for note in noteMap.items():
                    if inBounds(mouseHoldStart, mouse.get_pos(), note[1].SScoords) and note[1].color == colorName:
                        note[1].selected = True
                        selectConnected(note[0][0], note[0][1])
        if (time.time() - mouseDownTime) < 0.2 and brushType == "select":
            timeOffset = 0
            keyOffset = 0
            if not pygamekey.get_pressed()[K_LSHIFT]: # if shift is not held, unselect all elements.
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

    for event in pygameevent.get():
        if event.type == QUIT:
            running = False
            console.warn("Pygame was quit")
        elif event.type == VIDEORESIZE:
            screen = pygamedisplay.set_mode((max(event.w, minWidth), max(event.h, minHeight)), RESIZABLE)
            width, height = (max(event.w, minWidth), max(event.h, minHeight))
            transparentScreen = pygameSurface((width, height), SRCALPHA)
            thisNote = pygameSurface((width, height), SRCALPHA)
            otherNotes = pygameSurface((width, height), SRCALPHA)

            scrOrange = pygameSurface((width, height), SRCALPHA)
            scrPurple = pygameSurface((width, height), SRCALPHA)
            scrCyan = pygameSurface((width, height), SRCALPHA)
            scrLime = pygameSurface((width, height), SRCALPHA)
            scrBlue = pygameSurface((width, height), SRCALPHA)
            scrPink = pygameSurface((width, height), SRCALPHA)

            scrList = [scrOrange, scrPurple, scrCyan, scrLime, scrBlue, scrPink]

            viewScaleX = (width - leftColumn) / ((1100 - leftColumn) // 32) # keeps the box consistent width even when the window is resized
            viewScaleY = (height - toolbarHeight) / ((592 - toolbarHeight) / 16) # keeps the box consistent height even when the window is resized
            innerHeight = height - toolbarHeight

        elif event.type == KEYDOWN:
            ### Typing in textbox
            if any(textBox.selected for textBox in globalTextBoxes):
                selectedTextBoxes = [filter(lambda x : x.selected == True, globalTextBoxes)][0]
                pressedKeys = [pygamekey.get_pressed()[possKey] for possKey in [K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_BACKSPACE, K_RETURN]]
                if pressedKeys[10]:
                    for textBox in selectedTextBoxes:
                        textBox.text = textBox.text[:-1]
                if pressedKeys[11]:
                    unselectTextBoxes()
                else:
                    for textBox in selectedTextBoxes:
                        if True in pressedKeys:
                            textBox.text = textBox.text + str(pressedKeys.index(True))
            elif any(pygamekey.get_pressed()[possKey] for possKey in [K_1, K_2, K_3, K_4, K_5, K_6, K_7]):
                colorButton.setColor([pygamekey.get_pressed()[possKey] for possKey in [K_1, K_2, K_3, K_4, K_5, K_6, K_7]].index(True))
                if pygamekey.get_pressed()[K_LALT]:
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

            elif event.key == K_UP: # Scroll up
                dRow += 0.16
            elif event.key == K_DOWN: # Scroll down
                dRow -= 0.16
            elif event.key == K_RIGHT: # Scrub right
                dCol += 0.16
            elif event.key == K_LEFT: # Scrub left
                dCol -= 0.16
            elif event.key == CMD_KEY: # Switch to eraser momentarily
                brushType = "eraser"
            elif event.key == K_LSHIFT: # Switch to select permanently
                brushType = "select"
            elif event.key == K_SPACE: # Play / pause
                playing = not playing
                if playing:
                    playHead.play()
                    lastPlayTime = time.time()
                else:
                    play_obj.stop()
                playHead.tick = playHead.home
            elif event.key == K_BACKSPACE or event.key == K_DELETE: # Delete selected note
                delQ = []
                for index, note in noteMap.items():
                    if note.selected:
                        delQ.append(index)
                for q in delQ:
                    del noteMap[q]
            elif event.key == K_s:
                if pygamekey.get_pressed()[CMD_KEY]: # if the user presses Ctrl+S (to save)
                    if workingFile == "": # file dialog to show up if the user's workspace is not attached to a file
                        filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
                        if filename != None:
                            filestring = filename.name
                            myPath = open(f"{source_path}/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, directory=filestring)
                            myPath = open(f"{source_path}/assets/workingfile.symphony", "rb")

                            pathBytes = bytearray(myPath.read())
                            filename.write(pathBytes)
                            filename.close()
                            workingFile = filestring
                        else:
                            myPath = open(f"{source_path}/assets/workingfile.symphony", "wb")
                            dumpToFile(myPath, f"{source_path}/assets/workingfile.symphony")
                    else: # save to workspace file
                        myPath = open(workingFile, "wb")
                        dumpToFile(myPath, workingFile)
                    saveFrame = 0
            elif event.key == K_z or event.key == K_y:
                if pygamekey.get_pressed()[CMD_KEY]:
                    if (pygamekey.get_pressed()[K_LSHIFT] and event.key == K_z) or event.key == K_y: # user wishes to redo (Ctrl+Shift+Z or Ctrl+Y)
                        try:
                            noteMapVersionTracker.append(copy.deepcopy(noteMapFutureVersionTracker.pop()))
                        except Exception as e:
                            console.warn("Cannot redo further")
                        if len(noteMapFutureVersionTracker) > 0:
                            noteMap = copy.deepcopy(noteMapFutureVersionTracker[-1])
                    elif event.key == K_z: # user wishes to undo (Ctrl+Z)
                        try:
                            noteMapFutureVersionTracker.append(copy.deepcopy(noteMapVersionTracker.pop()))
                        except Exception as e:
                            console.warn("Cannot undo further")
                        if len(noteMapVersionTracker) > 0:
                            noteMap = copy.deepcopy(noteMapVersionTracker[-1])
            elif event.key == K_PERIOD:
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
            elif event.key == K_COMMA:
                delQ = []
                for note in noteMap.items():
                    if note[1].selected:
                        if not ((note[1].key, note[1].time + 1, note[1].color) in noteMap) or noteMap[(note[1].key, note[1].time + 1, note[1].color)].lead:
                            delQ.append(note[0])
                for d in delQ:
                    del noteMap[d]
        elif event.type == KEYUP:
            if event.key == CMD_KEY: # Switches away from eraser when Ctrl is let go
                brushType = "brush"
                for note in noteMap.items():
                    note[1].selected = False
            if event.key == K_LALT: # Duplicates selection
                for note in duplicatedNoteMap.items():
                    noteMap[note[0]] = copy.deepcopy(note[1])
                duplicatedNoteMap.clear()
        elif event.type == MOUSEWHEEL:
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

    if not mouse.get_pressed()[0]:
        mouseTask = False
    clock.tick(fps)
    pygamedisplay.flip()  # Update the display

if workingFile == "": # file dialog to show up if the user has unsaved changes (they have not attached the workspace to a file)
    filename = asksaveasfile(initialfile = 'Untitled.symphony', mode='wb',defaultextension=".symphony", filetypes=[("Symphony Musical Composition","*.symphony")])
    if filename != None:
        myPath = open(f"{source_path}/assets/workingfile.symphony", "wb")

        dumpToFile(myPath, directory=f"{source_path}/assets/workingfile.symphony")
        myPath = open(f"{source_path}/assets/workingfile.symphony", "rb")

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()
else: # save all changes upon closing that have happened since the last autosave
    myPath = open(workingFile, "wb")
    dumpToFile(myPath, directory=workingFile)
    
# quit loop
quit()
sys.exit()