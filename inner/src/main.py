# main.py
# entry point for the program. contains the mainloop.
###### CONSOLE ######

#import console_controls.console_window as cw
from console_controls.console import *

###### IMPORT ######

console.message('Welcome to Symphony v1.1.5.')

import time
lastTime = time.time()
START_TIME = lastTime

from collections import defaultdict
import copy
import dill as pkl
import json
from os import path
import pygame
from pygame._sdl2.video import Window as SDLWindow
import sys
import traceback
import webbrowser

console.log("Imported External Libraries "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### INTERNAL MODULES ######

import events
import gui.element as gui
import gui.frame as frame
import gui.custom as custom
import gui.dom as dom
import process_command.read_write as pcrw
import utils.state_loading as sl
import utils.file_io as fio
import utils.platform_controller as plat
import utils.sdl_resize_watch as sdl
import sound.sound_processing as sp
import sound.instruments as ins
import utils.project_state as pst
import utils.util as utils

console.log("Imported Internal Modules & Connected External Libraries "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PLATFORM DETECTION ######

platform, CMD_KEY = plat.getPlatformNameAndMeta()

####### SYSARG HANDLING ######

SAMPLE_RATE = 44100

console.log(f"sysargs: {sys.argv}")
source_path = sys.argv[1]

sessionID = time.strftime('%Y-%m-%d %H%M%S')

console.log("Platform Detection and Sysarg Handling "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### IMAGES ######

playImage = pygame.image.load(f"{source_path}/assets/play.png")
pauseImage = pygame.image.load(f"{source_path}/assets/pause.png")
headImage = pygame.image.load(f"{source_path}/assets/head.png")
headAltImage = pygame.image.load(f"{source_path}/assets/head-alt.png")
brushImage = pygame.image.load(f"{source_path}/assets/brush.png")
eraserImage = pygame.image.load(f"{source_path}/assets/eraser.png")
selectImage = pygame.image.load(f"{source_path}/assets/select.png")
sharpsImage = pygame.image.load(f"{source_path}/assets/sharps.png")
flatsImage = pygame.image.load(f"{source_path}/assets/flats.png")
questionImage = pygame.image.load(f"{source_path}/assets/question.png")

squareWaveImage = pygame.image.load(f"{source_path}/assets/square.png")
sawtoothWaveImage = pygame.image.load(f"{source_path}/assets/sawtooth.png")
triangleWaveImage = pygame.image.load(f"{source_path}/assets/triangle.png")
# guitarInstrumentImage = pygame.image.load(f"{source_path}/assets/guitar.png")
pianoInstrumentImage = pygame.image.load(f"{source_path}/assets/piano.png")
# bellsImage = pygame.image.load(f"{source_path}/assets/bells.png")
maleVoiceWaveImage = pygame.image.load(f"{source_path}/assets/male-voice.png")
# brassWaveImage = pygame.image.load(f"{source_path}/assets/brass.png")
instrumentImages = [
    squareWaveImage,
    triangleWaveImage,
    sawtoothWaveImage,
    pianoInstrumentImage,
    # bellsImage,
    maleVoiceWaveImage
]

upChevronImage = pygame.image.load(f"{source_path}/assets/up.png")
downChevronImage = pygame.image.load(f"{source_path}/assets/down.png")
upDownChevronImage = pygame.image.load(f"{source_path}/assets/up-down.png")

console.log("Loaded Assets "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PYGAME & WINDOW INITIALIZE ######

width, height = (1100, 592)
minWidth, minHeight = (1000, 592)
MAC_ICON_ZOOM_OUT_PERCENT = 20


def createMacDockIcon(iconSurface):
    iconWidth, iconHeight = iconSurface.get_size()
    scaledWidth = max(1, round(iconWidth * (100 - MAC_ICON_ZOOM_OUT_PERCENT) / 100))
    scaledHeight = max(1, round(iconHeight * (100 - MAC_ICON_ZOOM_OUT_PERCENT) / 100))
    paddingLeft = (iconWidth - scaledWidth) // 2
    paddingTop = (iconHeight - scaledHeight) // 2

    scaledIcon = pygame.transform.smoothscale(iconSurface, (scaledWidth, scaledHeight))
    dockIcon = pygame.Surface((iconWidth, iconHeight), pygame.SRCALPHA)
    dockIcon.blit(scaledIcon, (paddingLeft, paddingTop))
    return dockIcon

iconPath = f'{source_path}/assets/icon32x32.png'
if path.exists(iconPath):
    gameIcon = pygame.image.load(iconPath)
    if platform == 'mac':
        gameIcon = createMacDockIcon(gameIcon)
else:
    console.warn(f"Warning: Icon file not found at {iconPath}")

pygame.font.init()
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)

clock = pygame.time.Clock()

console.log("Initialized Pygame Data "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### VARIABLE & GUI ELEMENT SETUP ######

# initialize constants to make style setting easier (adds intellisense and allows for no quotes)
background = "background"
'''```type: list[int, int, int, int] # The RGBA background color of the Panel. \ndefault: gui.COLOR_TRANSPARENT'''
border = "border"
'''```type: int | list[int, int, int, int] # The thickness of the border around the Panel. \ndefault: 0'''
borderColor = "border-color"
'''```type: list[int, int, int, int] # The color of the border around the Panel. \ndefault: gui.COLOR_BORDER'''
rounding = "rounding"
'''```type: "sm" | "lg" | int | list[int, int, int, int] # The size of rounding on the corners of the Panel. \ndefault: 0'''
display = "display"
'''```type: "flex" | "absolute" | "fixed" # Whether to make the object anchor relative to the DOM, to its parent, or to the screen. \ndefault: "flex"'''
offset = "offset"
'''```type: list[int, int] # The offset of the object relative to its anchor. \ndefault: [0, 0]'''
orient = "orient"
'''```type: "row" | "col" # The direction to make the children of the panel flow. \ndefault: "row"'''
align = "align"
'''```type: "center" | "top" | "bottom" | "spread" # The layout of the children vertically. \ndefault: "top"'''
justify = "justify"
'''```type: "center" | "left" | "right" | "spread" # The layout of the children horizontally. \ndefault: "left"'''
sizing = "sizing"
'''```type: list["fit" | "fill" | int, "fit" | "fill" | int] # Decides how to occupy the provided space. \ndefault: "fit"'''
padding = "padding"
'''```type: int | list[int, int, int, int] # The additional space internal to the Panel. \ndefault: 0'''
gap = "gap"
'''```type: int # The space between children of the Panel. \ndefault: 0'''

fps = 60

WorldMessage = utils.LightWatchable('')
questions_url = "https://docs.nimbial.com/symphony/4"

Key = utils.LightWatchable('Eb')
Mode = utils.LightWatchable('Lydian')
Tempo = utils.LightWatchable(360)

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected

page = "Editor"
noteMap : dict[str, list[custom.Note]] = {}
projectMeta = copy.deepcopy(sl.DEFAULT_META_FIELD)

saveFrame = 0

suspendTransactionCapture = False

NOTES_SHARP =     ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =      ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
NOTES_FLAT_NEW =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
keyIndex = 0

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
modesMap = {}
for modeInt in modesIntervals:
    modesMap[modeInt[0]] = modeInt[1]

colors = {
    "orange" : (168, 136, 49),
    "purple" : (134, 48,  156),
    "cyan"   : (20,  128, 150),
    "lime"   : (102, 150, 20),
    "blue"   : (61,  80,  156),
    "pink"   : (168, 49,  94),
    "all"    : (255, 255, 255)
}
colorsInd = {
    "orange" : 0,
    "purple" : 1,
    "cyan"   : 2,
    "lime"   : 3,
    "blue"   : 4,
    "pink"   : 5,
    "all"    : 6
}
colorsList = list[tuple[str, tuple[int, int, int]]](colors.items())
justColors = [n[1] for n in colorsList]
justColorNames = [n[0] for n in colorsList]

instrumentTypes = ['square', 'triangle', 'sawtooth', 'piano', 'bells', 'voice']
waveMap = {}
for index, color in enumerate(colorsList):
    waveMap[color[0]] = 0

accidentals = "flats"
head = False
playing = False
brushType = "brush"

BeatLength = utils.LightWatchable(4)
BeatsPerMeasure = utils.LightWatchable(4)

mainFont = f'{source_path}/assets/InterVariable.ttf'
gui.init(source_path)
ins.init(source_path)

zoomDimensions = [
    (18,  24),
    (22,  26),
    (26,  28),
    (30,  30),
    (40,  40),
    (60,  48),
    (80,  54),
    (100, 56)
]

###### ASSETS ######

# LARGE_SPACE = 24
# SMALL_SPACE = 6
# PADDING = 26

PlayPauseButton = gui.Button(width=28, height=28, states=[playImage, pauseImage], name='PlayPauseButton')
AccidentalsButton = gui.Button(width=28, height=28, states=[flatsImage, sharpsImage], name='AccidentalsButton')
PlayheadButton = gui.Button(width=28, height=28, states=[headImage, headAltImage], name='PlayheadButton')
BrushButton = gui.Button(width=28, height=28, states=[brushImage, eraserImage, selectImage], name='BrushButton')
ControlButtons = frame.Panel(
    [PlayPauseButton, AccidentalsButton, PlayheadButton, BrushButton],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1,
    },
    name="ControlButtons"
)

BeatLengthDownButton = gui.Button(width=20, height=28, states=[downChevronImage], name='BeatLengthDownButton')
BeatLengthTextBox = gui.TextBox(width=90, height=28, suffix='tiles', name='BeatLengthTextBox')
BeatLengthTextBox.linkToValue(BeatLength)
BeatLengthUpButton = gui.Button(width=20, height=28, states=[upChevronImage], name='BeatLengthUpButton')
BeatLengthControls = frame.Panel(
    [BeatLengthDownButton, BeatLengthTextBox, BeatLengthUpButton],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1,
    },
    name="BeatLengthControls"
)

BeatsPerMeasureUpButton = gui.Button(width=20, height=28, states=[upChevronImage], name='BeatsPerMeasureUpButton')
BeatsPerMeasureTextBox = gui.TextBox(width=90, height=28, suffix='beats', name='BeatsPerMeasureTextBox')
BeatsPerMeasureTextBox.linkToValue(BeatsPerMeasure)
BeatsPerMeasureDownButton = gui.Button(width=20, height=28, states=[downChevronImage], name='BeatsPerMeasureDownButton')
BeatsPerMeasureControls = frame.Panel(
    [BeatsPerMeasureDownButton, BeatsPerMeasureTextBox, BeatsPerMeasureUpButton],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1,
    },
    name="BeatsPerMeasureControls"
)

LeftToolbar = frame.Panel(
    elements=[ControlButtons, BeatLengthControls, BeatsPerMeasureControls],
    style={
        gap : 24,
    },
    name="LeftToolbar"
)

TempoDownButton = gui.Button(width=20, height=28, states=[downChevronImage], name='TempoDownButton')
TempoTextBox = gui.TextBox(width=120, height=28, suffix='tiles/min', name='TempoTextBox')
TempoTextBox.linkToValue(Tempo)
TempoUpButton = gui.Button(width=20, height=28, states=[upChevronImage], name='TempoUpButton')
TempoControls = frame.Panel(
    elements=[TempoDownButton, TempoTextBox, TempoUpButton],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1,
    },
    name="TempoControls"
)

