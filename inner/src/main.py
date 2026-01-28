# main.py
# entry point for the program. contains the mainloop.
###### IMPORT ######
print('Welcome to Symphony v1.1.')

import time
lastTime = time.time()
START_TIME = lastTime

from collections import defaultdict
import dill as pkl
import json
from os import path
import pygame
from pygame._sdl2.video import Window as SDLWindow
import sys
import traceback
import webbrowser

###### INTERNAL MODULES ######

#import console_controls.console_window as cw
from console_controls.console import *

console.log("Imported Libraries "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

import events
import gui.element as gui
import gui.frame as frame
import gui.custom as custom
import process_command.read_write as pcrw
import utils.state_loading as sl
import utils.file_io as fio
import utils.sound_processing as sp

console.log("Imported Modules & Libraries "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

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
    myappid = 'nimbial.symphony.editor.v1-1' # arbitrary string
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    console.warn('Error importing windll or setting Unique AppID. You might be gui_running on a non-Windows platform.')
    pass # Not on Windows or ctypes is not available

####### SYSARG HANDLING ######

SAMPLE_RATE = 44100

console.log(sys.argv)
source_path = sys.argv[1]
process_command_file = sys.argv[2]

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
waveImages = [squareWaveImage, triangleWaveImage, sawtoothWaveImage]

upChevronImage = pygame.image.load(f"{source_path}/assets/up.png")
downChevronImage = pygame.image.load(f"{source_path}/assets/down.png")
upDownChevronImage = pygame.image.load(f"{source_path}/assets/up-down.png")

console.log("Loaded Assets "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PYGAME & WINDOW INITIALIZE ######

width, height = (1100, 592)
minWidth, minHeight = (925, 592)

iconPath = f'{source_path}/assets/icon32x32.png'
if path.exists(iconPath):
    gameIcon = pygame.image.load(iconPath)
else:
    console.warn(f"Warning: Icon file not found at {iconPath}")

pygame.font.init()
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)

clock = pygame.time.Clock()

console.log("Initialized Pygame Data "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### VARIABLE & GUI ELEMENT SETUP ######

fps = 60

worldMessage = ""
questions_url = "https://docs.nimbial.com/symphony/4"

key = 'Eb'
mode = 'Lydian'

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected

page = "Editor"
noteMap : dict[str, list[custom.Note]] = {}

saveFrame = 0

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
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
colorsList = list(colors.items())
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

beatLength = 4
beatsPerMeasure = 4

tpm = 360

mainFont = f'{source_path}/assets/InterVariable.ttf'
gui.init(source_path)

zoomDimensions = [
    (18, 24),
    (22, 26),
    (26, 28),
    (30, 30),
    (40, 40),
    (60, 48),
    (80, 54),
    (100, 56)
]

###### ASSETS ######

PlayPauseButton = gui.Button(pos=(26, 26), width=28, height=28, states=[playImage, pauseImage])
AccidentalsButton = gui.Button(pos=(60, 26), width=28, height=28, states=[flatsImage, sharpsImage])
PlayheadButton = gui.Button(pos=(94, 26), width=28, height=28, states=[headImage, headAltImage])
BrushButton = gui.Button(pos=(128, 26), width=28, height=28, states=[brushImage, eraserImage, selectImage])
LeftToolbar = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                           [PlayPauseButton, AccidentalsButton, PlayheadButton, BrushButton],
                           name="LeftToolbar")

TempoDownButton = gui.Button(pos=(180, 26), width=20, height=28, states=[downChevronImage])
TempoTextBox = gui.TextBox(pos=(205, 26), width=105, height=28, text='360')
TempoUpButton = gui.Button(pos=(315, 26), width=20, height=28, states=[upChevronImage])
TempoControls = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                            [TempoDownButton, TempoTextBox, TempoUpButton],
                            name="TempoControls")

BeatLengthDownButton = gui.Button(pos=(width - 516, 26), width=20, height=28, states=[downChevronImage])
BeatLengthTextBox = gui.TextBox(pos=(width - 491, 26), width=30, height=28, text='4')
BeatLengthUpButton = gui.Button(pos=(width - 456, 26), width=20, height=28, states=[upChevronImage])
BeatLengthControls = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                                    [BeatLengthDownButton, BeatLengthTextBox, BeatLengthUpButton],
                                    name="BeatLengthControls")

