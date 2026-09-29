# gui/element/base_element.py
# module for handling gui element rendering and interactions.
###### IMPORT ######

from __future__ import annotations

import pygame
from math import *

###### INTERNAL MODULES ######

from gui.element.colors import *

import gui.dom as dom
from console_controls.console import *
import sound.sound_processing as sp
import utils.util as utils
import events

###### INITIALIZE ######

source_path = 'inner/src'
DRAG_THRESHOLD = 2


TITLE1 = None
HEADING1 = None
SUBHEADING1 = None
BODY = None
SUBSCRIPT1 = None

def init(sourcePath):
    global source_path, TITLE1, HEADING1, SUBHEADING1, BODY, SUBSCRIPT1

    source_path = sourcePath
    mainFont = f'{source_path}/assets/InterVariable.ttf'
    TITLE1 = pygame.font.Font(mainFont, 60)
    HEADING1 = pygame.font.Font(mainFont, 24)
    SUBHEADING1 = pygame.font.Font(mainFont, 14)
    BODY = pygame.font.Font(mainFont, 13)
    SUBSCRIPT1 = pygame.font.Font(mainFont, 12)

###### METHODS ######

def inBounds(coords1, coords2, point) -> bool:
    '''
    fields:
        coords1 (pair[number]) - first coordinate\n
        coords2 (pair[number]) - second coordinate\n
        point (pair[number]) - point to check
    outputs: boolean

    Returns whether a point is within the bounds of two other points. order of coords is arbitrary.
    '''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def mouseBounds(rect):
    '''
    fields:
        rect (rect) - 4-coordinate x, y, dx, dy representing the bounds
    outputs: boolean

    Returns whether the mouse is within a rect-formatted bounding box.
    '''
    return rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]