ColorButton = gui.Button(width=28, height=28, states=custom.getColorStates(28, 28, source_path), name='ColorButton')
WaveDropdown = gui.Dropdown(width=64, height=28, states=instrumentImages, image=upDownChevronImage, name='WaveDropdown')
WaveControls = frame.Panel(
    [ColorButton, WaveDropdown],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1,
    },
    name="WaveControls"
)

KeyDropdown = gui.Dropdown(width=60, height=28, states=NOTES_FLAT, image=upDownChevronImage, name='KeyDropdown')
ModeDropdown = gui.Dropdown(width=140, height=28, states=modes, image=upDownChevronImage, name='ModeDropdown')
KeySignatureControls = frame.Panel(
    [KeyDropdown, ModeDropdown],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1, 
    },
    name="KeySignatureControls"
)

QuestionButton = gui.Button(width=28, height=28, states=[questionImage], name='QuestionButton')
QuestionButtonPanel = frame.Panel(
    [QuestionButton],
    style={
        background : gui.COLOR_BORDER,
        rounding : 3,
        gap : 1,
        padding: 1, 
    },
    name="QuestionButtonPanel"
)

RightToolbar = frame.Panel(
    [TempoControls, WaveControls, KeySignatureControls, QuestionButtonPanel],
    style={
        gap : 24,
    },
    name="RightToolbar"
)