BeatsPerMeasureDownButton = gui.Button(pos=(width - 412, 26), width=20, height=28, states=[downChevronImage])
BeatsPerMeasureTextBox = gui.TextBox(pos=(width - 387, 26), width=30, height=28, text='4')
BeatsPerMeasureUpButton = gui.Button(pos=(width - 352, 26), width=20, height=28, states=[upChevronImage])
BeatsPerMeasureControls = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                                    [BeatsPerMeasureDownButton, BeatsPerMeasureTextBox, BeatsPerMeasureUpButton],
                                    name="BeatsPerMeasureControls")

colorStates = custom.getColorStates(28, 28, source_path)
ColorButton = gui.Button(pos=(width - 308, 26), width=28, height=28, states=colorStates)
WaveButton = gui.Button(pos=(width - 275, 26), width=28, height=28, states=[squareWaveImage, triangleWaveImage, sawtoothWaveImage, "Pno"])
KeyDropdown = gui.Dropdown(pos=(width - 223, 26), width=40, height=28, states=NOTES_FLAT, image=upDownChevronImage)
ModeDropdown = gui.Dropdown(pos=(width - 178, 26), width=100, height=28, states=modes, image=upDownChevronImage)
QuestionButton = gui.Button(pos=(width - 54, 26), width=28, height=28, states=[questionImage])
RightToolbar = frame.Panel((0, 0, width, height), gui.EMPTY_COLOR,
                           [KeyDropdown, ModeDropdown, WaveButton, ColorButton, QuestionButton],
                           name="RightToolbar")

ToolBar = frame.Panel((0, 0, width, height), (0, 0, 0, 0),
                          [RightToolbar, LeftToolbar, BeatLengthControls, BeatsPerMeasureControls, TempoControls],
                          name="ToolBar")

def toolBarGraphics(screen):
    pygame.draw.rect(screen, gui.BG_COLOR, (0, 0, width, 80))
    pygame.draw.line(screen, gui.BORDER_COLOR, (0, 79), (width, 79), 1)

ToolBar.onSelfRender(toolBarGraphics)

NoteGrid = custom.NoteGrid(pos=(0, 0), width=width, height=height)

PitchList = custom.PitchList(pos=(0, 80), width=80, height=height-80, notes=NOTES_FLAT)
PlayHead = custom.PlayHead()

def bumpRight():
    if playing: custom.viewCol += 25

PlayHead.onExitView(bumpRight)

NotePanel = frame.Panel(rect=(80, 80, width-80, height-80), bgColor=gui.BG_COLOR, elements=[NoteGrid, PlayHead],
                        name="NotePanel")
PlayHead.setLinkedPanel(NotePanel)
PitchPanel = frame.Panel(rect=(0, 80, 80, height-80), bgColor=gui.BG_COLOR, elements=[PitchList],
                         name="PitchPanel")

NoteGrid.setLinkedPanels(NotePanel, PitchPanel)
PitchList.setLinkedPanels(PitchPanel)

GridPanel = frame.Panel((0, 80, width, height-80), (0, 0, 0, 0), [NotePanel, PitchPanel],
                        name="GridPanel")
NoteGrid.setNoteMap(noteMap)
NoteGrid.setColorNames(justColorNames)

MasterPanel = frame.Panel((0, 0, width, height), gui.BG_COLOR, [GridPanel, ToolBar],
                          name="MasterPanel")

NoteGrid.setModeKey(key = NOTES_SHARP.index(key) if ('#' in key) else NOTES_FLAT.index(key),
                    mode = modesMap[mode])