def mouseFunction(rect):
    '''
    fields:
        rect (rect) - 4-coordinate x, y, dx, dy representing the bounds
    outputs: tuple

    Function that returns a color based on whether the mouse is in the bounding box.
    '''
    isInside = mouseBounds(rect)
    return ((20, 20, 20) if isInside and pygame.mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

def stamp(screen, text, style, x, y, color: tuple | None = None, brightness: float | None = None, justification: str = "left"):
    '''
    fields:
        screen (pygame.Surface) - screen to blit to\n
        text (string) - text to write to screen\n
        style (pygame.font.Font) - style to write text in\n
        x (number) - x-coordinate of anchor point\n
        y (number) - y-coordinate of anchor point\n
        color (tuple) - color value to print text in, takes precedence over luminance\n
        luminance (number) - value between 0 and 1 that represents brightness of text, shorthand to avoid color\n
    Function to draw text to the screen abstracted, makes text drawing easy.
    Left and Right justifications are aligned with the respective *top corners* of the rect, while Center is true Center.
    '''
    if color:
        text = style.render(text, True, color)
    elif brightness:
        text = style.render(text, True, (round(brightness*255), round(brightness*255), round(brightness*255)))
    else:
        raise ValueError('color and brightness cannot both be None')
    
    if justification == "left":
        textRect = (x, y, text.get_rect()[2], text.get_rect()[3])
    elif justification == "right":
        textRect = (x - text.get_rect()[2], y, text.get_rect()[2], text.get_rect()[3])
    else:
        textRect = (x - (text.get_rect()[2]/2), y - (text.get_rect()[3]/2), text.get_rect()[2], text.get_rect()[3])
    
    screen.blit(text, textRect)

def unselectTextBoxes(globalTextBoxes):
    '''
    fields: none\n
    outputs: nothing

    Loops through all text boxes and unselects them.
    '''
    for tb in globalTextBoxes:
        tb.selected = False

###### CLASSES ######

class Element():
    '''
    Base for object in the DOM: damaging, style, dependency watching, etc.
    Panel inherits from this.
    '''

    def __init__(self, width: int = 0, height: int = 0, style: dict | None = {}, name: str = ''):
        self.name = name
        self.style = style if style is not None else {}
        self.width = width
        self.height = height
        self.offsetX = 0
        self.offsetY = 0
        self.x = 0
        self.y = 0
        self.z = 0
        self.display = self.style.get("display", "flex")
        self.domStatus = "clean"
        self.surface: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.damageRects: list[pygame.Rect] = []
        self.watching: list[utils.Watchable] = []
        self.oldWatching: list = []
        self.depChange = None

    def __str__(self):
        return self.name

    def watch(self, deps: list[utils.Watchable] | utils.Watchable, operation: str = 'set'):
        '''
        fields:
            deps (list[Watchable] | Watchable) - what dependencies to add/set to watchlist
            operation ('set', 'add') - what operation to do with the passed deps
        outputs: none

        Adds or sets a list of dependencies (Watchable objects) that determine when the component rerenders.
        '''

        if isinstance(deps, list):
            for watched in deps:
                if not (isinstance(watched, utils.Watchable)):
                    raise ValueError(f'All elements of deps must be Watchable, not {type(watched)}')
        elif (isinstance(deps, utils.Watchable)):
            None
        else:
            raise ValueError(f'deps must be a list object or Watchable, not {type(deps)}')

        if (isinstance(deps, utils.Watchable)):
            if operation == 'set':
                self.watching = [deps]
            else:
                self.watching.append(deps)
        elif isinstance(deps, list):
            if operation == 'set':
                self.watching = deps
            else:
                for dep in deps:
                    self.watching.append(dep)

        self.oldWatching = self.snapshotWatched()

    def onDepChange(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when any deps are changed.
        '''
        self.depChange = function

    def snapshotWatched(self):
        '''
        fields: none\n
        outputs: list

        Captures the current comparison value of every watched dependency. Light watchables compare
        by value, heavy ones by their watch id.
        '''
        return [
            el.value if isinstance(el, utils.LightWatchable) else el.watchId
            for el in self.watching
        ]

    def pollWatched(self):
        '''
        fields: none\n
        outputs: nothing

        Dirties this component and fires depChange if any watched dependency changed since last frame.
        '''
        for idx, var in enumerate(self.watching):
            current = var.value if isinstance(var, utils.LightWatchable) else var.watchId

            if current != self.oldWatching[idx]:
                dom.dirty(self)
                self.depChange() if callable(self.depChange) else None

        self.oldWatching = self.snapshotWatched()

    def update(self, screen):
        '''
        fields:
            screen (pygame.Surface) - surface this component is being updated against
        outputs: nothing

        Parent update method for every component. Subclasses that override this must call
        super().update(screen) so dependency watching keeps working.
        '''
        self.pollWatched()

    def calculateDimensions(self, parentDimensions: list[int] | tuple[int]):
        '''
        fields:
            parentDimensions (pair<number, number>) - effective dimensions of the parent.
        outputs: none

        Updates the dimensions of the component optionally based on the parent. By default, nothing is done, but
        some components require this behavior (like Panel and the NoteGrid).
        '''
        None

    def rebuildSurface(self):
        if self.surface is None or self.surface.get_size() != (self.width, self.height):
            self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def dirty(self):
        '''
        Flags the component as needing to be redrawn next frame.
        '''
        self.domStatus = "dirty"

    def damage(self, damageRect: pygame.Rect):
        '''
        fields:
            damageRect (pygame.Rect) - screen space region of this component that needs repainting
        outputs: nothing
        '''
        self.domStatus = "damaged"
        self.damageRects.append(damageRect)

    def clean(self):
        '''
        Clears the dirty/damaged state after the component has been repainted.
        '''
        self.domStatus = "clean"
        self.damageRects = []

    def repair(self, screen: pygame.Surface):
        '''
        Repairs the portions of this component that are damaged, the areas which are
        stored in this component's `damageRects`.

        The screen is intended to be the global screen (so in global coords)
        '''
        componentRect = pygame.Rect(self.x, self.y, self.width, self.height)

        for damageRect in self.damageRects:
            clip = componentRect.clip(pygame.Rect(damageRect)) # .clip gets the overlapping region

            if clip.width <= 0 or clip.height <= 0:
                continue

            areaInLocalSpace = pygame.Rect(clip.x - self.x, clip.y - self.y, clip.width, clip.height)
            screen.blit(self.surface, (clip.x, clip.y), area=areaInLocalSpace) # area is a way to blit only a subsurface

    def blit(self, screen: pygame.Surface, positioning: str = 'relative'):
        '''
        fields:
            screen (pygame.Surface) - surface to blit to\n
            positioning ('screen' | 'relative') - whether or not to blit in screen space or relative space
        outputs: nothing

        The shared tail of every render(): places this component's surface onto the given screen.
        '''
        if positioning == 'screen':
            screen.blit(self.surface, (self.x, self.y))
        elif positioning == 'relative':
            screen.blit(self.surface, (self.offsetX, self.offsetY))
        else:
            raise ValueError(f"Positioning of components must be either 'screen' or 'relative', not {positioning}")

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        '''
        fields:
            screen (pygame.Surface) - surface to blit to\n
            positioning ('screen' | 'relative') - whether or not to render in screen space or relative space
        outputs: nothing

        The parent rendering method for all components. Conditionally renders true or offset coordinates based on
        the positioning parameter.
        '''
        self.blit(screen, positioning)
        