WorldMessageLabel = gui.Label(width=width, height=20, text=WorldMessage, name='WorldMessage')
MessagePanel = frame.Panel(
    [WorldMessageLabel],
    style={
        display : "fixed"
    },
    name="MessagePanel"
)

ToolBar = frame.Panel(
    [LeftToolbar, RightToolbar, MessagePanel],
    style={
        background : gui.COLOR_BG,
        border : (0, 0, 1, 0),
        borderColor : (255, 0, 0, 0),
        display : "fixed",
        offset : [0, 0],
        align : "center",
        justify : "spread",
        sizing : ["fill", 80],
        padding : 26
    },
    name="ToolBar"
)

PitchList = custom.PitchList(width=80, height=height-80, name='PitchList')
NoteGrid = custom.NoteGrid(width=width-80, height=height-80, name='NoteGrid')
PlayHead = custom.PlayHead()

def bumpRight():
    if playing: custom.viewCol.set(custom.viewCol.value + 25)

PlayHead.onExitView(bumpRight)

NotePanel = frame.Panel(
    elements=[NoteGrid, PlayHead],
    style={
        background : gui.COLOR_BG,
        sizing: ['fill', 'fill']
    },
    name="NotePanel"
)
PlayHead.setLinkedPanel(NotePanel)
PitchPanel = frame.Panel(
    elements=[PitchList],
    style={
        background : gui.COLOR_BG,
        sizing: [80, 'fill']
    },
    name="PitchPanel"
)

NoteGrid.setLinkedPanels(NotePanel, PitchPanel)
PitchList.setLinkedPanels(PitchPanel)

GridPanel = frame.Panel(
    [PitchPanel, NotePanel],
    style={
        sizing: ['fill', 'fill']
    },
    name="GridPanel"
)
# every value below is defined in this module; the components read them live through these
# getters, so they are wired exactly once and never need re-pushing when the value changes
def getNoteMap(): return noteMap
def getColorNames(): return justColorNames
def getColorIndex(): return ColorButton.currentStateIdx
def getBeatLength(): return BeatLength.value
def getBeatsPerMeasure(): return BeatsPerMeasure.value
def getKeyIndex(): return NOTES_SHARP.index(Key.value) if ('#' in Key.value) else NOTES_FLAT.index(Key.value)
def getModeIntervals(): return modesMap[Mode.value]
def getPitchListNotes(): return NOTES_FLAT if (AccidentalsButton.currentStateIdx == 0) else NOTES_SHARP
def getPitchListWave(): return waveMap

NoteGrid.setNoteMap(getNoteMap)
NoteGrid.setColorNames(getColorNames)
NoteGrid.setColor(getColorIndex)
NoteGrid.setIntervals(getBeatLength, getBeatsPerMeasure)
NoteGrid.setMode(getModeIntervals)
NoteGrid.setKey(getKeyIndex)

PitchList.setMode(getModeIntervals)
PitchList.setKey(getKeyIndex)
PitchList.setNotes(getPitchListNotes)
PitchList.setWave(getPitchListWave)

MasterPanel = frame.Panel(
    [GridPanel, ToolBar],
    style={
        background : gui.COLOR_BG,
        sizing: ["fill", "fill"],
        padding: [80, 0, 0, 0]
    },
    name="MasterPanel"
)

dom.init(MasterPanel)

MasterPanel.visualizeHierarchy()
MasterPanel.calculateDimensions([width, height])
MasterPanel.relativeToScreenSpace([0, 0])
dom.setZOrderRecursively(MasterPanel)


console.log("Initialized GUI Objects "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### GUI LOGIC ######

# PlayPauseButton.onMouseEnter(lambda: (WorldMessage.setText("Control playback"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# PlayPauseButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# AccidentalsButton.onMouseEnter(lambda: (WorldMessage.setText("Toggle between sharps and flats"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# AccidentalsButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# PlayheadButton.onMouseEnter(lambda: (WorldMessage.setText("Set where to play from"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# PlayheadButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# BrushButton.onMouseEnter(lambda: (WorldMessage.setText("Toggle brush type"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# BrushButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))

# TempoDownButton.onMouseEnter(lambda: (WorldMessage.setText("Decrease Tempo.value"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# TempoDownButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# TempoUpButton.onMouseEnter(lambda: (WorldMessage.setText("Increase Tempo.value"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# TempoUpButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# BeatLengthDownButton.onMouseEnter(lambda: (WorldMessage.setText("Decrease beat length (in tiles)"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# BeatLengthDownButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# BeatLengthUpButton.onMouseEnter(lambda: (WorldMessage.setText("Increase beat length (in tiles)"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# BeatLengthUpButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# BeatsPerMeasureDownButton.onMouseEnter(lambda: (WorldMessage.setText("Decrease # of beats per measure"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# BeatsPerMeasureDownButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# BeatsPerMeasureUpButton.onMouseEnter(lambda: (WorldMessage.setText("Increase # of beats per measure"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# BeatsPerMeasureUpButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))

# QuestionButton.onMouseEnter(lambda: (WorldMessage.setText("Open Symphony Help"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# QuestionButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))

# ModeDropdown.onMouseEnter(lambda: (WorldMessage.setText("Change musical mode"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# ModeDropdown.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# KeyDropdown.onMouseEnter(lambda: (WorldMessage.setText("Change key"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# KeyDropdown.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# WaveDropdown.onMouseEnter(lambda: (WorldMessage.setText("Change the sound of this channel"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# WaveDropdown.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
# ColorButton.onMouseEnter(lambda: (WorldMessage.setText("Cycle color channel"), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
# ColorButton.onMouseLeave(lambda: (WorldMessage.setText(""), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))

# Key, Mode
KeyDropdown.setCurrentState(keyIndex)
ModeDropdown.setCurrentState(modes.index(Mode.value))

def playPauseToggle():
    global playing, play_obj, Tempo
    playing = not playing
    PlayPauseButton.cycleStates()
    PlayPauseButton.render(screen, 'screen')
    if playing:
        play_obj = sp.playFull(noteMap, waveMap, PlayHead.time, Tempo.value, volume=0.3,
                               channel='all' if ColorButton.currentStateIdx == 6 else ColorButton.currentStateIdx)
        PlayHead.play(Tempo.value)
    else:
        PlayHead.stop()
        NotePanel.render(screen, 'screen')
        try: play_obj.stop()
        except: None

PlayPauseButton.onMouseClick(playPauseToggle)

def headToggle():
    global head
    head = not head
    PlayheadButton.setCurrentState(1 if head else 0)

PlayheadButton.onMouseClick(headToggle)

# Tempo, BeatsPerMeasure, BeatLength Restrictions
TempoTextBox.setInputRestrictions('numeric')
TempoTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) != 0 and int(x) > 9))