console.log("Initialized GUI Objects "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### GUI LOGIC ######

# Key, Mode
KeyDropdown.setCurrentState(keyIndex)
ModeDropdown.setCurrentState(modes.index(mode))

def playPauseToggle():
    global playing, play_obj, tpm
    playing = not playing
    PlayPauseButton.cycleStates()
    PlayPauseButton.render(screen)
    if playing:
        play_obj = sp.playFull(noteMap, waveMap, PlayHead.time, tpm, 0.4,
                               channel='all' if ColorButton.currentStateIdx == 6 else ColorButton.currentStateIdx)
        PlayHead.play(tpm)
    else:
        PlayHead.stop()
        NotePanel.render(screen)
        try: play_obj.stop()
        except: None

PlayPauseButton.onMouseClick(playPauseToggle)

def headToggle():
    global head
    head = not head
    PlayheadButton.setCurrentState(1 if head else 0)

PlayheadButton.onMouseClick(headToggle)

# Tempo, BeatsPerMeasure Restrictions
TempoTextBox.setInputRestrictions('numeric')
TempoTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) != 0))
TempoTextBox.setText(TempoTextBox.getText() + ' tpm')

def addTpmToEnd():
    if not (len(TempoTextBox.getText()) > 4 and TempoTextBox.getText()[-4:] == ' tpm'):
        TempoTextBox.setText(TempoTextBox.getText() + ' tpm')
def removeTpmFromEnd():
    if len(TempoTextBox.getText()) > 4 and TempoTextBox.getText()[-4:] == ' tpm':
        TempoTextBox.setText(TempoTextBox.getText()[:-4])
TempoTextBox.onFocus(removeTpmFromEnd)
TempoTextBox.onBlurFocus(addTpmToEnd)

BeatsPerMeasureTextBox.setInputRestrictions('numeric')
BeatsPerMeasureTextBox.setStateRestrictions(lambda x : (len(x) > 0 and int(x) > 0))

# Tempo Controls
def tempoSync():
    global tempo
    tempo = int(TempoTextBox.getText().replace(' tpm', ''))
    TempoTextBox.setText(str(tempo) + ' tpm')

    TempoControls.render(screen)

def tempoUp():
    global tempo
    tempo += 1
    TempoTextBox.setText(str(tempo) + ' tpm')
    tempoSync()

def tempoDown():
    global tempo
    tempo = max(10, tempo - 1)
    TempoTextBox.setText(str(tempo) + ' tpm')
    tempoSync()

TempoUpButton.onMouseClick(tempoUp)
TempoDownButton.onMouseClick(tempoDown)
TempoTextBox.onBlurFocus(tempoSync)

# Beats Per Measure Controls
def beatsPerMeasureSync():
    global beatsPerMeasure
    beatsPerMeasure = int(BeatsPerMeasureTextBox.getText())
    BeatsPerMeasureControls.render(screen)
    if NoteGrid.beatsPerMeasure != beatsPerMeasure:
        NoteGrid.setIntervals(beatLength, beatsPerMeasure)
        NotePanel.render(screen)

def beatsPerMeasureUp():
    global beatsPerMeasure
    beatsPerMeasure += 1
    BeatsPerMeasureTextBox.setText(beatsPerMeasure)
    beatsPerMeasureSync()

def beatsPerMeasureDown():
    global beatsPerMeasure
    beatsPerMeasure = max(1, beatsPerMeasure - 1)
    BeatsPerMeasureTextBox.setText(beatsPerMeasure)
    beatsPerMeasureSync()

BeatsPerMeasureUpButton.onMouseClick(beatsPerMeasureUp)
BeatsPerMeasureDownButton.onMouseClick(beatsPerMeasureDown)
BeatsPerMeasureTextBox.onBlurFocus(beatsPerMeasureSync)

# Beat Length Controls
def beatLengthSync():
    global beatLength
    beatLength = int(BeatLengthTextBox.getText())
    BeatLengthControls.render(screen)
    if NoteGrid.beatLength != beatLength:
        NoteGrid.setIntervals(beatLength, beatsPerMeasure)
        NotePanel.render(screen)

