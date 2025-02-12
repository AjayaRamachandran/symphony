###### IMPORT ######
import pygame
from io import BytesIO
import numpy as np
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

class Note():
    def __init__(self, key:int, time:int, lead:bool):
        self.key = key
        self.time = time
        self.lead = lead
        self.selected = False
    
    def __str__(self):
        return f"Note object with attrs: [key: {self.key}, time: {self.time}, lead: {self.lead}]"

    def draw(self, screen, viewRow, viewColumn):
        headerY = toolbarHeight + ((viewRow - self.key) * innerHeight/floor(viewScaleY))
        headerX = leftColumn + ((self.time - viewColumn - 1) * (width - leftColumn)/floor(viewScaleX))
        if self.lead:
            pygame.draw.rect(screen, (150, 95, 20),
                         (headerX - 1, headerY - 1, (width - leftColumn)/floor(viewScaleX) + 2, innerHeight/floor(viewScaleY) + 2), border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0),
                         (headerX - 1, headerY - 1, (width - leftColumn)/floor(viewScaleX) + 2, innerHeight/floor(viewScaleY) + 2), 1, 3)
        else:
            pygame.draw.rect(screen, (130, 75, 0),
                         (headerX - 1, headerY, (width - leftColumn)/floor(viewScaleX) + 1, innerHeight/floor(viewScaleY)))
            

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

def stamp(text, style, x, y, luminance, justification = "left"):
    #style = heading1
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



###### MAINLOOP ######
running = True

tick = 0
tickInterval = 10

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
noteCount = 128

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
noteLocations = set()
#notes.append(Note(5, 7, True))
currentDraggingKey = 0

toolbarHeight = 80
innerHeight = height - toolbarHeight

mouseTask = False

#wallpaper = pygame.image.load("inner/wallpaper.jpg")

while running:
    #if page == "Editor":
        #screen.blit(wallpaper, ((width - wallpaper.get_rect()[2])/2, 0))
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

            if tintFromMouse((headerX, headerY, (width - leftColumn)/floor(viewScaleX), innerHeight/floor(viewScaleY)))[0] and pygame.mouse.get_pressed()[0] and (pygame.mouse.get_pos()[1] < (height - 50)):
                touchedKey, touchedTime = floor(viewRow - row + 1), floor(column + viewColumn + 1)
                #print(viewColumn)

                ## Brush - unconditionally adds notes to the track
                if type == "brush":
                    if not mouseTask and not (touchedKey, touchedTime) in noteLocations:
                            notes.append(Note(touchedKey, touchedTime, True))
                            noteLocations.add((touchedKey, touchedTime,))
                            currentDraggingKey = touchedKey
                    mouseTask = True
                    if not (currentDraggingKey, touchedTime) in noteLocations:
                        notes.append(Note(currentDraggingKey, touchedTime, False))
                        noteLocations.add((currentDraggingKey, touchedTime))
            
                ## Eraser - unconditionally removes notes from the track
                elif type == "eraser":
                    for note in notes:
                        if (note.key, note.time) == (touchedKey, touchedTime):
                            notes.remove(note)
                        if (note.key, note.time - 1) == (touchedKey, touchedTime) and not note.lead:
                            note.lead = True
                    try: noteLocations.remove((touchedKey, touchedTime))
                    except: None
                    mouseTask = True

                ## Selecter - when statically pressed, selects the note. When dragged moves the note.
                # if there is a previously selected note, it is unselected unless shift is pressed while selecting

                # Dragging moves the note UNLESS the drag is done from the very tail end of the note, in which case
                # all selected notes are lengthened or shortened by the drag amount.
    
    for note in notes:
        note.draw(screen, viewRow, viewColumn)

    for row in range(ceil(viewScaleY) + 1):
        headerX, headerY = 0, row * innerHeight / viewScaleY + toolbarHeight + (viewRow%1 * innerHeight/floor(viewScaleY)) - innerHeight/floor(viewScaleY)
        note = f"{(NOTES_SHARP if mode == 'sharps' else NOTES_FLAT)[floor((viewRow - row) % 12)]} {floor((viewRow - row) / 12)}"
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
            mouseTask = True

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
            mouseTask = True

        

    renderScrollBar()
    renderToolBar()
            
    tick += 1 - (tick == tickInterval - 1) * tickInterval

    if tick == tickInterval - 1:
        None


    dRow *= 0.9
    dCol *= 0.9

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(event.w, 800), max(event.h, 600)), pygame.RESIZABLE)
            width, height = (max(event.w, 800), max(event.h, 600))
            innerHeight = height - toolbarHeight
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                dRow += 0.16
            elif event.key == pygame.K_DOWN:
                dRow -= 0.16
            elif event.key == pygame.K_SPACE:
                playing = not playing
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                dRow += 0.06
            if event.y < 0:
                dRow -= 0.06
            if event.x > 0:
                dCol += 0.06
            if event.x < 0:
                dCol -= 0.06
    viewRow = max(min(viewRow + dRow, 73.01), viewScaleY - 0.01)
    viewColumn = max(min(viewColumn + dCol, (noteCount - viewScaleX)), 0.01)

    if not pygame.mouse.get_pressed()[0]:
        mouseTask = False
    clock.tick(fps)
    pygame.display.flip()  # Update the display

# quit loop
pygame.quit()