BeatsPerMeasureTextBox.setInputRestrictions('numeric')
BeatsPerMeasureTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) > 0))

BeatLengthTextBox.setInputRestrictions('numeric')
BeatLengthTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) > 0))

# Tempo Controls
def tempoUp():
    global Tempo
    Tempo.value += 1
    psm.pushEditorSnapshotTransaction("CHANGE_TEMPO", "Change Tempo.value")

def tempoDown():
    global Tempo
    Tempo.value = max(10, Tempo.value - 1)
    psm.pushEditorSnapshotTransaction("CHANGE_TEMPO", "Change Tempo.value")

TempoTextBox.watch([Tempo])
TempoUpButton.onMouseClick(tempoUp)
TempoDownButton.onMouseClick(tempoDown)

# Beats Per Measure Controls
def beatsPerMeasureUp():
    global BeatsPerMeasure
    BeatsPerMeasure.value += 1
    psm.pushEditorSnapshotTransaction("CHANGE_BEATS_PER_MEASURE", "Change beats per measure")

def beatsPerMeasureDown():
    global BeatsPerMeasure
    BeatsPerMeasure.value = max(1, BeatsPerMeasure.value - 1)
    psm.pushEditorSnapshotTransaction("CHANGE_BEATS_PER_MEASURE", "Change beats per measure")

BeatsPerMeasureUpButton.onMouseClick(beatsPerMeasureUp)
BeatsPerMeasureDownButton.onMouseClick(beatsPerMeasureDown)

# Beat Length Controls
def beatLengthUp():
    global BeatLength
    BeatLength.value += 1
    psm.pushEditorSnapshotTransaction("CHANGE_BEAT_LENGTH", "Change beat length")

def beatLengthDown():
    global BeatLength
    BeatLength.value = max(1, BeatLength.value - 1)
    psm.pushEditorSnapshotTransaction("CHANGE_BEAT_LENGTH", "Change beat length")

BeatLengthUpButton.onMouseClick(beatLengthUp)
BeatLengthDownButton.onMouseClick(beatLengthDown)

# Accidentals Controls
def toggleAccidentals():
    AccidentalsButton.cycleStates()
    AccidentalsButton.render(screen, 'screen')
    if AccidentalsButton.currentStateIdx == 0: # changed to flats
        KeyDropdown.states = NOTES_FLAT
        KeyDropdown.setCurrentState(keyIndex)
        KeyDropdown.render(screen, 'screen')
    else:
        KeyDropdown.states = NOTES_SHARP
        KeyDropdown.setCurrentState(keyIndex)
        KeyDropdown.render(screen, 'screen')
AccidentalsButton.onMouseClick(toggleAccidentals)

def finalizeKey():
    global Key
    Key.value = KeyDropdown.currentState
    psm.pushEditorSnapshotTransaction("CHANGE_KEY", "Change key")

def finalizeMode():
    global Mode
    Mode.value = ModeDropdown.currentState
    psm.pushEditorSnapshotTransaction("CHANGE_MODE", "Change mode")

KeyDropdown.onSelect(finalizeKey)
ModeDropdown.onSelect(finalizeMode)

GridPanel.watch([BeatsPerMeasure, BeatLength, Key, Mode])

def finalizeWave():
    global waveMap
    waveMap[justColorNames[ColorButton.currentStateIdx]] = WaveDropdown.currentStateIdx
    psm.pushEditorSnapshotTransaction("CHANGE_WAVE_TYPE", "Change wave type")

def colorSync():
    if ColorButton.currentStateIdx != 6:
        WaveDropdown.setCurrentState(waveMap[justColorNames[ColorButton.currentStateIdx]])

    # Clear selections when switching to universal view (channel 6)
    if ColorButton.currentStateIdx == 6:
        for color, notes in noteMap.items():
            # console.log(notes)
            clearSelection(notes)
    
    NotePanel.render(screen, 'screen')

def cycleColor():
    oldColor = ColorButton.currentStateIdx
    ColorButton.cycleStates()
    colorSync()
    if oldColor != ColorButton.currentStateIdx:
        psm.pushEditorSnapshotTransaction("CHANGE_COLOR", "Change color channel")

WaveDropdown.onSelect(finalizeWave)
WaveDropdown.onClose(lambda: MasterPanel.render(screen, 'screen'))
ColorButton.onMouseClick(cycleColor)
QuestionButton.onMouseClick(lambda: webbrowser.open(questions_url))