def beatLengthUp():
    global beatLength
    beatLength += 1
    BeatLengthTextBox.setText(beatLength)
    beatLengthSync()

def beatLengthDown():
    global beatLength
    beatLength = max(1, beatLength - 1)
    BeatLengthTextBox.setText(beatLength)
    beatLengthSync()

BeatLengthUpButton.onMouseClick(beatLengthUp)
BeatLengthDownButton.onMouseClick(beatLengthDown)
BeatLengthTextBox.onBlurFocus(beatLengthSync)

def toggleAccidentals():
    AccidentalsButton.cycleStates()
    AccidentalsButton.render(screen)
    PitchList.setNotes(NOTES_FLAT if (AccidentalsButton.currentStateIdx == 0) else NOTES_SHARP)
    PitchPanel.render(screen)
    if AccidentalsButton.currentStateIdx == 0: # changed to flats
        KeyDropdown.states = NOTES_FLAT
        KeyDropdown.setCurrentState(keyIndex)
        KeyDropdown.render(screen)
    else:
        KeyDropdown.states = NOTES_SHARP
        KeyDropdown.setCurrentState(keyIndex)
        KeyDropdown.render(screen)
AccidentalsButton.onMouseClick(toggleAccidentals)

def finalizeKey():
    NoteGrid.setModeKey(key = KeyDropdown.currentStateIdx)
    PitchList.setModeKey(key = KeyDropdown.currentStateIdx)

def finalizeMode():
    NoteGrid.setModeKey(mode = modesMap[ModeDropdown.currentState])
    PitchList.setModeKey(mode = modesMap[ModeDropdown.currentState])

KeyDropdown.onSelect(finalizeKey)
KeyDropdown.onClose(lambda: MasterPanel.render(screen))
ModeDropdown.onSelect(finalizeMode)
ModeDropdown.onClose(lambda: MasterPanel.render(screen))

def cycleWave():
    global waveMap
    WaveButton.cycleStates()
    waveMap[justColorNames[ColorButton.currentStateIdx]] = WaveButton.currentStateIdx
    PitchList.setWave(WaveButton.currentStateIdx)
    WaveButton.render(screen)

def colorSync():
    ColorButton.render(screen)
    WaveButton.setCurrentState(waveMap[justColorNames[ColorButton.currentStateIdx]])
    PitchList.setWave(WaveButton.currentStateIdx)
    WaveButton.render(screen)
    NoteGrid.color = ColorButton.currentStateIdx
    
    # Clear selections when switching to universal view (channel 6)
    if ColorButton.currentStateIdx == 6:
        for color, notes in noteMap.items():
            clearSelection(notes)
    
    NotePanel.render(screen)

def cycleColor():
    ColorButton.cycleStates()
    colorSync()

WaveButton.onMouseClick(cycleWave)
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
    trimOverlappingNotes()
    deleteZeroDurationNotes()
    
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

def getNoteAt(notes, time, pitch):
    for note in notes:
        if note.pitch == pitch and note.time <= time < note.time + note.duration:
            return note
    return None

def getExtendingNote(notes, time, pitch):
    for note in notes:
        if note.pitch == pitch and (note.time + note.duration - 1) <= time < note.time + note.duration:
            return note
    return False

def clearSelection(notes):
    for note in notes:
        note.unselect()

