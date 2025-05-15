###### IMPORT ######
import pygame
from io import BytesIO
import numpy as np
import simpleaudio as sa
import random
import copy
import cv2
from math import *
import time
import os
import json
import sys
import dill as pkl
from tkinter.filedialog import asksaveasfile, asksaveasfilename

if len(sys.argv) > 3:
    print("Usage: midi_editor.exe <file.mgrid>")
    sys.exit(1)
if len(sys.argv) == 2:
    workingFile = sys.argv[1]
else:
    workingFile = ""

###### PYGAME INITIALIZE ######
pygame.init()
pygame.mixer.quit()

width, height = (1100, 600)
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE, pygame.NOFRAME)
transparentScreen = pygame.Surface((width, height), pygame.SRCALPHA)
pygame.display.set_caption("MIDI Grid v1.0 Beta")
pygame.display.set_icon(pygame.image.load("inner/assets/icon.png"))
clock = pygame.time.Clock()
fps = 60

# imports font styles
TITLE1 = pygame.font.Font("inner/InterVariable.ttf", 60)
HEADING1 = pygame.font.Font("inner/InterVariable.ttf", 24)
SUBHEADING1 = pygame.font.Font("inner/InterVariable.ttf", 14)
BODY = pygame.font.Font("inner/InterVariable.ttf", 14)
SUBSCRIPT1 = pygame.font.Font("inner/InterVariable.ttf", 11)

bytes_io = BytesIO()
directory = "C:/Code/React Projects/Editor/tracks"

###### ASSETS ######
playButton = pygame.image.load("inner/assets/play.png")
pauseButton = pygame.image.load("inner/assets/pause.png")
headButton = pygame.image.load("inner/assets/head.png")
brushButton = pygame.image.load("inner/assets/brush.png")
eraserButton = pygame.image.load("inner/assets/eraser.png")
negaterButton = pygame.image.load("inner/assets/negater.png")

# imports files from the workspaces folder
#files_and_dirs = os.listdir(directory)
#files = [os.path.join(directory, f) for f in files_and_dirs if os.path.isfile(os.path.join(directory, f))]

page = "Editor"
noteMap = {}

###### VARIABLES INITIALIZE ######

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
    "pink" : (168, 49, 94)
}
colorsList = colors.items()
justColors = [n[0] for n in colors.items()]

accidentals = "flats"
head = False
playing = False
type = "brush"
worldMessage = ""

viewRow = 50.01
viewColumn = 0.01
viewScaleY = 16
viewScaleX = 32
dRow = 0
dCol = 0
timeInterval = 4

notes = []
duplicatedNoteMap = {}
currentDraggingKey = 0
initialDraggingTime = 0

toolbarHeight = 80
innerHeight = height - toolbarHeight

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

###### CLASSES ######