console.log("Initialized GUI Methods "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### FUNCTIONS ######

def deleteZeroDurationNotes():
    '''
    fields: none
    outputs: nothing
    
    Deletes all notes that have zero duration.
    '''
    global noteMap

    for color, notes in noteMap.items():
        #console.log([n for n in notes if n.duration == 0])
        noteMap[color] = [n for n in notes if n.duration != 0]

def trimOverlappingNotes():
    '''
    fields: none
    outputs: nothing
    
    Shortens notes so that overlapping notes of the SAME pitch
    in the SAME color channel do not overlap.
    '''
    global noteMap

    for color, notes in noteMap.items():

        # Group notes by pitch
        notes_by_pitch = defaultdict(list)
        for note in notes:
            notes_by_pitch[note.pitch].append(note)

        # Process each pitch independently
        for pitch, pitch_notes in notes_by_pitch.items():
            pitch_notes.sort(key=lambda n: n.time)

            for i in range(len(pitch_notes) - 1):
                current = pitch_notes[i]
                next_note = pitch_notes[i + 1]

                current_end = current.time + current.duration

                if next_note.time < current_end:
                    current.duration = max(0, next_note.time - current.time)

def preprocess():
    '''
    fields: none
    outputs: nothing

    Preprocesses the note map to remove overlapping notes and delete notes with zero duration.
    '''
    trimOverlappingNotes()
    deleteZeroDurationNotes()


def snapshotEditorState():
    '''
    fields: none\n
    outputs: dict

    Returns a snapshot of editor state needed to replay undo/redo deterministically.
    '''
    return {
        "noteMap"         : pst.snapshotNoteMapState(noteMap),
        "waveMap"         : copy.deepcopy(waveMap),
        "tempo"           : int(Tempo.value),
        "beatLength"      : int(BeatLength.value),
        "beatsPerMeasure" : int(BeatsPerMeasure.value),
        "key"             : str(KeyDropdown.currentState),
        "mode"            : str(ModeDropdown.currentState),
        "accidentals"     : "flats" if AccidentalsButton.currentStateIdx == 0 else "sharps",
        "colorIndex"      : int(ColorButton.currentStateIdx),
        "waveIndex"       : int(WaveDropdown.currentStateIdx)
    }


def applyNoteMapSnapshot(targetNoteMap, noteMapSnapshot):
    '''
    fields:
        targetNoteMap (dict) - runtime note map to mutate\n
        noteMapSnapshot (dict) - serialized note map snapshot
    outputs: nothing

    Rebuilds the runtime note map from a snapshot.
    '''
    targetNoteMap.clear()
    for colorName in justColorNames[:6]:
        targetNoteMap[colorName] = []

    for colorName, notes in noteMapSnapshot.items():
        if colorName not in targetNoteMap:
            targetNoteMap[colorName] = []
        for noteData in notes:
            newNote = custom.Note({
                "pitch": noteData["pitch"],
                "time": noteData["time"],
                "duration": noteData["duration"],
                "data_fields": copy.deepcopy(noteData.get("data_fields", {}))
            })
            if noteData.get("selected", False):
                newNote.select()
            else:
                newNote.unselect()
            targetNoteMap[colorName].append(newNote)


def applyEditorStateToRuntime(stateSnapshot):
    '''
    fields:
        stateSnapshot (dict) - full editor snapshot to apply
    outputs: nothing

    Applies a replayed snapshot to live runtime globals and UI controls.
    '''
    global noteMap, waveMap, Tempo, BeatLength, BeatsPerMeasure, Key, Mode
    global suspendTransactionCapture

    suspendTransactionCapture = True
    try:
        applyNoteMapSnapshot(noteMap, stateSnapshot.get("noteMap", {}))
        waveMap = copy.deepcopy(stateSnapshot.get("waveMap", waveMap))
        Tempo.value = int(stateSnapshot.get("Tempo.value", Tempo.value))
        BeatLength.value = int(stateSnapshot.get("beatLength", BeatLength.value))
        BeatsPerMeasure.value = int(stateSnapshot.get("beatsPerMeasure", BeatsPerMeasure.value))
        Key.value = stateSnapshot.get("key", Key.value)
        Mode.value = stateSnapshot.get("mode", Mode.value)

        accidentalsState = stateSnapshot.get("accidentals", "flats")
        AccidentalsButton.setCurrentState(0 if accidentalsState == "flats" else 1)
        KeyDropdown.states = NOTES_FLAT if accidentalsState == "flats" else NOTES_SHARP

        try:
            keyIdx = KeyDropdown.states.index(Key.value)
        except ValueError:
            keyIdx = 0
        KeyDropdown.setCurrentState(keyIdx)

        if Mode.value in modes:
            ModeDropdown.setCurrentState(modes.index(Mode.value))

        ColorButton.setCurrentState(int(stateSnapshot.get("colorIndex", ColorButton.currentStateIdx)))
        WaveDropdown.setCurrentState(int(stateSnapshot.get("waveIndex", WaveDropdown.currentStateIdx)))
        colorSync()
        preprocess()
        MasterPanel.render(screen, 'screen')
    finally:
        suspendTransactionCapture = False

psm = pst.ProjectStateManager(
    snapshotEditorState=snapshotEditorState,
    applyEditorStateToRuntime=applyEditorStateToRuntime,
    isCaptureSuspended=lambda: suspendTransactionCapture
)
    
console.log("Initialized Static Methods "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### NOTEGRID FUNCTIONALITY ######

selectingAnything = False
draggingSelection = False
selectionStartPos = None
dragStartGridPos = None
drawStartPos = None
extendingNote = False
extendStartGridPos = None
activeBrushNote = None

def getNoteAt(notes, time, pitch):
    for note in notes:
        if note.pitch == pitch and note.time <= time < note.time + note.duration:
            return note
    return None

def getExtendingNote(notes, time, pitch):
    for note in notes:
        delta = 0.5 if note.duration > 1 else 0.25
        if note.pitch == pitch and (note.time + note.duration - delta) <= time < note.time + note.duration:
            return note
    return False

def clearSelection(notes):
    for note in notes:
        note.unselect()

def removeAt(time, pitch, color):
    notes: list[custom.Note] = noteMap[color]
    for note in notes:
        if note.time == time and note.pitch == pitch:
            notes.remove(note)
            return note
    return None

def handleClick():
    global selectingAnything, draggingSelection, selectionStartPos, dragStartGridPos, drawStartPos, extendingNote, extendStartGridPos, activeBrushNote, head, waveMap
    if (pygame.mouse.get_pos()[1] < 80) or (pygame.mouse.get_pos()[0] < 80):
        # console.log("click was outside of the notegrid, we don't care")
        return
    if ModeDropdown.expanded:
        if pygame.rect.Rect(ModeDropdown.x, ModeDropdown.y, ModeDropdown.width, ModeDropdown.height).collidepoint(pygame.mouse.get_pos()):
            #console.log("click was on mode dropdown, we don't care")
            return
    if KeyDropdown.expanded:
        if pygame.rect.Rect(KeyDropdown.x, KeyDropdown.y, KeyDropdown.width, KeyDropdown.height).collidepoint(pygame.mouse.get_pos()):
            #console.log("click was on key dropdown, we don't care")
            return
    if WaveDropdown.expanded:
        if pygame.rect.Rect(WaveDropdown.x, WaveDropdown.y, WaveDropdown.width, WaveDropdown.height).collidepoint(pygame.mouse.get_pos()):
            #console.log("click was on wave dropdown, we don't care")
            return

    mouseTime, mousePitch = custom.convertWorldToGrid(pygame.mouse.get_pos(), rect=pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height))
    mouseTimeExact, _mousePitch = custom.convertWorldToGrid(pygame.mouse.get_pos(), timeInt=False, rect=pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height))

    drawStartPos = (mouseTime, mousePitch)
    if mouseTime is None:
        return
    if head:
        head = False
        PlayHead.setHome(mouseTime)
        # console.log(f"home: {mouseTime}")
        PlayheadButton.setCurrentState(0)
        PlayheadButton.render(screen, 'screen')
        NotePanel.render(screen, 'screen')
        return
    if ColorButton.currentStateIdx == 6:
        return

    if brushType in ["brush", "eraser", "select"]:
        psm.beginInteractionTransaction(brushType)

    currColorName = colorsList[ColorButton.currentStateIdx][0]
    if not (currColorName in noteMap):
        noteMap[currColorName] = []
    notes = noteMap[currColorName]

    if brushType == "brush":
        notes: list[custom.Note] = noteMap[currColorName]
        activeBrushNote = custom.Note({
            "pitch"       : mousePitch,
            "time"        : mouseTime,
            "duration"    : 1,
            "data_fields" : {}
        })
        # Track the note created for this mouse-down so drag only extends this note.
        noteMap[currColorName].append(activeBrushNote)
        sp.playNote(note=mousePitch, waves=waveMap[justColorNames[ColorButton.currentStateIdx]], duration=0.2)
    elif brushType == "eraser":
        notes: list[custom.Note] = noteMap[currColorName]
        removeAt(mouseTime, mousePitch, currColorName)
    else:
        activeBrushNote = None

    clickedNote = getNoteAt(notes, mouseTime, mousePitch)
    shiftHeld = pygame.key.get_pressed()[pygame.K_LSHIFT]
    altHeld = pygame.key.get_pressed()[pygame.K_LALT]
    extendingNote = getExtendingNote(notes, mouseTimeExact, mousePitch)

    if clickedNote:
        if extendingNote:
            extendStartGridPos = (mouseTime, mousePitch)
        selectingAnything = True
        draggingSelection = True
        dragStartGridPos = (mouseTime, mousePitch)

        # Shift allows multi-select
        if not shiftHeld and not clickedNote.selected:
            clearSelection(notes)

        if clickedNote.selected:
            #clickedNote.unselect()
            None
        else:
            clickedNote.select()
            if not extendingNote:
                sp.playNote(note=clickedNote.pitch, waves=waveMap[justColorNames[ColorButton.currentStateIdx]], duration=0.2)

        if extendingNote:
            for note in notes:
                if note.selected:
                    note.extendOriginalDuration = note.duration
        else:
            # Cache drag start positions
            for note in notes:
                if note.selected:
                    note.dragInitialPosition = (note.time, note.pitch)
            
            if altHeld:
                for note in notes:
                    if note.selected:
                        notes.append(custom.Note({
                            "pitch"       : note.pitch,
                            "time"        : note.time,
                            "duration"    : note.duration,
                            "data_fields" : note.dataFields
                        }))

    else:
        # Clicked empty space
        if not shiftHeld:
            clearSelection(notes)

        selectingAnything = False
        draggingSelection = False
        selectionStartPos = [pygame.mouse.get_pos()[0] - NoteGrid.x, pygame.mouse.get_pos()[1] - NoteGrid.y]

    NotePanel.render(screen, 'screen')