def handleClick():
    global selectingAnything, draggingSelection, selectionStartPos, dragStartGridPos, drawStartPos, extendingNote, extendStartGridPos, head, waveMap
    if pygame.mouse.get_pos()[1] < 80:
        #console.log("click was outside of the notepanel, we don't care")
        return
    if ModeDropdown.expanded:
        if pygame.rect.Rect(ModeDropdown.x, ModeDropdown.y, ModeDropdown.width, ModeDropdown.height).collidepoint(pygame.mouse.get_pos()):
            #console.log("click was on mode dropdown, we don't care")
            return
    if KeyDropdown.expanded:
        if pygame.rect.Rect(KeyDropdown.x, KeyDropdown.y, KeyDropdown.width, KeyDropdown.height).collidepoint(pygame.mouse.get_pos()):
            #console.log("click was on key dropdown, we don't care")
            return

    mouseTime, mousePitch = custom.convertWorldToGrid(pygame.mouse.get_pos())

    drawStartPos = (mouseTime, mousePitch)
    if mouseTime is None:
        return
    if head:
        head = False
        PlayHead.setHome(mouseTime)
        console.log(f"home: {mouseTime}")
        PlayheadButton.setCurrentState(0)
        PlayheadButton.render(screen)
        NotePanel.render(screen)
        return
    if ColorButton.currentStateIdx == 6:
        return

    currColorName = colorsList[ColorButton.currentStateIdx][0]
    if not (currColorName in noteMap):
        noteMap[currColorName] = []
    notes = noteMap[currColorName]

    if brushType == "brush":
        notes: list[custom.Note] = noteMap[currColorName]
        noteAlrExists = False
        for note in notes:
            if (mousePitch == note.pitch) and (
                (mouseTime >= note.time) and (mouseTime < note.time + note.duration)
                ):
                noteAlrExists = True
        if not noteAlrExists:
            noteMap[currColorName].append(custom.Note({
                "pitch" : mousePitch,
                "time" : mouseTime,
                "duration" : 1,
                "data_fields" : {}
                }))
            sp.playNotes(notes=[mousePitch], waves=waveMap[justColorNames[ColorButton.currentStateIdx]], duration=0.2, volume=0.12)
    elif brushType == "eraser":
        notes: list[custom.Note] = noteMap[currColorName]
        for note in notes:
            if (mousePitch == note.pitch) and (
                (mouseTime >= note.time) and (mouseTime < note.time + note.duration)
                ):
                notes.remove(note)

    clickedNote = getNoteAt(notes, mouseTime, mousePitch)
    shiftHeld = pygame.key.get_pressed()[pygame.K_LSHIFT]
    altHeld = pygame.key.get_pressed()[pygame.K_LALT]
    extendingNote = getExtendingNote(notes, mouseTime, mousePitch)

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
                sp.playNotes(notes=[clickedNote.pitch], waves=waveMap[justColorNames[ColorButton.currentStateIdx]], duration=0.2, volume=0.12)

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
                            "pitch" : note.pitch,
                            "time" : note.time,
                            "duration" : note.duration,
                            "data_fields" : note.dataFields
                        }))

    else:
        # Clicked empty space
        if not shiftHeld:
            clearSelection(notes)

        selectingAnything = False
        draggingSelection = False
        selectionStartPos = pygame.mouse.get_pos()

    NotePanel.render(screen)

