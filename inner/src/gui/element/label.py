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
import utils.util as utils
from console_controls.console import *
import events

###### CLASSES ######

class Label(Element):
    '''
    Class to contain labels, which inherit an element, having a text and a font.

    A label can also act as a tooltip target: interactive elements call showHint/clearHint while
    hovered, and the label shows the hint in place of its own text until the hover ends.
    '''
    def __init__(self, width, height, text: str | utils.Watchable = '', font: pygame.font.Font | None = None, name=''):
        super().__init__(width, height, name=name)

        # label properties
        self.font = font if (font != None) else base.BODY
        self.redraw = False
        self.disabled = False
        self.hintOwner = None
        self.hintText = ''
        self.text: str | utils.Watchable = ''
        self.setText(text)

    def setText(self, text: str | utils.Watchable):
        '''
        fields:
            text (str | Watchable) - static text, or a Watchable whose value is shown (and tracked for rerenders)
        outputs: nothing
        '''
        if isinstance(self.text, utils.Watchable) and self.text in self.watching:
            self.watching.remove(self.text)
            self.oldWatching = self.snapshotWatched()
        self.text = text
        if isinstance(text, utils.Watchable):
            self.watch(text, operation='add')
        self.redraw = True

    def showHint(self, owner, text: str):
        '''
        fields:
            owner (object) - the element the hint belongs to

            text (string) - the hint to show

        outputs: nothing

        Shows a hover hint in place of the label's own text.
        '''
        self.hintOwner = owner
        self.hintText = text
        self.redraw = True

    def clearHint(self, owner):
        '''
        fields:
            owner (object) - the element whose hint should be cleared

        outputs: nothing

        Goes back to the label's own text, but only if `owner` still holds the hint, so a late
        leave event from one element can't wipe out the hint of a neighbour entered first.
        '''
        if self.hintOwner is owner:
            self.hintOwner = None
            self.hintText = ''
            self.redraw = True

    def displayText(self) -> str:
        '''
        fields: none\n
        outputs: str

        Resolves what the label shows: the active hint if any, otherwise its own text
        (unwrapping Watchables).
        '''
        if self.hintOwner is not None:
            return self.hintText
        value = self.text.value if isinstance(self.text, utils.Watchable) else self.text
        return '' if value is None else str(value)

    def setDisabled(self, disabled):
        self.disabled = disabled

    def update(self, screen):
        super().update(screen)

        if self.redraw and not self.disabled:
            dom.dirty(self)
    
    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        if not self.disabled:
            pygame.draw.rect(self.surface, COLOR_BG, (0, 0, self.width, self.height), border_radius=3)
            stamp(self.surface, self.displayText(), self.font, self.width/2, self.height/2, COLOR_TEXT_ALT, justification="center")
            self.redraw = False

        super().render(screen, positioning)