def handleDrag(xy):
    global selectingAnything, draggingSelection, drawStartPos, extendingNote, activeBrushNote
    if not pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height).collidepoint(pygame.mouse.get_pos()):
        return

    mouseTime, mousePitch = custom.convertWorldToGrid(pygame.mouse.get_pos(), rect=pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height))
    if mouseTime is None or ColorButton.currentStateIdx == 6:
        return

    currColorName = colorsList[ColorButton.currentStateIdx][0]
    notes = noteMap[currColorName]

    if brushType == "brush":
        if not activeBrushNote:
            return
        if mousePitch != activeBrushNote.pitch:
            return
        if mouseTime >= activeBrushNote.time:
            activeBrushNote.duration = mouseTime - activeBrushNote.time + 1
    elif brushType == "eraser":
        notes: list[custom.Note] = noteMap[currColorName]
        for note in notes:
            if (mousePitch == note.pitch) and (
                (mouseTime >= note.time) and (mouseTime < note.time + note.duration)
                ):
                notes.remove(note)
    elif brushType == 'select':
        if extendingNote:
            # EXTEND/RETRACT
            dx = round(xy[0] / custom.tileWidth.value)
            dy = -round(xy[1] / custom.tileHeight.value)
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)

            for note in notes:
                if note.selected and note.extendOriginalDuration:
                    note.duration = note.extendOriginalDuration + dx
                    if note.duration == 0:
                        note.extendOriginalDuration += 1
                    note.duration = note.extendOriginalDuration + dx
        elif draggingSelection:
            # GRID-SNAPPED MOVE
            dx = round(xy[0] / custom.tileWidth.value)
            dy = -round(xy[1] / custom.tileHeight.value)

            for note in notes:
                if note.selected and note.dragInitialPosition:
                    note.time = note.dragInitialPosition[0] + dx
                    note.pitch = note.dragInitialPosition[1] + dy
        else:
            # SELECTION BOX
            x0, y0 = selectionStartPos
            x1, y1 = [pygame.mouse.get_pos()[0] - NoteGrid.x, pygame.mouse.get_pos()[1] - NoteGrid.y]

            selectionRect = pygame.Rect(
                min(x0, x1),
                min(y0, y1),
                abs(x1 - x0),
                abs(y1 - y0)
            )
            NoteGrid.setSelection(selectionRect)

            for note in notes:
                note_x, note_y = custom.convertGridToWorld(note.time, note.pitch)
                note_rect = pygame.Rect(note_x, note_y, note.duration * custom.tileWidth.value, custom.tileHeight.value)

                if selectionRect.colliderect(note_rect): note.select()
                elif not pygame.key.get_pressed()[pygame.K_LSHIFT]: note.unselect()

    NotePanel.render(screen, 'screen')

def handleUnDrag():
    '''
    fields: none\n
    outputs: nothing

    Finalizes drag interactions, commits transaction state, and restores normal cursor/render state.
    '''
    global activeBrushNote
    if not pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height).collidepoint(pygame.mouse.get_pos()):
        activeBrushNote = None
        return

    psm.finalizeInteractionTransaction()
    NoteGrid.selectionRect = None
    preprocess()
    activeBrushNote = None
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    NotePanel.render(screen, 'screen')

def handleUnClick():
    global activeBrushNote
    if not pygame.Rect(NoteGrid.x, NoteGrid.y, NoteGrid.width, NoteGrid.height).collidepoint(pygame.mouse.get_pos()):
        activeBrushNote = None
        return
    psm.finalizeInteractionTransaction()
    NoteGrid.selectionRect = None
    preprocess()
    activeBrushNote = None
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    NotePanel.render(screen, 'screen')

NoteGrid.onMouseClick(handleClick)
NoteGrid.onMouseDrag(handleDrag)
NoteGrid.onMouseUnDrag(handleUnDrag)
NoteGrid.onMouseUnClick(handleUnClick)

