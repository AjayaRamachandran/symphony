# gui/custom.py
# module for holding data for custom gui elements, bespoke interfaces.
###### IMPORT ######

from __future__ import annotations

import pygame
import time
from io import BytesIO
from math import *

###### INTERNAL MODULES ######

from console_controls.console import *
import gui.element as element
import gui.frame as frame
import sound.sound_processing as sp
import gui.dom as dom
import utils.util as utils
import events

###### INITIALIZE ######

# Watchable view state. Panels watch these directly, so scrolling and zooming dirty the
# affected panels without any component having to reach up and dirty its parent by hand.
viewRow = utils.LightWatchable(0)  # will be initialized when GUI opens
viewCol = utils.LightWatchable(0)  # will be initialized when GUI opens
tileWidth = utils.LightWatchable(30)
tileHeight = utils.LightWatchable(30)


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
        element.stamp(surf, str(idx + 1), element.SUBHEADING1, width/2, height/2, element.COLOR_BG, justification='center')
        outputs.append(surf)
    
    element.stamp(rainbowImage, '7', element.SUBHEADING1, rainbowImage.get_width()/2, rainbowImage.get_height()/2, element.COLOR_BG, justification='center')
    outputs.append(rainbowImage)
    return outputs

def convertGridToWorld(time, pitch, tileSize: tuple[int | float, int | float] | None = None, view: tuple[int | float, int | float] | None = None, rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)):
    '''
    fields:
        time (number) - the time of the grid coordinate
        pitch (number) - the pitch of the grid coordinate
        tileSize (tuple[number]) - the coordinate dimensions of the grid tiles
        view (tuple[number]) - the coordinates of the view camera in relation to the GRID
        rect (pygame.Rect) - a rect to apply to conversions (local to world space)
    outputs: tuple[number]
    
    Converts the Grid coordinates to Screen (world) coordinates.
    '''

    _tileWidth, _tileHeight = tileSize if tileSize is not None else (tileWidth.value, tileHeight.value)
    _viewCol, _viewRow = view if view is not None else (viewCol.value, viewRow.value)

    return [(time - viewCol.value) * _tileWidth - rect.topleft[0], ((84 - viewRow.value) - pitch) * _tileHeight - rect.topleft[1]]

def convertWorldToGrid(mousePos, tileSize: tuple[int | float, int | float] | None = None, view: tuple[int | float, int | float] | None = None, timeInt = True, rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)):
    '''
    fields:
        mousePos (tuple[number]) - the mouse coordinates in world/screen space
        tileSize (tuple[number]) - the coordinate dimensions of the grid tiles
        view (tuple[number]) - the coordinates of the view camera in relation to the GRID
        timeInt (boolean) - whether or not to round the values
        rect (pygame.Rect) - a clipping mask to omit conversions outside of
    outputs: tuple[number]
    
    Converts Screen (world) coordinates to Grid coordinates.
    '''

    mouseX, mouseY = mousePos

    if not rect.collidepoint(mousePos):
        return None, None
    
    _tileWidth, _tileHeight = tileSize if tileSize is not None else (tileWidth.value, tileHeight.value)
    _viewCol, _viewRow = view if view is not None else (viewCol.value, viewRow.value)

    time = (mouseX - rect.topleft[0]) / _tileWidth + _viewCol
    pitch = (84 - _viewRow) - (mouseY - rect.topleft[1]) / _tileHeight

    return floor(time) if timeInt else time, ceil(pitch)

###### CLASSES ######

