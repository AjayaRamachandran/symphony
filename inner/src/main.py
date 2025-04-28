###### IMPORT ######
import pygame
from io import BytesIO
import numpy as np
import simpleaudio as sa
import random
import cv2
from math import *
import time
import os
import json

###### INITIALIZE ######
pygame.init()

width, height = (1100, 600)
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE, pygame.NOFRAME)
pygame.display.set_caption("MIDI Grid v1.0 Beta")
pygame.display.set_icon(pygame.image.load("inner/assets/icon.png"))
clock = pygame.time.Clock()
fps = 60

# imports font styles
TITLE1 = pygame.font.Font("inner/InterVariable.ttf", 60)
HEADING1 = pygame.font.Font("inner/InterVariable.ttf", 24)
SUBHEADING1 = pygame.font.Font("inner/InterVariable.ttf", 14)
BODY = pygame.font.Font("inner/InterVariable.ttf", 14)
SUBSCRIPT1 = pygame.font.Font("inner/InterVariable.ttf", 12)

bytes_io = BytesIO()
directory = "C:/Code/React Projects/Editor/tracks"

### ASSETS ###
playButton = pygame.image.load("inner/assets/play.png")
pauseButton = pygame.image.load("inner/assets/pause.png")
headButton = pygame.image.load("inner/assets/head.png")
brushButton = pygame.image.load("inner/assets/brush.png")
eraserButton = pygame.image.load("inner/assets/eraser.png")
negaterButton = pygame.image.load("inner/assets/negater.png")

# imports files from the workspaces folder
files_and_dirs = os.listdir(directory)
files = [os.path.join(directory, f) for f in files_and_dirs if os.path.isfile(os.path.join(directory, f))]

page = "Editor"

###### CLASSES ######