def handleDrag(xy):
    global selectingAnything, draggingSelection, drawStartPos, extendingNote
    if pygame.mouse.get_pos()[1] < 80:
        return

    mouseTime, mousePitch = custom.convertWorldToGrid(pygame.mouse.get_pos())
    if mouseTime is None or ColorButton.currentStateIdx == 6:
        return

    currColorName = colorsList[ColorButton.currentStateIdx][0]
    notes = noteMap[currColorName]

    if brushType == "brush":
        notes: list[custom.Note] = noteMap[currColorName]
        maxTimeBefore = float('-inf')
        closestNote = None
        notesInPitch: list[custom.Note] = []
        for note in notes:
            if (mousePitch == note.pitch):
                notesInPitch.append(note)
                closestNote: custom.Note = None
        for note in notesInPitch:
            if (drawStartPos[1] == note.pitch) and (mouseTime >= note.time) and (note.time >= maxTimeBefore):
                closestNote = note

        try: notes.remove(closestNote)
        except: None

        if closestNote != None:
            notes.append(custom.Note({
                "pitch" : closestNote.pitch,
                "time" : closestNote.time,
                "duration" : mouseTime - closestNote.time + 1,
                "data_fields" : closestNote.dataFields
            }))
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
            dx = round(xy[0] / custom.tileWidth)
            dy = -round(xy[1] / custom.tileHeight)
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)

            for note in notes:
                if note.selected and note.extendOriginalDuration:
                    note.duration = note.extendOriginalDuration + dx
                    if note.duration == 0:
                        note.extendOriginalDuration += 1
                    note.duration = note.extendOriginalDuration + dx
        elif draggingSelection:
            # GRID-SNAPPED MOVE
            dx = round(xy[0] / custom.tileWidth)
            dy = -round(xy[1] / custom.tileHeight)

            for note in notes:
                if note.selected and note.dragInitialPosition:
                    note.time = note.dragInitialPosition[0] + dx
                    note.pitch = note.dragInitialPosition[1] + dy
        else:
            # SELECTION BOX
            x0, y0 = selectionStartPos
            x1, y1 = pygame.mouse.get_pos()

            rect = pygame.Rect(
                min(x0, x1),
                min(y0, y1),
                abs(x1 - x0),
                abs(y1 - y0)
            )
            NoteGrid.setSelection(rect)

            for note in notes:
                note_x, note_y = custom.convertGridToWorld(note.time, note.pitch)
                note_rect = pygame.Rect(note_x, note_y, note.duration * custom.tileWidth, custom.tileHeight)

                if rect.colliderect(note_rect): note.select()
                else: note.unselect()

    NotePanel.render(screen)


def handleUnClick():
    if pygame.mouse.get_pos()[1] < 80:
        return
    NoteGrid.selectionRect = None
    preprocess()
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    NotePanel.render(screen)

NoteGrid.onMouseClick(handleClick)
NoteGrid.onMouseDrag(handleDrag)
NoteGrid.onMouseUnClick(handleUnClick)

