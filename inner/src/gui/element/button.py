# gui/element/button.py
# module for handling button rendering and interactions.
###### IMPORT ######

from __future__ import annotations

import pygame
from math import *

###### INTERNAL MODULES ######

import gui.element.base_element as base
from gui.element.base_element import *
from gui.element.base_interactive import *
from gui.element.colors import *

import gui.dom as dom
from console_controls.console import *

###### CLASSES ######

class Button(Interactive):
    '''
    Class to contain buttons, which inherit an interactive, having states and fully customizable function.
    '''
    def __init__(self, width, height, states: list, font: pygame.font.Font | None = None, name=''):
        super().__init__(width, height, name=name)

        # button properties
        self.states = states
        self.currentStateIdx = 0
        self.currentState = self.states[self.currentStateIdx]
        self.font = font if (font != None) else base.SUBHEADING1

        self.onMouseEnter(lambda: (setattr(self, "redraw", True), setattr(self, "mouseInside", True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
        self.onMouseLeave(lambda: (setattr(self, "redraw", True), setattr(self, "mouseInside", False), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
        self.onMouseClick(lambda: (setattr(self, "redraw", True), self.cycleStates()))
        self.onMouseUnClick(lambda: (setattr(self, "redraw", True)))

    def cycleStates(self):
        self.currentStateIdx = (self.currentStateIdx + 1) % len(self.states)
        self.currentState = self.states[self.currentStateIdx]
    
    def setCurrentState(self, idx):
        self.currentStateIdx = idx
        self.currentState = self.states[self.currentStateIdx]

    def update(self, screen):
        super().update(screen)
        if self.redraw:
            dom.dirty(self)

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        pygame.draw.rect(self.surface, COLOR_ALT_BG_1 if self.mouseInside else COLOR_ALT_BG_4, (0, 0, self.width, self.height), border_radius=3)
        if isinstance(self.currentState, pygame.Surface): # if it's an image (icon)
            loc = (self.width / 2 - self.currentState.get_width() / 2,
                   self.height / 2 - self.currentState.get_height() / 2)
            self.surface.blit(self.currentState, loc)
        else:
            stamp(self.surface, self.currentState, self.font, 0, 0, COLOR_TEXT_ALT, justification="center")

        # then, blit this surface onto the passed surface
        super().render(screen, positioning)