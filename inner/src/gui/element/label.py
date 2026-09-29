# gui/element/label.py
# module for handling label rendering.
###### IMPORT ######

from __future__ import annotations

import pygame
from math import *

###### INTERNAL MODULES ######

import gui.element.base_element as base
from gui.element.base_element import *
from gui.element.colors import *

import gui.dom as dom
from console_controls.console import *
import events

###### CLASSES ######

class Label(Element):
    '''
    Class to contain labels, which inherit an element, having a text and a font.
    '''
    def __init__(self, width, height, text = '', font: pygame.font.Font | None = None, name=''):
        super().__init__(width, height, name=name)

        # label properties
        self.text = text
        self.font = font if (font != None) else base.BODY
        self.redraw = False
        self.disabled = False

    def setText(self, text):
        self.text = text
        self.redraw = True

    def setDisabled(self, disabled):
        self.disabled = disabled

    def update(self, screen):
        super().update(screen)

        if self.redraw and not self.disabled:
            dom.dirty(self)
    
    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        if not self.disabled:
            pygame.draw.rect(self.surface, COLOR_BG, (0, 0, self.width, self.height), border_radius=3)
            stamp(self.surface, self.text, self.font, self.width/2, self.height/2, COLOR_TEXT_ALT, justification="center")
            self.redraw = False

        super().render(screen, positioning)