class PitchList(element.Interactive):
    '''
    Class that manages the Pitch list on the left side of the screen, and how it plays back notes.
    '''
    def __init__(self, width, height, name):
        super().__init__(width, height, name=name)

        # every piece of state below is owned elsewhere; these getters read the live value
        # so the PitchList never holds a stale shadow copy
        self.modeGetter = lambda: [0, 2, 4, 6, 7, 9, 11]
        self.keyGetter = lambda: 3
        self.noteGetter = lambda: []
        self.waveGetter = lambda: {}

        self.onMouseEnter(lambda: (setattr(self, 'redraw', True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
        self.onMouseLeave(lambda: (setattr(self, 'redraw', True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
        self.onMouseClick(self.onPitchListClick)

    def setMode(self, modeGetter):
        '''
        fields:
            modeGetter (function -> list[int]) - a getter for the 12TET notes in the current mode
        outputs: none

        Sets the internal modeGetter lambda so the live mode can be read whenever needed.
        '''
        self.modeGetter = modeGetter

    def setKey(self, keyGetter):
        '''
        fields:
            keyGetter (function -> int) - a getter for the index of the current key
        outputs: none

        Sets the internal keyGetter lambda so the live key can be read whenever needed.
        '''
        self.keyGetter = keyGetter

    def setNotes(self, noteGetter):
        '''
        fields:
            noteGetter (function -> list[str]) - a getter function for the latest noteList
        outputs: none

        Sets the internal noteGetter lambda so it can be called to get the notes whenever needed.
        '''
        self.noteGetter = noteGetter

    def setWave(self, waveGetter):
        '''
        fields:
            waveGetter (function -> list[str]) - a getter function for the latest waveMap
        outputs: none

        Sets the internal waveGetter lambda so it can be called to get the wavemap whenever needed.
        '''
        self.waveGetter = waveGetter

    def setLinkedPanels(self, panel: frame.Panel):
        '''
        fields:
            panel (Panel) - linked Panel
        
        Sets the linked NotePanel to render with the PitchList is updated.
        '''
        self.panel = panel

    def onPitchListClick(self):
        '''
        Handles pitch list clicks and plays the clicked note.
        '''

        self.redraw = True

        mouseY = pygame.mouse.get_pos()[1]
        baseRow = int(viewRow.value)
        frac = viewRow.value - baseRow
        offsetY = (-frac) * tileHeight.value + self.y
        rowOffset = floor((mouseY - offsetY) / tileHeight.value)
        rowIndex = baseRow + rowOffset

        note = (-1 - (rowIndex % 12)) + 12 * (7 - rowIndex // 12) + 1
        sp.playNote(note=note, waves=self.waveGetter(), duration=0.2)
        console.log(f"played note {note}")

    def calculateDimensions(self, parentDimensions: list[int] | tuple[int]):
        '''
        Updates the PitchList's dimensions to be inherited from its parent. This overwrites the default calculateDimensions()
        behavior of an Element, which is to do nothing.
        '''
        # console.log(f"calculating dimensions of child element {self.name} to be {[80, parentDimensions[1]]}")
        self.width = 80
        self.height = parentDimensions[1]
        # if the panel has no surface yet, or it does not match its new dimensions, (re)build it.
        if self.surface is None or self.surface.get_size() != (self.width, self.height):
            self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def update(self, screen):
        super().update(screen)
        if self.redraw and self.panel:
            dom.dirty(self.panel)

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        # resolve every externally owned value once for this pass
        mode = self.modeGetter()
        key = self.keyGetter()
        notes = self.noteGetter()

        screen.fill(element.COLOR_BG)
        # split viewRow into a stable integer row index and a fractional scroll offset
        # this avoids floating-point precision issues (e.g. 53.00000000000001)
        baseRow = int(viewRow.value)
        frac = viewRow.value - baseRow
        offsetY = (-frac) * tileHeight.value # calculate the vertical pixel offset caused by partial scrolling
        y = 0
        while offsetY < pygame.display.get_window_size()[1]:
            rowIndex = baseRow + y # calculate the absolute row index for this tile

            litRow = ((11 - ((rowIndex + key) % 12)) in mode)

            noteToWrite = notes[11 - (rowIndex % 12)]
            octaveToWrite = 8 - (rowIndex // 12)

            pygame.draw.rect(screen, element.COLOR_ALT_BG_4 if litRow else element.COLOR_ALT_BG_3, (1, offsetY + 1, 78, tileHeight.value - 2), border_radius=3)
            element.stamp(screen, f"{noteToWrite} {octaveToWrite}", element.SUBHEADING1, 5, offsetY + 5, element.COLOR_TEXT_ALT)

            offsetY += tileHeight.value
            y += 1



class NoteGrid(element.Interactive):
    '''
    Class that manages interactivity of the note grid, and renders the note elements.
    '''
    def __init__(self, width, height, name):
        super().__init__(width, height, name=name)
        # every piece of state below is owned elsewhere; these getters read the live value
        # so the NoteGrid never holds a stale shadow copy
        self.noteMapGetter = lambda: {}
        self.colorGetter = lambda: 0
        # colour names in order: ["orange", "purple", "cyan", "lime", "blue", "pink", "all"]
        self.colorNamesGetter = lambda: []
        self.beatLengthGetter = lambda: 4
        self.beatsPerMeasureGetter = lambda: 4
        self.modeGetter = lambda: [0, 2, 4, 6, 7, 9, 11]
        self.keyGetter = lambda: 3

        self.scVel = [0, 0]

        self.selectionRect = None

        def changeView(xy):
            self.redraw = True

            self.scVel[0] += xy[0] / 2
            
            self.scVel[1] += xy[1] / 2

            for dim in [0, 1]:
                if (xy[dim] > 0) != (self.scVel[dim] > 0) and (xy[dim] < 0) != (self.scVel[dim] < 0):
                    #console.log(f"xy: {xy}, scvel: {self.scVel}")
                    self.scVel[dim] *= -0.2
                else:
                    self.scVel[dim] *= 1.03

            if viewCol.value <= 0:
                viewCol.set(0)
            self.viewBounds()
            x, y = xy

        self.onMouseClick(lambda: setattr(self, 'redraw', True))
        self.onHoverScroll(changeView)

    def viewBounds(self):
        numRowsVisible = self.height / tileHeight.value
        if viewRow.value <= 23:
            viewRow.set(23)
        if viewRow.value >= 96 - numRowsVisible:
            viewRow.set(96 - numRowsVisible)
        #console.log((viewRow.value, viewCol.value))

    def setNoteMap(self, noteMapGetter):
        '''
        fields:
            noteMapGetter (function -> dict) - a getter for the live noteMap
        outputs: none

        Sets the internal noteMapGetter lambda so the latest noteMap can be read whenever needed.
        '''
        self.noteMapGetter = noteMapGetter

    def setColor(self, colorGetter):
        '''
        fields:
            colorGetter (function -> int) - a getter for the index of the active color channel
        outputs: none

        Sets the internal colorGetter lambda so the live color channel can be read whenever needed.
        '''
        self.colorGetter = colorGetter

    def setColorNames(self, colorNamesGetter):
        '''
        fields:
            colorNamesGetter (function -> list[str]) - a getter for the ordered color name list
        outputs: none

        Sets the internal colorNamesGetter lambda, used for color channel lookup.
        '''
        self.colorNamesGetter = colorNamesGetter

    def setIntervals(self, beatLengthGetter, beatsPerMeasureGetter):
        '''
        fields:
            beatLengthGetter (function -> int) - a getter for the interval between light tiles
            beatsPerMeasureGetter (function -> int) - a getter for the beats in a measure
        outputs: none

        Sets the internal interval getters so the live values can be read whenever needed.
        '''
        self.beatLengthGetter = beatLengthGetter
        self.beatsPerMeasureGetter = beatsPerMeasureGetter

    def setMode(self, modeGetter):
        '''
        fields:
            modeGetter (function -> list[int]) - a getter for the 12TET notes in the current mode
        outputs: none

        Sets the internal modeGetter lambda so the live mode can be read whenever needed.
        '''
        self.modeGetter = modeGetter

    def setKey(self, keyGetter):
        '''
        fields:
            keyGetter (function -> int) - a getter for the index of the current key
        outputs: none

        Sets the internal keyGetter lambda so the live key can be read whenever needed.
        '''
        self.keyGetter = keyGetter

    def setLinkedPanels(self, panel: frame.Panel, notes: frame.Panel):
        '''
        fields:
            panel (Panel) - the linked NotePanel
            notes (Panel) - the linked PitchPanel

        Sets the linked panels to be rendered when the NoteGrid is updated. This is a structural
        link, not a data dependency: the grid is repainted as part of its parent panel's surface.
        '''
        self.panel = panel
        self.notes = notes

    def setSelection(self, rect):
        self.selectionRect = rect

    def calculateDimensions(self, parentDimensions: list[int] | tuple[int]):
        '''
        Updates the NoteGrid's dimensions to be inherited from its parent. This overwrites the default calculateDimensions()
        behavior of an Element, which is to do nothing.
        '''
        # console.log(f"calculating dimensions of child element {self.name} to be {parentDimensions}")
        self.width = parentDimensions[0]
        self.height = parentDimensions[1]
        # if the panel has no surface yet, or it does not match its new dimensions, (re)build it.
        if self.surface is None or self.surface.get_size() != (self.width, self.height):
            self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
    
    def update(self, screen):
        super().update(screen)
        if self.panel and self.notes and (self.redraw or self.scVel != [0, 0]):
            self.scVel = [self.scVel[0] * 0.94, self.scVel[1] * 0.94]

            viewCol.set(viewCol.value + self.scVel[0] / 24)
            viewRow.set(viewRow.value - self.scVel[1] / 24)

            if abs(self.scVel[0]) < 1:
                self.scVel[0] = 0
            if abs(self.scVel[1]) < 1:
                self.scVel[1] = 0

            if viewCol.value <= 0:
                viewCol.set(0)

            self.viewBounds()

            dom.dirty(self.panel)
            dom.dirty(self.notes)
    
    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        # resolve every externally owned value once for this pass
        noteMap = self.noteMapGetter()
        color = self.colorGetter()
        colorNames = self.colorNamesGetter()
        beatLength = self.beatLengthGetter()
        beatsPerMeasure = self.beatsPerMeasureGetter()
        mode = self.modeGetter()
        key = self.keyGetter()

        self.surface.fill(element.COLOR_BG)
        # split viewCol into integer column index and fractional scroll offset
        baseCol = int(viewCol.value)
        fracCol = viewCol.value - baseCol
        offsetX = (-fracCol) * tileWidth.value # initial horizontal pixel offset from partial scrolling
        x = 0
        while offsetX < pygame.display.get_window_size()[0]:
            # absolute column index for this tile
            colIndex = baseCol + x

            litColAmount = int(colIndex % beatLength == 0) + int(colIndex % (beatLength * beatsPerMeasure) == 0)

            baseRow = int(viewRow.value) # split viewRow into integer row index and fractional scroll offset
            fracRow = viewRow.value - baseRow
            offsetY = (-fracRow) * tileHeight.value # initial vertical pixel offset from partial scrolling
            y = 0
            while offsetY < pygame.display.get_window_size()[1]:
                rowIndex = baseRow + y # absolute row index for this tile

                litRow = ((11 - ((rowIndex + key) % 12)) in mode)

                thisColor = element.COLOR_GRID_BG
                if not litRow:
                    if litColAmount == 1:
                        thisColor = element.COLOR_GRID_BG_BEAT
                    elif litColAmount == 2:
                        thisColor = element.COLOR_GRID_BG_MEASURE
                else:
                    if litColAmount == 0:
                        thisColor = element.COLOR_GRID_LITROW
                    elif litColAmount == 1:
                        thisColor = element.COLOR_GRID_LITROW_BEAT
                    elif litColAmount == 2:
                        thisColor = element.COLOR_GRID_LITROW_MEASURE

                pygame.draw.rect(self.surface, thisColor, (offsetX + 1, offsetY + 1, tileWidth.value - 2, tileHeight.value - 2), border_radius=3)

                offsetY += tileHeight.value
                y += 1
            offsetX += tileWidth.value
            x += 1

        # render all color channels except the selected one
        for colorName, colorNotes in noteMap.items():
            try: colorIdx = colorNames.index(colorName) if colorNames else 0
            except ValueError: continue
            
            # skip rendering the selected color (it will be rendered separately)
            if color != 6 and colorIdx == color:
                continue
            for note in colorNotes:
                if isinstance(note, Note):
                    note.render(self.surface, colors[colorIdx] if colorIdx < len(colors) else colors[0], color != 6 and color != colorIdx, [0,0])
                else:
                    if isinstance(note, dict):
                        note.render(self.surface, colors[colorIdx] if colorIdx < len(colors) else colors[0], color != 6 and color != colorIdx, [0,0])

                    raise ValueError(f'Invalid data type for note: {note.__class__()}')
        
        # Render the selected color channel (if not "all" and it exists)
        if color != 6 and len(colorNames) > color:
            selectedColorName = colorNames[color]
            if selectedColorName in noteMap:
                colorNotes = noteMap[selectedColorName]
                for note in colorNotes:
                    if isinstance(note, Note):
                        note.render(self.surface, colors[color], False)
                    else:
                        raise ValueError(f'Invalid data type for note: {note}')

        if self.selectionRect:
            pygame.draw.rect(self.surface, (255, 255, 255, 255), self.selectionRect, 1)

        super().render(screen, positioning)

class PlayHead(element.Element):
    '''
    Class to contain the playhead, which cues music playback and displays it on the screen.
    It draws straight onto its parent panel's surface, so it is sized 0x0 and kept out of
    the flexbox via absolute display.
    '''
    def __init__(self, name='PlayHead'):
        super().__init__(0, 0, name=name, style={"display": "absolute", "offset": [0, 0]})

        # playhead properties
        self.time = 0
        self.home = 0
        self.tempo = 360
        self.playing = False
        self.lastPlayTime = time.time()

        self.onExitViewCallback = None
        self.panel = None

    def setHome(self, home):
        self.home = home
        self.time = self.home

    def play(self, tempo):
        self.playing = True
        self.tempo = tempo
        self.lastPlayTime = time.time()

    def stop(self):
        self.playing = False
        self.time = self.home

    def setLinkedPanel(self, panel):
        self.panel = panel
    
    def update(self, screen: pygame.Surface):
        super().update(screen)

        if self.playing:
            secondsPassed = time.time() - self.lastPlayTime
            minutesPassed = secondsPassed / 60
            tilesPassed = minutesPassed * self.tempo
            self.time = self.home + tilesPassed

            if self.panel != None:
                dom.dirty(self.panel)
        else:
            self.time = self.home
    
    def onExitView(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the playhead leaves the view.
        '''
        self.onExitViewCallback = function

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        lineX = convertGridToWorld(self.time, 0)[0]
        if lineX > screen.get_width():
            if callable(self.onExitViewCallback): self.onExitViewCallback()

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
        self.extendOriginalDuration = self.duration
    
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

    def render(self, screen: pygame.Surface, color: tuple[int, int, int, int], transparent: bool = False): 
        #drawScreen = pygame.Surface(pygame.display.get_window_size(), pygame.SRCALPHA)
        rectCoords = [
            *convertGridToWorld(self.time, self.pitch, (tileWidth.value, tileHeight.value), (viewCol.value, viewRow.value)),
            self.duration * tileWidth.value,
            tileHeight.value
        ]
        lineCoordsTop = [
            rectCoords[0] + rectCoords[2] - 6,
            rectCoords[1] + 5
        ]
        lineCoordsBottom = [
            rectCoords[0] + rectCoords[2] - 6,
            rectCoords[1] + rectCoords[3] - 5
        ]
        lineCoordsTop2 = [
            rectCoords[0] + rectCoords[2] - 10,
            rectCoords[1] + 5
        ]
        lineCoordsBottom2 = [
            rectCoords[0] + rectCoords[2] - 10,
            rectCoords[1] + rectCoords[3] - 5
        ]
        pygame.draw.rect(screen, ([100, 100, 100, 255] if transparent else color), rectCoords, border_radius=3)
        pygame.draw.line(screen, ([80, 80, 80, 255] if transparent else [*[min(255, color[a]*0.8) for a in range(3)], 255]),
                         lineCoordsTop, lineCoordsBottom, 2)
        # pygame.draw.line(screen, ([80, 80, 80, 255] if transparent else [*[min(255, color[a]*0.8) for a in range(3)], 255]),
        #                  lineCoordsTop2, lineCoordsBottom2, 2)
        if self.selected:
            pygame.draw.rect(screen, (255, 255, 255, 255), rectCoords, width=2, border_radius=3)
        #screen.blit(screen, [0, 0])