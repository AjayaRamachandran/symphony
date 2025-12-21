# gui/custom.py
# module for holding data for custom gui elements, bespoke interfaces.
###### IMPORT ######

import pygame
import time
import numpy as np
import cv2
from io import BytesIO
import copy
from math import *

###### INTERNAL MODULES ######

from console_controls.console import *
import gui.element as gui
import gui.frame as frame
import utils.sound_processing as sp
import events

###### INITIALIZE ######

viewRow = 50
viewCol = 0
tileWidth = 30
tileHeight = 30


colors = [(235, 144, 74, 255),
        (184, 125, 227, 255),
        (108, 207, 198, 255),
        (154, 222, 138, 255),
        (106, 122, 214, 255),
        (214, 106, 155, 255)]

def getColorStates(width, height, source_path):
    rainbowImage = pygame.image.load(f"{source_path}/assets/rainbow.png")
    outputs = []
    for idx, color in enumerate(colors):
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(surf, color, (0, 0, width, height), border_radius=3)
        gui.stamp(surf, str(idx + 1), gui.SUBHEADING1, width/2, height/2, gui.BG_COLOR, justification='center')
        outputs.append(surf)
    
    gui.stamp(rainbowImage, '7', gui.SUBHEADING1, rainbowImage.get_width()/2, rainbowImage.get_height()/2, gui.BG_COLOR, justification='center')
    outputs.append(rainbowImage)
    return outputs

def convertGridToWorld(time, pitch, tileSize: tuple[int | float] = None, view: tuple[int | float] = None):
    '''
    fields:
        time (number) - the time of the grid coordinate
        pitch (number) - the pitch of the grid coordinate
        tileSize (tuple[number]) - the coordinate dimensions of the grid tiles
        view (tuple[number]) - the coordinates of the view camera in relation to the GRID
    outputs: tuple[number]
    
    Converts the Grid coordinates to Screen (world) coordinates.
    '''
    global tileWidth, tileHeight, viewRow, viewCol

    _tileWidth, _tileHeight = tileSize if tileSize is not None else (tileWidth, tileHeight)
    _viewCol, _viewRow = view if view is not None else (viewCol, viewRow)

    return [(time - viewCol) * _tileWidth + 80, ((112 - viewRow) - pitch) * _tileHeight + 80]

def convertWorldToGrid(mousePos, tileSize: tuple[int | float] = None, view: tuple[int | float] = None):
    '''
    fields:
        mousePos (tuple[number]) - the mouse coordinates in world/screen space
        tileSize (tuple[number]) - the coordinate dimensions of the grid tiles
        view (tuple[number]) - the coordinates of the view camera in relation to the GRID
    outputs: tuple[number]
    
    Converts Screen (world) coordinates to Grid coordinates.
    '''
    global tileWidth, tileHeight, viewRow, viewCol

    mouseX, mouseY = mousePos
    if mouseX < 80 or mouseY < 80:
        return None, None
    
    _tileWidth, _tileHeight = tileSize if tileSize is not None else (tileWidth, tileHeight)
    _viewCol, _viewRow = view if view is not None else (viewCol, viewRow)

    time = (mouseX - 80) / _tileWidth + _viewCol
    pitch = (112 - _viewRow) - (mouseY - 80) / _tileHeight

    return floor(time), ceil(pitch)


###### CLASSES ######

