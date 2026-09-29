# gui/element/textbox.py
# module for handling text box rendering and interactions.
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
import utils.util as utils
from console_controls.console import *
import events

###### CLASSES ######

class TextBox(Interactive):
    '''
    Class to contain text boxes, which inherit a clickable, storing text and adding editing, etc.
    *Note*: TextBoxes can only have one linkedValue, but they can watch as many values as needed.
    '''
    def __init__(self, width, height, suffix: str, font: pygame.font.Font | None = None, name=''):
        super().__init__(width, height, name=name)

        # text box properties
        self.linkedValue: utils.Watchable | None = None
        self.linkedValueType = None
        self.text: str = ''
        self.temporaryText: str = ''
        self.inputRestrict = None
        self.stateRestrict = None
        self.font = font if font else base.SUBHEADING1
        self.suffix = suffix
        self.selected = False
        self.focus = None
        self.blurFocus = None

        def tempMouseClick():
            if callable(self.focus):
                self.focus()
            self.temporaryText = str(self.linkedValue.value) if (self.linkedValue and self.selected == False) else self.temporaryText
            self.selected = True
            self.redraw = True

        self.onMouseClick(tempMouseClick)
        self.onMouseClickOut(self.deselectAndFinalizeValue)
        self.onMouseEnter(lambda: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM))
        self.onMouseLeave(lambda: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW))

    def onFocus(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the text box is focused.
        '''

        self.focus = function 

    def onBlurFocus(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the text box is unfocused (finalized).
        '''

        self.blurFocus = function 
    
    def deselectAndFinalizeValue(self):
        '''
        Deselects the text box, and finalizes the value.
        If the state is valid (or no state restriction is set), completes.
        If not, reverts to previous valid state.
        '''
        if self.selected:
            self.selected = False
            if callable(self.stateRestrict) and self.stateRestrict(self.temporaryText): # field is valid
                self.text = self.temporaryText
            else: # field is invalid, don't update it
                None
            self.redraw = True
            
            if self.linkedValue:
                # console.warn(self.name)
                self.linkedValue.value = self.linkedValueType(self.text)
        
            if callable(self.blurFocus):
                self.blurFocus()

    def setInputRestrictions(self, restriction: list[str] | str):
        '''
        fields:
            restriction (list or string) - the restrictions on the field input.
        outputs: nothing

        Imposes restrictions on what character inputs the text field can take.
        By default, text box can take anything, restriction imposes limitations via a list or string.\n
        ### If restriction is a list, the field can only take characters in that list as input.
        ### If restriction is a string, it must be one of the following:
        - `'alphanumeric'`: 'a'-'z', '0'-'9'
        - `'alphabet'`: 'a'-'z'
        - `'numeric'`: '0'-'9'
        - `'decimal'`: '0'-'9', '-' and '.'
        '''
        if isinstance(restriction, str):
            if restriction == 'alphanumeric':
                self.inputRestrict = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','1','2','3','4','5','6','7','8','9','0']
            elif restriction == 'alphabet':
                self.inputRestrict = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
            elif restriction == 'numeric':
                self.inputRestrict = ['1','2','3','4','5','6','7','8','9','0']
            elif restriction == 'decimal':
                self.inputRestrict = ['1','2','3','4','5','6','7','8','9','0','.','-']
            else:
                raise ValueError('if restriction is a string, it must be "alphanumeric", "alphabet", "numeric", or "decimal".')
        elif isinstance(restriction, list):
            self.inputRestrict = restriction

    def setStateRestrictions(self, function):
        '''
        fields:
            function<string> (function or lambda) - function that defines whether or not the state is valid
        outputs: nothing

        Sets the internal state restrictions field, which determines what makes the field valid.
        '''
        self.stateRestrict = function
    
    def linkToValue(self, linkedValue: utils.Watchable ):
        '''
        Sets the Watchable value that the textbox is linked to. Two things are set:
        - list of watched values is updated (to add watchable to list of rerender deps)
        - linkedValue is set, which tells what the textbox should render
        '''
        self.watch(linkedValue, operation='add')
        self.linkedValue = linkedValue
        self.linkedValueType = type(linkedValue.value)

    def update(self, screen):
        super().update(screen)

        if self.selected:
            for event in events.get():
                if event.type == pygame.QUIT:
                    pygame.display.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.temporaryText = self.temporaryText[:-1]
                        self.redraw = True
                    elif event.key == pygame.K_RETURN:
                        self.deselectAndFinalizeValue()
                    else:
                        self.temporaryText += event.unicode if ((self.inputRestrict == None) or (event.unicode in self.inputRestrict)) else ""
                        self.redraw = True

        if self.redraw:
            dom.dirty(self)
    
    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        pygame.draw.rect(self.surface, COLOR_ALT_BG_4,
                         (0, 0, self.width, self.height), border_radius=3)
        if self.selected:
            pygame.draw.rect(self.surface, COLOR_BORDER_SELECTED,
                         (0, 0, self.width, self.height), width=1, border_radius=3)

        #pygame.draw.rect(screen, COLOR_BORDER_SELECTED if self.selected else COLOR_BORDER,
                         #(self.offsetX, self.offsetY, self.width, self.height), width=1, border_radius=3)

        stamp(self.surface, self.temporaryText if self.selected else str(self.linkedValue.value) + ' ' + self.suffix, self.font, self.width/2, self.height/2, COLOR_TEXT_ALT, justification="center")

        # then, blit this surface onto the passed surface
        super().render(screen, positioning)