class Head():
    def __init__(self, speed:int, tick:int, home:int = 0):
        self.speed = speed
        self.tick = tick
        self.home = home # home is the time that the head returns to when restarted (default 0)

    def draw(self, screen, viewRow, viewColumn, leftColW, tileW):
        top = [(self.tick / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
        bottom = [(self.tick / ticksPerTile * tileW) - (viewColumn * tileW) + leftColW, height]

        pygame.draw.line(screen, (0, 255, 255), top, bottom, 1)

    def play(self):
        global play_obj
        phases = {}
        tempTick = 0
        finalWave = np.array([], dtype=np.int16)
        for tempTick in range(noteCount):
            #print(f"note played {random.randint(0, 100000)}")
            playingNotes = []
            for index, note in noteMap.items():
                if note.time == tempTick:
                    playingNotes.append(note.key)
            #if len(playingNotes) > 0:
                #print(f"Playing notes {playingNotes}")
                
            #finalWave = np.concatenate([finalWave,
                                        #assembleNotes(playingNotes, duration=ticksPerTile/fps)])
            audioChunk, phases = assembleNotes(playingNotes, phases, duration=ticksPerTile/fps)
            finalWave = np.concatenate([finalWave, audioChunk])
            
        play_obj = sa.play_buffer(finalWave, 1, 2, 44100)

class Note():
    def __init__(self, key:int, time:int, lead:bool):
        self.key = key
        self.time = time
        self.lead = lead
        self.originalKey = key
        self.originalTime = time
        self.selected = False
        self.extending = False
    
    def __str__(self):
        return f'''Note object with attrs: [key: {self.key}, time: {self.time}, lead: {self.lead}, selected: {self.selected}, originalKey: {self.originalKey}, originalTime: {self.originalTime}]'''

    def draw(self, screen, viewRow, viewColumn):
        headerY = toolbarHeight + ((viewRow - self.key) * innerHeight/floor(viewScaleY))
        headerX = leftColumn + ((self.time - viewColumn - 1) * (width - leftColumn)/floor(viewScaleX))
        if self.lead:
            pygame.draw.rect(screen, (150, 95, 20),
                         (headerX - 1, headerY - 1, (width - leftColumn)/floor(viewScaleX) + 2, innerHeight/floor(viewScaleY) + 2), border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0),
                         (headerX - 1, headerY - 1, (width - leftColumn)/floor(viewScaleX) + 2, innerHeight/floor(viewScaleY) + 2), 1, 3)
            if self.selected:
                pygame.draw.line(screen, (255, 255, 255), # top edge
                         (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY - 1), 2)
                pygame.draw.line(screen, (255, 255, 255), # left edge
                         (headerX - 1, headerY - 1), (headerX - 1, headerY + innerHeight/floor(viewScaleY) - 1), 2)
                pygame.draw.line(screen, (255, 255, 255), # bottom edge
                         (headerX - 1, headerY + innerHeight/floor(viewScaleY) - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY + innerHeight/floor(viewScaleY) - 1), 2)
                if not (self.key, self.time + 1) in noteMap:
                    pygame.draw.line(screen, (255, 255, 255), # right edge
                            (headerX + (width - leftColumn)/floor(viewScaleX), headerY + 1), (headerX + (width - leftColumn)/floor(viewScaleX), headerY + innerHeight/floor(viewScaleY) - 1), 2)        
        else:
            pygame.draw.rect(screen, (130, 75, 0),
                         (headerX - 1, headerY, (width - leftColumn)/floor(viewScaleX) + 1, innerHeight/floor(viewScaleY)))
            if (self.key, self.time + 1) in noteMap and noteMap[(self.key, self.time + 1)].lead == False:
                if self.selected:
                    pygame.draw.line(screen, (255, 255, 255), # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY - 1), 2)
                    pygame.draw.line(screen, (255, 255, 255), # bottom edge
                            (headerX - 1, headerY + innerHeight/floor(viewScaleY) - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY + innerHeight/floor(viewScaleY) - 1), 2)
            else:
                if self.selected:
                    pygame.draw.line(screen, (255, 255, 255), # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY - 1), 2)
                    pygame.draw.line(screen, (255, 255, 255), # right edge
                            (headerX + (width - leftColumn)/floor(viewScaleX), headerY + 1), (headerX + (width - leftColumn)/floor(viewScaleX), headerY + innerHeight/floor(viewScaleY) - 1), 2)
                    pygame.draw.line(screen, (255, 255, 255), # bottom edge
                            (headerX - 1, headerY + innerHeight/floor(viewScaleY) - 1), (headerX + (width - leftColumn)/floor(viewScaleX) + 1, headerY + innerHeight/floor(viewScaleY) - 1), 2)
        if self.extending:
            pygame.draw.line(screen, (0, 255, 0), # right edge
                            (headerX + (width - leftColumn)/floor(viewScaleX), headerY + 1), (headerX + (width - leftColumn)/floor(viewScaleX), headerY + innerHeight/floor(viewScaleY) - 1), 2)
                    

###### FUNCTIONS ######

def process_image(image_bytes):
    # Load the image from the BytesIO object
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    
    # Apply a heavy blur to the image
    blurred_image = cv2.GaussianBlur(image, (51, 51), 0)
    
    height, width = blurred_image.shape[:2]
    cropped_image = blurred_image[:, :300]
    
    # Encode the image to a BytesIO object
    _, buffer = cv2.imencode('.jpg', cropped_image)
    image_io = BytesIO(buffer)
    
    return image_io

def notesToFreq(notes):
    freqs = []
    C2 = 65.41
    ratio = 1.05946309436
    for note in notes:
        noteFreq = C2 * (ratio ** (note - 1))
        freqs.append(noteFreq)
    return freqs

def playNotes(notes, duration=1, volume=0.2, sample_rate=44100):
    frequencies = notesToFreq(notes)
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    wave = np.zeros_like(t)
    for freq in frequencies:
        wave += np.sign(np.sin(2 * np.pi * freq * t))
    
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
    wave *= volume
    audio = (wave * 32767).astype(np.int16)
    
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)

def assembleNotes(notes, phases, duration=1, volume=0.2, sample_rate=44100):
    frequencies = notesToFreq(notes)
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    newPhases = {}
    
    wave = np.zeros_like(t)
    for freq in frequencies:
        phase = phases.get(freq, 0.0)  # default phase 0 if new
        waveform = np.sign(np.sin(2 * np.pi * freq * t + phase))
        
        # Update phase after this tile
        phaseIncrement = 2 * np.pi * freq * duration
        newPhase = (phase + phaseIncrement) % (2 * np.pi)

        wave += waveform
        newPhases[freq] = newPhase
    
    #wave = wave / np.max(np.abs(wave))
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
    wave *= volume
    audio = (wave * 32767).astype(np.int16)

    return audio, newPhases

def playNoise(duration=0.08, volume=0.3, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    wave = np.zeros_like(t)
    wave += np.random.random(t.shape) * 2 - 1
    
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
    wave *= volume
    audio = (wave * 32767).astype(np.int16)
    
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    #play_obj.wait_done()

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

tick = 0
tickInterval = 10

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
noteCount = 128
noteRange = 60

mode = "flats"
head = False
playing = False
type = "brush"

viewRow = 50.01
viewColumn = 0.01
viewScaleY = 16
viewScaleX = 32
dRow = 0
dCol = 0

notes = []
noteMap = {}
currentDraggingKey = 0
initialDraggingTime = 0
ticksPerTile = 10

toolbarHeight = 80
innerHeight = height - toolbarHeight

mouseTask = False
mouseDownTime = time.time()
mouseWOTask = True
mouseHoldStart = []

playHead = Head(0, 1, 0)

while running:
    screen.fill((0, 0, 0))

    leftColumn = 60
    
    for row in range(ceil(viewScaleY) + 1):
        headerY = row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/floor(viewScaleY)) - innerHeight/floor(viewScaleY)
        headerX = leftColumn - (viewColumn%1 * (width - leftColumn)/floor(viewScaleX)) - (width - leftColumn)/floor(viewScaleX)
        for column in range(ceil(viewScaleX) + 2):
            cm = (floor((column+viewColumn)%4) == 0) * 8
            pygame.draw.rect(screen, ((32 + cm, 32 + cm, 32 + cm) if floor((row - viewRow)%2) == 0 else (40 + cm, 40 + cm, 40 + cm)),
                         (headerX, headerY, (width - leftColumn)/floor(viewScaleX), innerHeight/floor(viewScaleY)), border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0),
                         (headerX, headerY, (width - leftColumn)/floor(viewScaleX), innerHeight/floor(viewScaleY)), 1, 3)
            headerX += (width - leftColumn)/floor(viewScaleX)

            ##### BRUSH CONTROLS #####
            if tintFromMouse((headerX, headerY, (width - leftColumn)/floor(viewScaleX), innerHeight/floor(viewScaleY)))[0] and (pygame.mouse.get_pressed()[0]) and (toolbarHeight < pygame.mouse.get_pos()[1] < (height - 50)):
                touchedKey, touchedTime = floor(viewRow - row + 1), floor(column + viewColumn + 1)
                if not mouseTask:
                    mouseDownTime = time.time() # sets mouse start down time
                ## Brush - unconditionally adds notes to the track
                if type == "brush":
                    if not mouseTask and not (touchedKey, touchedTime) in noteMap:
                        playNotes([touchedKey], duration=1)
                        noteMap[(touchedKey, touchedTime)] = Note(touchedKey, touchedTime, True)
                        currentDraggingKey = touchedKey
                        initialDraggingTime = touchedTime
                    reevaluateLeads()
                    mouseTask = True
                    if (not (currentDraggingKey, touchedTime) in noteMap) and touchedTime > initialDraggingTime:
                        noteMap[(currentDraggingKey, touchedTime)] = Note(currentDraggingKey, touchedTime, False)
            
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
                    if not mouseTask:
                        for note in noteMap.items():
                            noteMap[note[0]].originalKey = noteMap[note[0]].key
                            noteMap[note[0]].originalTime = noteMap[note[0]].time
                        mouseHoldStart = pygame.mouse.get_pos()
                        mouseCellStart = (touchedKey, touchedTime)
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
                            for note in noteMap.items():
                                if noteMap[note[0]].selected:
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

                mouseWOTask = False
                mouseTask = True
    for note in noteMap.items():
        #### REMEMBER TO ADD OPTIMIZATION TO ONLY DRAW SCREEN SPACE NOTES - DONE!
        if note[1].key > viewRow - viewScaleY and note[1].key < viewRow + 1:
            if note[1].time > viewColumn and note[1].time < viewColumn + viewScaleX + 1:
                #print(f"Note Key : {note[1].key}, viewRow : {viewRow}, Note Time : {note[1].time}, viewColumn : {viewColumn}, viewScaleX : {viewScaleX}, viewScaleY : {viewScaleY}")
                note[1].draw(screen, viewRow, viewColumn)

    for row in range(ceil(viewScaleY) + 1):
        headerX, headerY = 0, row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/floor(viewScaleY)) - innerHeight/floor(viewScaleY)
        note = f"{(NOTES_SHARP if mode == 'sharps' else NOTES_FLAT)[floor((viewRow - row) % 12)]} {floor((viewRow - row) / 12) + 2}"
        pygame.draw.rect(screen, ((43, 43, 43) if floor((row - viewRow)%2) == 0 else (51, 51, 51)),
                         (headerX, headerY, leftColumn, innerHeight/floor(viewScaleY)), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0),
                         (headerX, headerY, leftColumn, innerHeight/floor(viewScaleY)), 1, 3)
        stamp(note, SUBHEADING1, headerX + 5, headerY + 5, 0.4)

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
        global mode, mouseTask, playing, head, type
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
            else:
                play_obj.stop()
            mouseTask = True
            playHead.tick = playHead.home

        ### ACCIDENTALS BUTTON
        xPos = 120
        pygame.draw.rect(screen, tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[1], (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        stamp(mode, SUBHEADING1, xPos + 30, 40, 0.4, "center")
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            mode = ("sharps" if mode == "flats" else "flats")
            mouseTask = True
        
        ### PLAYHEAD BUTTON
        xPos = 207
        pygame.draw.rect(screen, (30, 30, 30) if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] or head else (35, 35, 35), (xPos, toolbarHeight/2 - 14, 60, 28), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (xPos, toolbarHeight/2 - 14, 60, 28), 1, 3)
        screen.blit((headButton if playing else headButton), (xPos + 20, 32))
        if tintFromMouse((xPos, toolbarHeight/2 - 14, 60, 28))[0] and pygame.mouse.get_pressed()[0] and not mouseTask:
            head = not head
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

    # functionality to move playhead and draw it when it is moving
    if playing:
        playHead.tick += 1
        playHead.draw(screen, viewRow, viewColumn, leftColumn, (width - leftColumn)/floor(viewScaleX))
            
    tick += 1 - (tick == tickInterval - 1) * tickInterval

    if tick == tickInterval - 1:
        None

    if not pygame.mouse.get_pressed()[0] and not mouseWOTask:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        if (time.time() - mouseDownTime) < 0.2 and type == "select":
            if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # if shift is not held, unselect all elements.
                for note in noteMap.items():
                    note[1].selected = False
            # selected from mouse selection, opposite of dragging, only happens once mouse is lifted.
            deviation = 0
            while (touchedKey, touchedTime + deviation) in noteMap:
                noteMap[(touchedKey, touchedTime + deviation)].selected = True
                if noteMap[(touchedKey, touchedTime + deviation)].lead == True:
                    noteMap[(touchedKey, touchedTime + deviation)].selected = True
                    break
                deviation -= 1
            deviation = 1
            while (touchedKey, touchedTime + deviation) in noteMap:
                if noteMap[(touchedKey, touchedTime + deviation)].lead == True:
                    break
                noteMap[(touchedKey, touchedTime + deviation)].selected = True
                deviation += 1
            #for note in noteMap.items():
                #noteMap[note[0]].originalKey = noteMap[note[0]].key
                #noteMap[note[0]].originalTime = noteMap[note[0]].time
            mouseTask = True
        mouseWOTask = True

    dRow *= 0.9
    dCol *= 0.9

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(event.w, 800), max(event.h, 600)), pygame.RESIZABLE)
            width, height = (max(event.w, 800), max(event.h, 600))
            viewScaleX = floor(width / 34)
            viewScaleY = floor(height / 37)
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
            elif event.key == pygame.K_SPACE:
                playing = not playing
                if playing:
                    playHead.play()
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
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LCTRL:
                type = "brush"
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

    if not pygame.mouse.get_pressed()[0]:
        mouseTask = False
    clock.tick(fps)
    pygame.display.flip()  # Update the display

# quit loop
pygame.quit()