class PitchList(gui.Interactive):
    '''
    Class that manages the Pitch list on the left side of the screen, and how it plays back notes.
    '''
    def __init__(self, pos, width, height, notes):
        super().__init__(pos, width, height)
        self.notes = notes

        self.onMouseEnter(lambda: (setattr(self, 'redraw', True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
        self.onMouseLeave(lambda: (setattr(self, 'redraw', True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
        self.onMouseClick(lambda: setattr(self, 'redraw', True))

    def setNotes(self, notes):
        self.notes = notes

    def setLinkedPanels(self, panel: frame.Panel):
        self.panel = panel

    def update(self, screen):
        super().update(screen)
        if self.redraw and self.panel:
            self.panel.render(screen)

    def render(self, screen):
        screen.fill(gui.BG_COLOR)
        offsetY = (ceil(viewRow) - viewRow - 1) * tileHeight + 80
        y = 0
        while offsetY < pygame.display.get_window_size()[1]:
            litRow = (ceil(viewRow + y - 1) % 2 == 0)
            noteToWrite = self.notes[11 - (ceil(viewRow + y - 1) % 12)]
            octaveToWrite = 8 - ceil(viewRow + y - 1) // 12
            pygame.draw.rect(screen, gui.ALT_BG_COLOR_4 if (litRow) else gui.ALT_BG_COLOR_3,
                                (1, offsetY + 1, 78, tileHeight - 2), border_radius=3)
            gui.stamp(screen, f"{noteToWrite} {octaveToWrite}", gui.SUBHEADING1, 5, offsetY + 5, gui.ALT_TEXT_COLOR)
            if pygame.mouse.get_pressed()[0] and gui.mouseBounds((1, offsetY + 1, 78, tileHeight - 2)):
                sp.playNotes(notes=[(11 - (ceil(viewRow + y - 1) % 12)) + 12 * (7 - ceil(viewRow + y - 1) // 12) + 1], duration=0.2, volume=0.05)
            
            offsetY += tileHeight
            y += 1

class NoteGrid(gui.Interactive):
    '''
    Class that manages interactivity of the note grid, and renders the note elements.
    '''
    def __init__(self, pos, width, height):
        super().__init__(pos, width, height)
        self.noteMap = {}
        self.scVel = [0, 0]
        self.interval = 4

        self.selectionRect = None

        def changeView(xy):
            global viewRow, viewCol
            self.redraw = True
            viewCol += xy[0] / 8
            viewRow -= xy[1] / 8
            if viewCol <= 0:
                viewCol = 0
            if viewRow <= 12:
                viewRow = 12
            if viewRow >= 84:
                viewRow = 84
            x, y = xy
            self.scVel = [x * 2, y * 2]

        self.onMouseClick(lambda: setattr(self, 'redraw', True))
        self.onHoverScroll(changeView)

    def setNoteMap(self, noteMap):
        '''
        fields:
            noteMap (dict) - noteMap passed in
        
        Updates the internal noteMap to match the main noteMap.
        '''
        self.noteMap = noteMap

    def setIntervals(self, interval: int):
        '''
        fields:
            interval (number) - interval between light tiles
        
        Updates the internal interval to match the main interval.
        '''
        self.interval = interval

    def setLinkedPanels(self, panel: frame.Panel, notes: frame.Panel):
        self.panel = panel
        self.notes = notes

    def setSelection(self, rect):
        self.selectionRect = rect
    
    def update(self, screen):
        global viewCol, viewRow
        super().update(screen)
        if self.panel and self.notes and (self.redraw or self.scVel != [0, 0]):
            if self.scVel[0] < 0:
                self.scVel = [self.scVel[0] + 1, self.scVel[1]]
            if self.scVel[0] > 0:
                self.scVel = [self.scVel[0] - 1, self.scVel[1]]
            if self.scVel[1] < 0:
                self.scVel = [self.scVel[0], self.scVel[1] + 1]
            if self.scVel[1] > 0:
                self.scVel = [self.scVel[0], self.scVel[1] - 1]
            viewCol += self.scVel[0] / 20
            viewRow -= self.scVel[1] / 20
            if viewCol <= 0:
                viewCol = 0
            if viewRow <= 12:
                viewRow = 12
            if viewRow >= 84:
                viewRow = 84
            self.panel.render(screen)
            self.notes.render(screen)
    
    def render(self, screen):
        screen.fill(gui.BG_COLOR)
        offsetX = (ceil(viewCol) - viewCol - 1) * tileWidth + 80
        #console.log((viewCol, offsetX))
        x = 0
        while offsetX < pygame.display.get_window_size()[0]:
            offsetY = (ceil(viewRow) - viewRow - 1) * tileHeight + 80
            litCol = (ceil(viewCol + x - 1) % self.interval == 0)
            y = 0
            while offsetY < pygame.display.get_window_size()[1]:
                litRow = (ceil(viewRow + y - 1) % 2 == 0)
                pygame.draw.rect(screen, gui.ALT_BG_COLOR_1 if (litRow != litCol) else gui.ALT_BG_COLOR_2 if (litRow and litCol) else gui.ALT_BG_COLOR,
                                 (offsetX + 1, offsetY + 1, tileWidth - 2, tileHeight - 2), border_radius=3)
                offsetY += tileHeight
                y += 1
            offsetX += tileWidth
            x += 1

        for colorIdx, colorChannel in enumerate(self.noteMap.items()):
            colorName = colorChannel[0]
            colorNotes = colorChannel[1]

            for note in colorNotes:
                if isinstance(note, Note):
                    note.render(screen, colors[colorIdx], False, [0,0])
                else:
                    raise ValueError(f'Invalid data type for note: {note.__class__()}')
        
        if self.selectionRect:
            pygame.draw.rect(screen, (255, 255, 255, 255), self.selectionRect, 1)
            #pygame.draw.rect(screen, (255, 255, 255, 5), self.selectionRect)

class PlayHead():
    '''
    Class to contain the playhead, which cues music playback and displays it on the screen
    '''
    def __init__(self):
        # playhead properties
        self.time = 0
        self.home = 0
        self.tpm = 360
        self.playing = False
        self.lastPlayTime = time.time()

        self.panel = None

    def setHome(self, home):
        self.home = home
        self.time = self.home

    def play(self, tpm):
        self.playing = True
        self.tpm = tpm
        self.lastPlayTime = time.time()

    def stop(self):
        self.playing = False
        self.time = self.home

    def setLinkedPanel(self, panel):
        self.panel = panel
    
    def update(self, screen: pygame.Surface):
        if self.playing:
            secondsPassed = time.time() - self.lastPlayTime
            minutesPassed = secondsPassed / 60
            tilesPassed = minutesPassed * self.tpm
            self.time = self.home + tilesPassed

            if self.panel != None:
                self.panel.render(screen)
        else:
            self.time = self.home

    def render(self, screen: pygame.Surface):
        lineX = convertGridToWorld(self.time, 0)[0]
        pygame.draw.line(screen,
                    (0, 255, 255, 255) if self.playing else (255, 255, 0, 255),
                    (lineX, 0),
                    (lineX, pygame.display.get_window_size()[1]),
                    1)

class Note():
    '''
    Class to contain notes, which are interactive and renderable. Their data is also
    exposed as a dict for when saving.
    '''
    def __init__(self, noteData: dict):
        # note properties
        self.pitch = noteData.get('pitch', 1)
        self.time = noteData.get('time', 1)
        self.duration = noteData.get('duration', 1)
        self.dataFields = noteData.get('data_fields', {})

        self.selected = False
        self.visible = True
        self.dragInitialPosition = None
    
    def __repr__(self):
        return f"Note object with Pitch: {self.pitch}, Time: {self.time}, Duration: {self.duration}, Data Fields: {self.dataFields}, Selected?: {self.selected}"

    def getData(self):
        return {
            "pitch" : self.pitch,
            "time" : self.time,
            "duration" : self.duration,
            "data_fields" : self.dataFields
        }

    def select(self):
        self.selected = True
        self.drag()
    
    def unselect(self):
        self.selected = False
        self.undrag()

    def hide(self):
        self.visible = False
    
    def unhide(self):
        self.visible = True

    def drag(self):
        self.dragInitialPosition = [self.time, self.pitch]
    
    def undrag(self):
        self.dragInitialPosition = None
    
    def setNoteData(self, newData: dict):
        '''
        fields:
            newData (dict) - dictionary of all the fields that need updating
        outputs: nothing

        Non-destructively updates the data of the object with optional fields.
        '''
        self.pitch = newData.get('pitch', self.pitch)
        self.time = newData.get('time', self.time)
        self.duration = newData.get('duration', self.duration)
        self.dataFields = newData.get('data_fields', self.dataFields)

    def render(self, screen: pygame.Surface, color: tuple[int, int, int, int], transparent = False, tileOffset: tuple = None): 

        drawScreen = pygame.Surface(pygame.display.get_window_size(), pygame.SRCALPHA)
        rectCoords = [
            *convertGridToWorld(self.time, self.pitch, (tileWidth, tileHeight), (viewCol, viewRow)),
            self.duration * tileWidth,
            tileHeight
        ]
        pygame.draw.rect(drawScreen, (*color[:3], 128 if transparent else 255), rectCoords, border_radius=3)
        if self.selected:
            pygame.draw.rect(drawScreen, (255, 255, 255, 255), rectCoords, width=2, border_radius=3)
        screen.blit(drawScreen, [0, 0])