class Head():
    '''Class to contain the playhead, which plays the music.'''

    def __init__(self, speed:int, tick:int, home:int = 0):
        self.speed = speed
        self.tick = tick
        self.home = home # home is the time that the head returns to when restarted (default 0)

    def draw(self, screen, viewRow, viewColumn, leftColW, tileW, drawHead=False): # by default, only draws home
        '''Method to draw the playhead.'''
        if drawHead:
            top = [((((time.time() - lastPlayTime) * 60) + self.home) / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [((((time.time() - lastPlayTime) * 60) + self.home) / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (0, 255, 255), top, bottom, 1)

        if self.home != 0:
            top = [(self.home / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [(self.home / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (255, 255, 0), top, bottom, 1)

    def play(self):
        global play_obj
        phases = {}
        finalWave = np.array([], dtype=np.int16)
        for tempTick in range(self.home // ticksPerTile + 1, noteCount):

            playingNotes = []
            for index, note in noteMap.items():
                if note.time == tempTick:
                    playingNotes.append((note.key, note.lead))

            audioChunk, phases = assembleNotes(playingNotes, phases, duration=ticksPerTile/60)
            finalWave = np.concatenate([finalWave, audioChunk])
            
        play_obj = sa.play_buffer(finalWave, 1, 2, 44100)

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
        return f'''Note object with attrs: [key: {self.key}, time: {self.time}, lead: {self.lead}, selected: {self.selected}, originalKey: {self.originalKey}, originalTime: {self.originalTime}]'''

    def setSScoords(self, x, y):
        self.SScoords = [x, y]

    def draw(self, screen, viewRow, viewColumn, noteMap, transparent = False):
        '''Method to draw the note.'''
        global viewScaleX, viewScaleY
        opacity = 130
        tailsDarkness = 20
        def darkenColor(init, amt):
            return [init[n] - (amt * (n!=3)) for n in range(len(init))] # darkens a tuple by a constant n, if init is a quadtuple with opacity, alpha is untouched.
        leadColor = colors[self.color] if not transparent else (*colors[self.color], opacity)
        outlineColor = (255, 255, 255) if not transparent else (0, 0, 0, 0)
        tailColor = darkenColor(leadColor, tailsDarkness)
        black = (0, 0, 0) if not transparent else (0, 0, 0, 0)

        headerY = toolbarHeight + ((viewRow - self.key) * innerHeight/viewScaleY)
        headerX = leftColumn + ((self.time - viewColumn - 1) * (width - leftColumn)/viewScaleX)
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
                if not (self.key, self.time + 1) in noteMap:
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)        
        else:
            pygame.draw.rect(screen, tailColor,
                         (headerX - 1, headerY, (width - leftColumn)/viewScaleX + 1, innerHeight/viewScaleY))
            if (self.key, self.time + 1) in noteMap and noteMap[(self.key, self.time + 1)].lead == False:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
            else:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
        if self.extending:
            pygame.draw.line(screen, (0, 255, 0), # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)

def toNote(note: Note):
    return Note(note.key, note.time, note.lead)

class ProgramState():
    '''Class to contain the entire editor's state, with all relevant fields for opening and saving.'''

    def __init__(self, ticksPerTile, noteMap, key, mode):
        self.ticksPerTile = ticksPerTile
        self.noteMap = noteMap
        self.key = key
        self.mode = mode

    def updateAttributes(self, noteMap, ticksPerTile, key, mode):
        self.noteMap = copy.deepcopy(noteMap)
        self.ticksPerTile = ticksPerTile
        self.key = key
        self.mode = mode
        print(f"Updated ProgramState with key {key} and mode {mode}.")

def toProgramState(state : ProgramState):
    try:
        key = state.key
    except:
        key = "Eb"

    try:
        mode = state.mode
    except:
        mode = "Lydian"

    return ProgramState(state.ticksPerTile, {key : toNote(val) for key, val in state.noteMap.items()}, key, mode)

if workingFile == "":
    ps = ProgramState(10, noteMap, "Eb", "Lydian")
else:
    ps = toProgramState(pkl.load(open(workingFile, "rb")))
noteMap = ps.noteMap
ticksPerTile = ps.ticksPerTile

key = ps.key
keyIndex = NOTES_FLAT.index(key) if accidentals == "flats" else NOTES_SHARP.index(key)
mode = ps.mode
modeIntervals = set(modesIntervals[0][1])

###### FUNCTIONS ######

def dumpToFile(file, directory):
    global worldMessage
    # Get current time in epoch seconds
    epochSeconds = time.time()
    localTime = time.localtime(epochSeconds)
    readableTime = time.strftime('%Y-%m-%d at %H:%M:%S', localTime)

    ps.updateAttributes(noteMap, ticksPerTile, key, mode)
    pkl.dump(ps, file, -1)

    worldMessage = (f"Last Saved {readableTime} to " + directory) if directory != "inner/assets/workingfile.mgrid" else "You have unsaved changes - Please save to a file on your PC."

def inBounds(coords1, coords2, point) -> bool:
    '''returns whether a point is within the bounds of two other points. order is arbitrary.'''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def processImage(imageBytes):
    image = cv2.imdecode(np.frombuffer(imageBytes, np.uint8), cv2.IMREAD_COLOR)
    # Apply a heavy blur to the image
    blurredImage = cv2.GaussianBlur(image, (51, 51), 0)
    
    height, width = blurredImage.shape[:2]
    croppedImage = blurredImage[:, :300]
    
    # Encode the image to a BytesIO object
    _, buffer = cv2.imencode('.jpg', croppedImage)
    imageIO = BytesIO(buffer)
    
    return imageIO

def notesToFreq(notes):
    '''converts a set of notes (as ints from C2) to frequencies'''
    freqs = []
    C2 = 65.41
    ratio = 1.05946309436
    for note in notes:
        noteFreq = C2 * (ratio ** (note - 1))
        freqs.append(noteFreq)
    return freqs

def playNotes(notes, duration=1, volume=0.2, sample_rate=44100):
    try: # needed try catch because sound keeps randomly crashing
        frequencies = notesToFreq(notes)
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        wave = np.zeros_like(t)
        for freq in frequencies:
            wave += np.sign(np.sin(2 * np.pi * freq * t))
        
        wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
        wave *= volume * 0.6
        audio = (wave * 32767).astype(np.int16)
        
        play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    except Exception as e:
        print(e)

def assembleNotes(notes, phases, duration=1, volume=0.2, sample_rate=44100):
    frequencies = notesToFreq([note[0] for note in notes])
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    newPhases = {}
    
    wave = np.zeros_like(t)
    for index, freq in enumerate(frequencies):
        phase = phases.get(freq, 0.0)  # default phase 0 if new
        if notes[index][1]:
            phase += pi
        waveform = np.sign(np.sin(2 * np.pi * freq * t + phase))
        
        # Update phase after this tile
        phaseIncrement = 2 * np.pi * freq * duration
        newPhase = (phase + phaseIncrement) % (2 * np.pi)

        wave += waveform
        newPhases[freq] = newPhase
    
    #wave = wave / np.max(np.abs(wave))
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / ((np.max(np.abs(wave)) ** 2) if (np.max(np.abs(wave)) ** 2)!=0 else 999999))
    wave *= volume * 0.6
    audio = (wave * 32767).astype(np.int16)

    return audio, newPhases

def playNoise(duration=0.08, volume=0.3, sample_rate=44100):
    try: # needed try catch because sound keeps randomly crashing
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        wave = np.zeros_like(t)
        wave += np.random.random(t.shape) * 2 - 1
        
        wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
        wave *= volume * 0.6
        audio = (wave * 32767).astype(np.int16)
        
        play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
        #play_obj.wait_done()
    except Exception as e:
        print(e)

def stamp(text, style, x, y, luminance, justification = "left"):
    text = style.render(text, True, (round(luminance*255), round(luminance*255), round(luminance*255)))
    if justification == "left":
        textRect = (x, y, text.get_rect()[2], text.get_rect()[3])
    elif justification == "right":
        textRect = (x - text.get_rect()[2], y, text.get_rect()[2], text.get_rect()[3])
    else:
        textRect = (x - (text.get_rect()[2]/2), y - (text.get_rect()[3]/2), text.get_rect()[2], text.get_rect()[3])
    screen.blit(text, textRect)

def tintFromMouse(rect):
    '''function that returns (2 things) whether or not the mouse is in the bounding box, as well as a color.'''
    isInside = rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]
    return isInside, ((20, 20, 20) if isInside and pygame.mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

def reevaluateLeads():
    for note in noteMap.items():
        if not ((note[0][0], note[0][1] - 1) in noteMap):
            noteMap[note[0]].lead = True

###### MAINLOOP ######
running = True
playHead = Head(0, 1, 0)

while running:
    saveFrame += 1
    if saveFrame == 1200:
        saveFrame = 0

        myPath = open(workingFile if workingFile != "" else "inner/assets/workingfile.mgrid", "wb")

        dumpToFile(myPath, workingFile if workingFile != "" else "inner/assets/workingfile.mgrid")
        myPath.close()

    screen.fill((0, 0, 0))
    transparentScreen.fill((0, 0, 0, 0))

    leftColumn = 60
    
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
            if tintFromMouse((headerX, headerY, (width - leftColumn)/viewScaleX, innerHeight/viewScaleY))[0] and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)):
                touchedKey, touchedTime = floor(viewRow - row + 1), floor(column + viewColumn + 1)
                if not mouseTask:
                    mouseDownTime = time.time() # sets mouse start down time

                ## Head - means that selecting time stamp
                if head:
                    if not mouseTask:
                        playHead.home = (touchedTime - 1) * ticksPerTile
                        mouseTask = True
                ## Brush - unconditionally adds notes to the track
                elif type == "brush":
                    if not mouseTask and not (touchedKey, touchedTime) in noteMap:
                        playNotes([touchedKey], duration=0.25)
                        noteMap[(touchedKey, touchedTime)] = Note(touchedKey, touchedTime, True, color=random.choice(justColors))
                        currentDraggingKey = touchedKey
                        initialDraggingTime = touchedTime
                    reevaluateLeads()
                    mouseTask = True
                    if (not (currentDraggingKey, touchedTime) in noteMap) and touchedTime > initialDraggingTime:
                        noteMap[(currentDraggingKey, touchedTime)] = Note(currentDraggingKey, touchedTime, False, color=random.choice(justColors))
            
                ## Eraser - unconditionally removes notes from the track
                elif type == "eraser":
                    toDelete = []
                    for note in noteMap.items():
                        if (note[1].key, note[1].time) == (touchedKey, touchedTime):
                            toDelete.append((touchedKey, touchedTime))
                        if (note[1].key, note[1].time - 1) == (touchedKey, touchedTime) and not note[1].lead:
                            note[1].lead = True
                    for itemToDelete in toDelete:
                        del noteMap[itemToDelete]
                    mouseTask = True

                ## Selecter - when statically pressed, selects the note. When dragged moves the note.
                # if there is a previously selected note, it is unselected unless shift is pressed while selecting

                # Dragging moves the note UNLESS the drag is done from the very tail end of the note, in which case
                # all selected notes are lengthened or shortened by the drag amount.
                
                elif type == "select":
                    if not mouseTask: # mouse was just clicked
                        for note in noteMap.items():
                            noteMap[note[0]].originalKey = noteMap[note[0]].key
                            noteMap[note[0]].originalTime = noteMap[note[0]].time
                        mouseHoldStart = pygame.mouse.get_pos()
                        mouseCellStart = (touchedKey, touchedTime)
                        mouseTask = True
                    else:
                        #print(timeOffset, keyOffset)
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
                                    if mouseTask and numSelected and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        #print("dragging")
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
                                                            duplicatedNoteMap[note[0]].originalTime + timeOffset), note[1]))
                                        for delete in delQ:
                                            del duplicatedNoteMap[delete]
                                        for add in addQ:
                                            duplicatedNoteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if oldKeyOffset != keyOffset and consistentKey != -1 and consistentKey != 0:
                                            playNotes([addQ[0][0][0]], duration=0.07)
                                else:
                                    numSelected = False
                                    for note in noteMap.items():
                                        if note[1].selected:
                                            numSelected = True
                                    if mouseTask and numSelected and dist(pygame.mouse.get_pos(), mouseHoldStart) > 10:
                                        #print("dragging")
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
                                                            noteMap[note[0]].originalTime + timeOffset), note[1]))
                                        for delete in delQ:
                                            del noteMap[delete]
                                        for add in addQ:
                                            noteMap[add[0]] = add[1]
                                        if refreshQ:
                                            reevaluateLeads()
                                        if oldKeyOffset != keyOffset and consistentKey != -1 and consistentKey != 0:
                                            playNotes([addQ[0][0][0]], duration=0.07)
                            
                mouseWOTask = False
                mouseTask = True
    for note in noteMap.items():
        if note[1].key > viewRow - viewScaleY and note[1].key < viewRow + 1:
            if note[1].time > viewColumn and note[1].time < viewColumn + viewScaleX + 1:
                #print(f"Note Key : {note[1].key}, viewRow : {viewRow}, Note Time : {note[1].time}, viewColumn : {viewColumn}, viewScaleX : {viewScaleX}, viewScaleY : {viewScaleY}")
                note[1].draw(screen, viewRow, viewColumn, noteMap)
    
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

        if tintFromMouse((0, headerY, leftColumn, innerHeight/viewScaleY))[0] and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)) and not mouseTask:
            # mouse is clicking the note labels
            mouseTask = True
            playNotes([floor(viewRow - row + 1)], duration=0.25)

    def renderScrollBar():
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
        global accidentals, mouseTask, playing, head, type, key, keyIndex, mode, modeIntervals, lastPlayTime
        pygame.draw.rect(screen, (43, 43, 43), (0, 0, width, toolbarHeight))
        pygame.draw.line(screen, (0, 0, 0), (0, toolbarHeight), (width, toolbarHeight))
        pygame.draw.line(screen, (30, 30, 30), (0, toolbarHeight - 1), (width, toolbarHeight - 1))
        pygame.draw.line(screen, (49, 49, 49), (0, toolbarHeight - 2), (width, toolbarHeight - 2))
        pygame.draw.line(screen, (45, 45, 45), (0, toolbarHeight - 3), (width, toolbarHeight - 3))

        ### TRACK TITLE BAR
        pygame.draw.rect(screen, (0, 0, 0), (width/2 - 100, toolbarHeight/2 - 14, 200, 28), 1, 3)
        stamp("My Track 1", SUBHEADING1, width/2, 40, 0.4, "center")

        ### PLAY/PAUSE BUTTON
        xPos = 33
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[1], (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        screen.blit((pauseButton if playing else playButton), (xPos + 20, 32))
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            playing = not playing
            if playing:
                playHead.play()
                lastPlayTime = time.time()
            else:
                play_obj.stop()
            mouseTask = True
            playHead.tick = playHead.home

        ### ACCIDENTALS BUTTON
        xPos = 120
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[1], (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        stamp(accidentals, SUBHEADING1, xPos + 30, 40, 0.4, "center")
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
            key = (NOTES_FLAT if accidentals == "sharps" else NOTES_SHARP)[keyIndex] # swaps the style of the 
            accidentals = ("sharps" if accidentals == "flats" else "flats")
            mouseTask = True
        
        ### PLAYHEAD BUTTON
        xPos = 207
        pygame.draw.rect(screen, (30, 30, 30) if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] or head else (35, 35, 35), (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        screen.blit((headButton if playing else headButton), (xPos + 20, 32))
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            head = not head
            mouseTask = True

        ### KEY BUTTON
        xPos = width - 33 - 60 - 87 - 80
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 40, 28))[1], (xPos, toolbarHeight/2 - 14, 40, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 40, 28), 1, 3)
        stamp(key, SUBHEADING1, xPos + 20, 40, 0.4, "center")
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 40, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
            key = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT)[keyIndex + 1 if keyIndex != 11 else 0]
            keyIndex = keyIndex + 1 if keyIndex != 11 else 0
            mouseTask = True

        ### MODE BUTTON
        xPos = width - 33 - 60 - 127
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 100, 28))[1], (xPos, toolbarHeight/2 - 14, 100, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 100, 28), 1, 3)
        stamp(mode, SUBHEADING1, xPos + 50, 40, 0.4, "center")
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 100, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            modeIndex = next(i for i, (x, _) in enumerate(modesIntervals) if x == mode)
            mode = modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][0]
            modeIntervals = set(modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][1])
            mouseTask = True

        ### BRUSH/ERASER/NEGATER BUTTON
        xPos = width - 33 - 60
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[1], (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        if type == "select":
            stamp("select", SUBHEADING1, xPos + 30, 40, 0.4, "center")
        else:
            screen.blit((brushButton if type == "brush" else eraserButton), (xPos + 20, 32))
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            if type == "brush":
                type = "eraser"
            elif type == "eraser":
                type = "select"
            else:
                type = "brush"
                for note in noteMap.items():
                    note[1].selected = False
            mouseTask = True

    renderScrollBar()
    renderToolBar()
            
    tick += 1 - (tick == tickInterval - 1) * tickInterval

    if tick == tickInterval - 1:
        None

    def selectConnected(key, time):
        '''function to take in a key and time and select all connected notes, and return whether a note exists at that key and time'''
        noteExists = False
        deviation = 0
        while (key, time + deviation) in noteMap:
            noteExists = True
            noteMap[(key, time + deviation)].selected = True
            if noteMap[(key, time + deviation)].lead == True:
                noteMap[(key, time + deviation)].selected = True
                break
            deviation -= 1
        deviation = 1
        while (key, time + deviation) in noteMap:
            noteExists = True
            if noteMap[(key, time + deviation)].lead == True:
                break
            noteMap[(key, time + deviation)].selected = True
            deviation += 1
        return noteExists

    if not pygame.mouse.get_pressed()[0] and not mouseWOTask:
        #print("Unclicked")
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        if head:
            head = False
        try:
            mouseCellStart
        except NameError:
            #print("mouseCellStart not defined -- a selection was not initialized.")
            None
        else:
            if (mouseHoldStart != pygame.mouse.get_pos()) and type == "select":
                #print("Drag Selected")
                for note in noteMap.items():
                    if inBounds(mouseHoldStart, pygame.mouse.get_pos(), note[1].SScoords):
                        note[1].selected = True
                        selectConnected(note[0][0], note[0][1])
        if (time.time() - mouseDownTime) < 0.2 and type == "select":
            timeOffset = 0
            keyOffset = 0
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # if shift is not held, unselect all elements.
                for note in noteMap.items():
                    note[1].selected = False
            
            # selected from mouse selection, opposite of dragging, only happens once mouse is lifted.
            noteExists = selectConnected(touchedKey, touchedTime)

            if noteExists:
                playNotes([touchedKey], duration=0.25)
            mouseTask = True
        mouseWOTask = True

    if worldMessage != "":
        worldMessageRender = stamp(worldMessage, SUBSCRIPT1, width/2, 8, 0.5, "center")

    dRow *= 0.9
    dCol *= 0.9

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            print("Pygame was quit")
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(event.w, 800), max(event.h, 600)), pygame.RESIZABLE)
            width, height = (max(event.w, 800), max(event.h, 600))
            transparentScreen = pygame.Surface((width, height), pygame.SRCALPHA)

            viewScaleX = (width - leftColumn) / ((1100 - leftColumn)/32) # keeps the box consistent width even when the window is resized
            viewScaleY = (height - toolbarHeight) / ((600 - toolbarHeight)/16) # keeps the box consistent height even when the window is resized
            innerHeight = height - toolbarHeight

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                dRow += 0.16
            elif event.key == pygame.K_DOWN:
                dRow -= 0.16
            elif event.key == pygame.K_RIGHT:
                dCol += 0.16
            elif event.key == pygame.K_LEFT:
                dCol -= 0.16
            elif event.key == pygame.K_LCTRL:
                type = "eraser"
            elif event.key == pygame.K_LSHIFT:
                type = "select"
            elif event.key == pygame.K_SPACE:
                playing = not playing
                if playing:
                    playHead.play()
                    lastPlayTime = time.time()
                else:
                    play_obj.stop()
                playHead.tick = playHead.home
            elif event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
                delQ = []
                for index, note in noteMap.items():
                    if note.selected:
                        delQ.append(index)
                for q in delQ:
                    del noteMap[q]
            elif event.key == pygame.K_s:
                if pygame.key.get_pressed()[pygame.K_LCTRL]: # if the user presses Ctrl+S (to save)
                    if workingFile == "": # file dialog to show up if the user's workspace is not attached to a file
                        filename = asksaveasfile(initialfile = 'Untitled.mgrid', mode='wb',defaultextension=".mgrid", filetypes=[("Musical Composition Grid File","*.mgrid")])
                        if filename != None:
                            filestring = filename.name
                            myPath = open("inner/assets/workingfile.mgrid", "wb")
                            dumpToFile(myPath, directory=filestring)
                            myPath = open("inner/assets/workingfile.mgrid", "rb")

                            pathBytes = bytearray(myPath.read())
                            filename.write(pathBytes)
                            filename.close()
                        else:
                            myPath = open("inner/assets/workingfile.mgrid", "wb")
                            dumpToFile(myPath, "inner/assets/workingfile.mgrid")
                    else: # save to workspace file
                        myPath = open(workingFile, "wb")
                        dumpToFile(myPath, workingFile)
                    saveFrame = 0
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LCTRL:
                type = "brush"
                for note in noteMap.items():
                    note[1].selected = False
            if event.key == pygame.K_LALT:
                for note in duplicatedNoteMap.items():
                    noteMap[note[0]] = copy.deepcopy(note[1])
                duplicatedNoteMap.clear()
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                dRow += 0.06
            if event.y < 0:
                dRow -= 0.06
            if event.x > 0:
                dCol += 0.06
            if event.x < 0:
                dCol -= 0.06
    viewRow = max(min(viewRow + dRow, noteRange + 0.01), viewScaleY - 0.01)
    viewColumn = max(min(viewColumn + dCol, (noteCount - viewScaleX)), 0.01)

    oldKeyOffset = keyOffset
    drawSelectBox = False

    screen.blit(transparentScreen, transparentScreen.get_rect())

    if not pygame.mouse.get_pressed()[0]:
        mouseTask = False
    clock.tick(fps)
    pygame.display.flip()  # Update the display


if workingFile == "": # file dialog to show up if the user has unsaved changes (they have not attached the workspace to a file)
    filename = asksaveasfile(initialfile = 'Untitled.mgrid', mode='wb',defaultextension=".mgrid", filetypes=[("Musical Composition Grid File","*.mgrid")])
    if filename != None:
        myPath = open("inner/assets/workingfile.mgrid", "wb")

        dumpToFile(myPath, directory="inner/assets/workingfile.mgrid")
        myPath = open("inner/assets/workingfile.mgrid", "rb")

        pathBytes = bytearray(myPath.read())
        filename.write(pathBytes)
        filename.close()
else: # save all changes upon closing that have happened since the last autosave
    myPath = open(workingFile, "wb")
    dumpToFile(myPath, directory=workingFile)
    
# quit loop
pygame.quit()