console.log("Initialized NoteGrid Functionality "+ '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()
console.log("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')

###### MAINLOOP ######

gui_running = False
run = True

root = None
last_update = time.time()

while run:
    while not gui_running:
        time.sleep(0.3)

        if platform == 'mac':
            try:
                pygame.event.pump()
            except:
                pass
        
        pc_data = pcrw.operateProcessCommand(process_command_file)

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

            noteMap = ps["noteMap"]
            waveMap = ps["waveMap"]
            key = ps["key"]
            beatLength = ps['beatLength']
            beatsPerMeasure = ps['beatsPerMeasure']
            if "#" in key:
                keyIndex = NOTES_SHARP.index(key)
                accidentals = "sharps"
            elif "b" in key:
                keyIndex = NOTES_FLAT.index(key)
                accidentals = "flats"
            mode = ps["mode"]
            tpm = ps["tpm"]

            NoteGrid.setModeKey(key = NOTES_SHARP.index(key) if ('#' in key) else NOTES_FLAT.index(key),
                        mode = modesMap[mode])
            KeyDropdown.setCurrentState(keyIndex)
            ModeDropdown.setCurrentState(modes.index(mode))
            BeatLengthTextBox.setText(str(beatLength))
            BeatsPerMeasureTextBox.setText(str(beatsPerMeasure))
            NoteGrid.setIntervals(beatLength, beatsPerMeasure)
            
            # Initialize view position and color channel when opening GUI
            custom.viewRow = 50
            custom.viewCol = 0
            ColorButton.setCurrentState(0)
            NoteGrid.color = 0
            
            # On macOS, show the hidden window; on other platforms, reinitialize
            if platform == 'mac' and pygame.display.get_init():
                # Window was hidden, not destroyed - show it and update
                try:
                    sdl_window = SDLWindow.from_display_module()
                    sdl_window.show()
                    pygame.display.set_caption(f"{title_text} - Symphony v1.1 Beta")
                    screen = pygame.display.get_surface()
                    if screen is None or screen.get_size() != (width, height):
                        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
                except Exception as e:
                    console.warn(f"Error showing hidden window: {e}")
                    # Fallback to full init
                    pygame.display.init()
                    pygame.display.set_caption(f"{title_text} - Symphony v1.1 Beta")
                    pygame.display.set_icon(gameIcon)
                    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
            else:
                # Standard initialization for Windows/Linux or first run
                pygame.display.init()
                pygame.display.set_caption(f"{title_text} - Symphony v1.1 Beta")
                pygame.display.set_icon(gameIcon)
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SHOWN)
            
            PlayHead.setHome(0)
            MasterPanel.render(screen)
            pygame.event.pump()
            pygame.display.flip()

    while gui_running:
        try:
            events.pump()

            saveFrame += 60 * (1 / fps)
            if round(saveFrame) == 20:
                pc_data = pcrw.operateProcessCommand(process_command_file)
            if saveFrame > 1200: # Saves every 20 seconds
                saveFrame = 0
                working_file_path
                worldMessage = fio.dumpToFile(
                                        working_file_path,
                                        working_file_path,
                                        sl.newProgramState(key, mode, tpm, noteMap, waveMap, beatLength, beatsPerMeasure),
                                        autoSave,
                                        title_text,
                                        sessionID)

            NoteGrid.setNoteMap(noteMap)
            try:
                MasterPanel.update(screen)
                for event in events.get():
                    if event.type == pygame.QUIT:
                        gui_running = False
            except pygame.error as e:
                traceback.print_exc()
                console.log('Pygame display was likely quit outside of the main module. Handling and closing properly...\nIf this was unexpected, investigate.')
                gui_running = False
                break

            for event in events.get():
                if event.type == pygame.QUIT:
                    gui_running = False
                    console.warn("Pygame was quit")
                    break
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode((max(event.w, minWidth), max(event.h, minHeight)), pygame.RESIZABLE | pygame.SHOWN)
                    width, height = (max(event.w, minWidth), max(event.h, minHeight))

                    BeatLengthDownButton.setPosition((width - 516, 26))
                    BeatLengthTextBox.setPosition((width - 491, 26))
                    BeatLengthUpButton.setPosition((width - 456, 26))

                    BeatsPerMeasureDownButton.setPosition((width - 412, 26))
                    BeatsPerMeasureTextBox.setPosition((width - 387, 26))
                    BeatsPerMeasureUpButton.setPosition((width - 352, 26))

                    ColorButton.setPosition((width - 308, 26))
                    WaveButton.setPosition((width - 275, 26))
                    KeyDropdown.setPosition((width - 223, 26))
                    ModeDropdown.setPosition((width - 178, 26))
                    QuestionButton.setPosition((width - 54, 26))

                    BeatsPerMeasureControls.setRect((0, 0, width, height))
                    TempoControls.setRect((0, 0, width, height))

                    LeftToolbar.setRect((0, 0, width, height))
                    RightToolbar.setRect((0, 0, width, height))

                    PitchPanel.setRect((0, 80, 80, height - 80))
                    NotePanel.setRect((80, 80, width - 80, height - 80))
                    NoteGrid.width = width
                    NoteGrid.height = height
                    PitchList.height = height
                    NoteGrid.viewBounds()

                    ToolBar.setRect((0, 0, width, 80))
                    GridPanel.setRect((0, 80, width, height - 80))
                    MasterPanel.setRect((0, 0, width, height))

                    MasterPanel.render(screen)
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]:
                        numKeyPressed = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7].index(event.key)
                        draggingNotes = []
                        # Only move notes when dragging to channels 1-6 (indices 0-5), not to universal view (channel 7, index 6)
                        if numKeyPressed < 6 and NoteGrid.mouseInside and pygame.mouse.get_pressed()[0]:
                            draggingNotes = [note for note in noteMap[justColorNames[ColorButton.currentStateIdx]] if note.selected]
                            noteMap[justColorNames[ColorButton.currentStateIdx]] = [note for note in noteMap[justColorNames[ColorButton.currentStateIdx]] if not note.selected]
                        ColorButton.setCurrentState(numKeyPressed)
                        if numKeyPressed < 6 and NoteGrid.mouseInside and pygame.mouse.get_pressed()[0]:
                            try:
                                noteMap[justColorNames[ColorButton.currentStateIdx]].append(*draggingNotes)
                            except Exception as e:
                                console.warn("Color channel to paste into was empty. Setting instead of appending...")
                                noteMap[justColorNames[ColorButton.currentStateIdx]] = draggingNotes
                        colorSync()
                    if event.key in [pygame.K_MINUS, pygame.K_EQUALS]: # zoom out horizontally
                        if pygame.key.get_pressed()[CMD_KEY]:
                            zoomIndex = zoomDimensions.index((custom.tileWidth, custom.tileHeight))
                            if event.key == pygame.K_MINUS:
                                zoomIndex = max(zoomIndex - 1, 0)
                            elif event.key == pygame.K_EQUALS:
                                zoomIndex = min(zoomIndex + 1, len(zoomDimensions) - 1)
                            custom.tileWidth, custom.tileHeight = zoomDimensions[zoomIndex]
                            GridPanel.render(screen)
                    if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE: # Delete all selected notes
                        for colorName in noteMap:
                            noteMap[colorName] = [
                                note for note in noteMap[colorName]
                                if not note.selected
                            ]
                        NotePanel.render(screen)
                    elif event.key == CMD_KEY: # Switch to eraser momentarily
                        brushType = "eraser"
                        BrushButton.setCurrentState(1)
                        BrushButton.render(screen)
                    elif event.key == pygame.K_LSHIFT: # Switch to select permanently
                        brushType = "select"
                        BrushButton.setCurrentState(2)
                        BrushButton.render(screen)
                    elif event.key == pygame.K_SPACE: # Play / pause
                        playPauseToggle()
                    elif event.key == pygame.K_s:
                        if pygame.key.get_pressed()[CMD_KEY]: # if the user presses Ctrl+S (to save)
                            worldMessage = fio.dumpToFile(working_file_path, working_file_path, sl.newProgramState(key, mode, tpm, noteMap, waveMap, beatLength, beatsPerMeasure), autoSave, title_text, sessionID)
                            saveFrame = 0
                elif event.type == pygame.KEYUP:
                    if event.key == CMD_KEY: # Switches away from eraser when Ctrl is let go
                        brushType = "brush"
                        BrushButton.setCurrentState(0)
                        BrushButton.render(screen)
                        for color, colorChannel in noteMap.items():
                            for note in colorChannel:
                                note.selected = False
                        NotePanel.render(screen)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    console.warn("Window unfocused")
                    MasterPanel.render(screen)
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    console.warn("Window focused")
                    MasterPanel.render(screen)

            if gui_running == False:
                break
            clock.tick(fps)
            pygame.display.flip()  # Update the display
        except Exception as e:
            gui_running = False
            traceback.print_exc()
            break

    worldMessage = fio.dumpToFile(working_file_path, working_file_path, sl.newProgramState(key, mode, tpm, noteMap, waveMap, beatLength, beatsPerMeasure), autoSave, title_text, sessionID)
    
    try:
        # on macOS, hiding the window works better than destroying it, i think
        # pygame.display.quit() doesn't properly close the window on macOS
        if platform == 'mac':
            try:
                sdl_window = SDLWindow.from_display_module()
                sdl_window.hide()
                # pump events to let macOS process the hide
                for _ in range(5):
                    pygame.event.pump()
                    time.sleep(0.02)
            except Exception as e:
                console.warn(f"Error hiding window on macOS: {e}")
                # fallback to display quit
                if pygame.display.get_init():
                    pygame.display.quit()
        else:
            # on Windows/Linux, display quit works fine
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
    
    pcrw.gui_is_open = False

# full pygame quit only when daemon is completely done
try:
    pygame.quit()
except:
    pass

console.log("Daemon was quit.")