console.log("Initialized NoteGrid Functionality "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()
console.message("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')
pcrw.startProcessCommandServer()
console.message(f"Process command server listening on localhost:{pcrw.PROCESS_COMMAND_PORT}.")

###### MAINLOOP ######

gui_running = False
run = True

root = None
last_update = time.time()


_lastFullFrame = None


def handleResize(new_w, new_h, full=True):
    '''
    fields:
        new_w (number) - new screen width
        new_h (number) - new screen height
        full (bool) - whether or not to perform a full recalc

    Resize the display surface and reflow the UI to the new dimensions.
    '''
    global screen, width, height, _lastFullFrame

    width, height = (max(new_w, minWidth), max(new_h, minHeight))

    # SDL already resized the window surface for us, so avoid set_mode() here
    screen = pygame.display.get_surface()
    if screen is None or screen.get_size() != (width, height):
        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
        sdl.reapply_minimum_window_size()  # set_mode() wipes the minimum size

    if not full:
        screen.fill((36, 36, 36))
        if _lastFullFrame is not None:
            screen.blit(_lastFullFrame, (0, 0))
        pygame.display.flip()
        return

    NoteGrid.viewBounds()
    MasterPanel.calculateDimensions([width, height])
    MasterPanel.relativeToScreenSpace([0, 0])

    MasterPanel.render(screen, 'screen')
    _lastFullFrame = screen.copy()
    pygame.display.flip()

while run:
    while not gui_running:
        pc_data = pcrw.waitForOpenCommand()

        if pc_data != None:
            gui_running = True
            args = pc_data['args']
            title_text = args['project_file_name']

            working_file_path = path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'
            with open(working_file_path, "rb") as pf:
                ps = sl.toProgramState(pkl.load(pf))

            user_settings_path = path.join(args['symphony_data_path'], 'user-settings.json')
            with open(user_settings_path) as settings_file:
                settings = json.load(settings_file)

            directory_path = path.join(args['symphony_data_path'], 'directory.json')
            with open(directory_path) as directory_file:
                directory = json.load(directory_file)

            autoSave = False if settings['disable_auto_save'] else directory["Symphony Auto-Save"][0]["Auto-Save"]
            showButtonTooltips = settings['show_button_tooltips']

            WorldMessageLabel.setDisabled(not showButtonTooltips)
            console.log(ps)

            noteMap : dict[str: list] = ps["noteMap"]
            waveMap = ps["waveMap"]
            Key.value = ps["key"]
            BeatLength.value = ps['beatLength']
            BeatsPerMeasure.value = ps['beatsPerMeasure']
            if "#" in Key.value:
                accidentals = "sharps"
                KeyDropdown.states = NOTES_SHARP
                AccidentalsButton.setCurrentState(1)
            elif "b" in Key.value:
                accidentals = "flats"
                KeyDropdown.states = NOTES_FLAT
                AccidentalsButton.setCurrentState(0)
            try:
                keyIndex = KeyDropdown.states.index(Key.value)
            except ValueError:
                keyIndex = 0
            Mode.value = ps["mode"]
            Tempo.value = ps["tpm"]
            projectMeta = copy.deepcopy(ps["meta"])

            KeyDropdown.setCurrentState(keyIndex)
            ModeDropdown.setCurrentState(modes.index(Mode.value))
            
            # Initialize view position and color channel when opening GUI
            custom.viewRow.set(50)
            custom.viewCol.set(0)
            ColorButton.setCurrentState(0)
            
            # On macOS, show the hidden window; on other platforms, reinitialize
            if platform == 'mac' and pygame.display.get_init():
                # Window was hidden, not destroyed - show it and update
                try:
                    plat.setDockIconVisible(True)
                    sdl_window = SDLWindow.from_display_module()
                    sdl_window.show()
                    pygame.display.set_caption(f"{title_text} - Symphony v1.1.5")
                    screen = pygame.display.get_surface()
                    if screen is None or screen.get_size() != (width, height):
                        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
                except Exception as e:
                    console.warn(f"Error showing hidden window: {e}")
                    # Fallback to full init
                    pygame.display.init()
                    pygame.display.set_caption(f"{title_text} - Symphony v1.1.5")
                    pygame.display.set_icon(gameIcon)
                    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
            else:
                # Standard initialization for Windows/Linux or first run
                if platform == 'mac':
                    plat.setDockIconVisible(True)
                pygame.display.init()
                pygame.display.set_caption(f"{title_text} - Symphony v1.1.5")
                pygame.display.set_icon(gameIcon)
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)

            sdl.install_live_resize_watch(handleResize)
            # if not sdl.set_minimum_window_size(minWidth, minHeight):
            #     console.warn("Could not set native minimum window size")

            colorSync()
            PlayHead.setHome(0)
            MasterPanel.render(screen, 'screen')
            _lastFullFrame = screen.copy()
            psm.resetTransactionHistory()
            pygame.event.pump()
            pygame.display.flip()
            plat.bringEditorWindowToFront()

    while gui_running:
        try:
            events.pump()

            saveFrame += 60 * (1 / fps)
            if saveFrame > 1200: # Saves every 20 seconds
                saveFrame = 0
                working_file_path
                WorldMessage.value = fio.dumpToFile(
                                        workingFile  = working_file_path,
                                        destFile     = working_file_path,
                                        programState = sl.newProgramState(Key.value, Mode.value, Tempo.value, noteMap, waveMap, BeatLength.value, BeatsPerMeasure.value, meta=projectMeta),
                                        autoSave     = autoSave,
                                        titleText    = title_text,
                                        sessionID    = sessionID)

            try:
                MasterPanel.update(screen)
                for event in events.get():
                    if event.type == pygame.QUIT:
                        gui_running = False
            except pygame.error as e:
                traceback.print_exc()
                console.warn('Pygame display was likely quit outside of the main module. Handling and closing properly...\nIf this was unexpected, investigate.')
                gui_running = False
                break

            for event in events.get():
                if event.type == pygame.QUIT:
                    gui_running = False
                    console.warn("Pygame was quit")
                    break
                elif event.type == pygame.VIDEORESIZE:
                    handleResize(event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]:
                        # Skip color channel switching if a text box is selected
                        if not (TempoTextBox.selected or BeatLengthTextBox.selected or BeatsPerMeasureTextBox.selected):
                            oldColorIdx = ColorButton.currentStateIdx
                            numKeyPressed = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7].index(event.key)
                            altHeld = pygame.key.get_pressed()[pygame.K_LALT] or pygame.key.get_pressed()[pygame.K_RALT]
                            draggingNotes = []
                            draggingNotesToNewChannel = numKeyPressed < 6 and NoteGrid.mouseInside and pygame.mouse.get_pressed()[0]
                            # Only move notes when dragging to channels 1-6 (indices 0-5), not to universal view (channel 7, index 6)
                            if draggingNotesToNewChannel:
                                draggingNotes = [note for note in noteMap[justColorNames[ColorButton.currentStateIdx]] if note.selected]
                                noteMap[justColorNames[ColorButton.currentStateIdx]] = [note for note in noteMap[justColorNames[ColorButton.currentStateIdx]] if not note.selected]
                            ColorButton.setCurrentState(numKeyPressed)
                            if draggingNotesToNewChannel:
                                try:
                                    for note in draggingNotes:
                                        noteMap[justColorNames[ColorButton.currentStateIdx]].append(note)
                                except Exception as e:
                                    console.error(e)
                            elif oldColorIdx != ColorButton.currentStateIdx:
                                for notes in noteMap.values():
                                    clearSelection(notes)  # Clear selected notes on channel-only switch (no Alt-drag transfer).
                            colorSync()
                            if oldColorIdx != ColorButton.currentStateIdx:
                                psm.pushEditorSnapshotTransaction("CHANGE_COLOR", "Change color channel")
                    if event.key in [pygame.K_MINUS, pygame.K_EQUALS]: # zoom out horizontally
                        if pygame.key.get_pressed()[CMD_KEY]:
                            zoomIndex = zoomDimensions.index((custom.tileWidth.value, custom.tileHeight.value))
                            if event.key == pygame.K_MINUS:
                                zoomIndex = max(zoomIndex - 1, 0)
                            elif event.key == pygame.K_EQUALS:
                                zoomIndex = min(zoomIndex + 1, len(zoomDimensions) - 1)
                            custom.tileWidth.set(zoomDimensions[zoomIndex][0])
                            custom.tileHeight.set(zoomDimensions[zoomIndex][1])
                            GridPanel.render(screen, 'screen')
                    if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE: # Delete all selected notes
                        beforeDelete = snapshotEditorState()
                        for colorName in noteMap:
                            noteMap[colorName] = [
                                note for note in noteMap[colorName]
                                if not note.selected
                            ]
                        if beforeDelete != snapshotEditorState():
                            psm.pushEditorSnapshotTransaction("DELETE_NOTES", "Delete selected notes")
                        NotePanel.render(screen, 'screen')
                    elif event.key == pygame.K_z and pygame.key.get_pressed()[CMD_KEY]:
                        if pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]:
                            psm.performRedo()
                        else:
                            psm.performUndo()
                    elif event.key == pygame.K_y and pygame.key.get_pressed()[CMD_KEY]:
                        psm.performRedo()
                    elif event.key == pygame.K_a:
                        for note in noteMap[justColorNames[ColorButton.currentStateIdx]]:
                            note.select()
                        NotePanel.render(screen, 'screen')
                    elif event.key == CMD_KEY: # Switch to eraser momentarily
                        brushType = "eraser"
                        BrushButton.setCurrentState(1)
                        BrushButton.render(screen, 'screen')
                    elif event.key == pygame.K_LSHIFT: # Switch to select permanently
                        brushType = "select"
                        BrushButton.setCurrentState(2)
                        BrushButton.render(screen, 'screen')
                    elif event.key == pygame.K_SPACE: # Play / pause
                        playPauseToggle()
                    elif event.key == pygame.K_s:
                        if pygame.key.get_pressed()[CMD_KEY]: # if the user presses Ctrl+S (to save)
                            WorldMessage.value = fio.dumpToFile(
                                workingFile  = working_file_path,
                                destFile     = working_file_path,
                                programState = sl.newProgramState(Key.value, Mode.value, Tempo.value, noteMap, waveMap, BeatLength.value, BeatsPerMeasure.value, meta=projectMeta),
                                autoSave     = autoSave,
                                titleText    = title_text,
                                sessionID    = sessionID)
                            saveFrame = 0
                elif event.type == pygame.KEYUP:
                    if event.key == CMD_KEY: # Switches away from eraser when Ctrl is let go
                        brushType = "brush"
                        BrushButton.setCurrentState(0)
                        BrushButton.render(screen, 'screen')
                        for color, colorChannel in noteMap.items():
                            for note in colorChannel:
                                note.selected = False
                        NotePanel.render(screen, 'screen')
                elif event.type == pygame.WINDOWFOCUSLOST:
                    console.warn("Window unfocused")
                    MasterPanel.render(screen, 'screen')
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    console.warn("Window focused")
                    MasterPanel.render(screen, 'screen')

            if gui_running == False:
                PlayHead.stop()
                break
            dom.flip(screen)  # repaint whatever dirtied itself this frame, then clear the queues
            clock.tick(fps)
            pygame.display.flip()  # Update the display
        except Exception as e:
            gui_running = False
            traceback.print_exc()
            break

    WorldMessage.value = fio.dumpToFile(
        workingFile  = working_file_path,
        destFile     = working_file_path,
        programState = sl.newProgramState(Key.value, Mode.value, Tempo.value, noteMap, waveMap, BeatLength.value, BeatsPerMeasure.value, meta=projectMeta),
        autoSave     = autoSave,
        titleText    = title_text,
        sessionID    = sessionID)
    
    try:
        # On macOS, destroying/recreating pygame's Cocoa window while the
        # daemon persists can hang SDL. Keep the historical hide path, then
        # hide this process from the Dock so closing the editor removes its icon.
        if platform == 'mac':
            try:
                sdl_window = SDLWindow.from_display_module()
                sdl_window.hide()
                plat.setDockIconVisible(False)
                for _ in range(5):
                    pygame.event.pump()
                    time.sleep(0.02)
            except Exception as e:
                console.warn(f"Error hiding window on macOS: {e}")
                if pygame.display.get_init():
                    pygame.display.quit()
        else:
            pygame.event.pump()
            if pygame.display.get_init():
                pygame.display.quit()
    
    except Exception as e:
        console.warn(f"Error during pygame cleanup: {e}")
        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except:
            pass
    
    pcrw.setGuiIsOpen(False)

# full pygame quit only when daemon is completely done
try:
    pygame.quit()
except:
    pass

console.warn("Daemon was quit.")