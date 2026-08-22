# gui/element/dropdown.py
# module for handling dropdown rendering and interactions.
###### IMPORT ######

from __future__ import annotations

import pygame
from math import *

###### INTERNAL MODULES ######

import gui.element.base_element as base
from gui.element.base_element import stamp
from gui.element.base_interactive import Interactive
from gui.element.colors import *

import gui.dom as dom
from console_controls.console import *

###### CLASSES ######

class Dropdown(Interactive):
    '''
    Class to contain dropdowns, which inherit an interactive, having states and open/closed state.
    '''
    def __init__(self, width, height, states: list, font: pygame.font.Font | None = None, image: pygame.Surface | None = None, name=''):
        super().__init__(width, height, name)

        # button properties
        self.initHeight = height
        self.states = states
        self.currentStateIdx = 0
        self.currentState = self.states[self.currentStateIdx]
        self.font = font if (font != None) else base.SUBHEADING1
        self.image = image if (image != None) else pygame.Surface((16, 16), pygame.SRCALPHA)
        self.expanded = False
        self.onSelectCallback = None
        self.onCloseCallback = None

        self.onMouseEnter(lambda: (setattr(self, "redraw", True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
        self.onMouseLeave(lambda: (setattr(self, "redraw", True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
        
        self.onMouseClick(self.handleClick)
        self.onMouseClickOut(self.handleClickOut)

    def handleClick(self):
        self.redraw = True
        self.expanded = not self.expanded
        if self.expanded:
            self.height = self.initHeight * (len(self.states) + 1)
        else:
            if ((pygame.mouse.get_pos()[1] - self.offsetY) // self.initHeight) - 1 == -1:
                self.handleClickOut() # if we select the top item (the placeholder), treat it like clicking out
            else:
                self.setCurrentState(((pygame.mouse.get_pos()[1] - self.offsetY) // self.initHeight) - 1)
                self.height = self.initHeight
                if callable(self.onSelectCallback) : self.onSelectCallback()
                if callable(self.onCloseCallback): self.onCloseCallback()

    def handleClickOut(self):
        self.redraw = True
        self.expanded = False
        self.height = self.initHeight
        if callable(self.onCloseCallback): self.onCloseCallback()

    def onSelect(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when a dropdown item is selected.
        '''
        self.onSelectCallback = function

    def onClose(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when a dropdown is closed.
        '''
        self.onCloseCallback = function 

    def cycleStates(self):
        self.currentStateIdx = (self.currentStateIdx + 1) % len(self.states)
        self.currentState = self.states[self.currentStateIdx]
    
    def setCurrentState(self, idx):
        if idx >= len(self.states):
            idx = 1
            console.error
        if idx < 0:
            idx = 0
        self.currentStateIdx = idx
        self.currentState = self.states[self.currentStateIdx]
    
    def update(self, screen):
        super().update(screen)
        if self.redraw:
            dom.dirty(self)

    def renderState(self, screen: pygame.Surface, state, yCenter):
        '''
        fields:
            screen (pygame.Surface) - the surface to draw to
            state (string | pygame.Surface) - the object or string to draw in the state
            yCenter (number) - the center of the state, as an offset from the dropdown's rect

        Renders one of the "states" of a dropdown, applies for both collapsed and expanded dropdowns.
        '''
        stateCenterX = self.width/2 - 4
        if isinstance(state, pygame.Surface): # if it's an image (icon)
            loc = (stateCenterX - state.get_width() / 2,
                   yCenter - state.get_height() / 2)
            screen.blit(state, loc)
        else:
            stamp(screen, state, self.font, stateCenterX, yCenter, COLOR_TEXT_ALT, justification="center")

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        if not self.expanded:
            pygame.draw.rect(self.surface, COLOR_ALT_BG_1 if self.mouseInside else COLOR_ALT_BG_4, (0, 0, self.width, self.height), border_radius=3)
            self.renderState(self.surface, self.currentState, self.height/2)

            self.surface.blit(self.image, (self.width - self.image.get_width() - 4, (self.height / 2) - (self.image.get_height() / 2)))
        if self.expanded:
            pygame.draw.rect(self.surface, COLOR_ALT_BG_4, (0, 0, self.width, self.height), border_radius=3)
            self.renderState(self.surface, self.currentState, self.initHeight/2)

            self.surface.blit(self.image, (self.width - self.image.get_width() - 4, (self.initHeight / 2) - (self.image.get_height() / 2)))
        
            # dropdown bg
            pygame.draw.rect(self.surface, COLOR_ALT_BG_4, (0, self.initHeight, self.width, self.height - self.initHeight), border_radius=3)
            # outline
            pygame.draw.rect(self.surface, COLOR_BORDER, (0, self.initHeight, self.width, self.height - self.initHeight), border_radius=3, width=1)
            # selected item highlight
            pygame.draw.rect(self.surface, COLOR_ALT_BG_1, (0, self.initHeight + (self.currentStateIdx * self.initHeight), self.width, self.initHeight), border_radius=3)
            for idx, state in enumerate(self.states):
                self.renderState(self.surface, state, self.initHeight/2 + ((idx + 1) * self.initHeight))

        # then, blit this surface onto the passed surface
        super().render(screen, positioning)