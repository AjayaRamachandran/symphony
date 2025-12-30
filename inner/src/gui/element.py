# gui/element.py
# module for handling gui element rendering and interactions.
###### IMPORT ######

import pygame
import numpy as np
from math import *
import cv2
from io import BytesIO

###### INTERNAL MODULES ######

from console_controls.console import *
import utils.sound_processing as sp
import events

###### INITIALIZE ######

source_path = 'inner/src'
DRAG_THRESHOLD = 2

GRID_BG_COLOR = (40, 40, 40, 255)
GRID_BG_COLOR_BEAT = (45, 45, 45, 255)
GRID_BG_COLOR_MEASURE = (55, 55, 55, 255)
GRID_LITROW_COLOR = (43, 43, 43, 255)
GRID_LITROW_COLOR_BEAT = (48, 48, 48, 255)
GRID_LITROW_COLOR_MEASURE = (62, 62, 62, 255)

ALT_BG_COLOR_3 = (36, 36, 36, 255) #242424ff
ALT_BG_COLOR_4 = (40, 40, 40, 255) #282828ff
BG_COLOR = (34, 34, 34, 255) #222222ff
ALT_BG_COLOR = (42, 42, 42, 255) #2a2a2aff
ALT_BG_COLOR_1 = (50, 50, 50, 255) #323232ff
ALT_BG_COLOR_2 = (60, 60, 60, 255) #3c3c3cff
BORDER_COLOR = (60, 60, 60, 255) #3c3c3cff
SELECTED_BORDER_COLOR = (197, 110, 201, 255) #c56ec9ff
NIMBIAL_ORANGE = (234, 123, 54, 255) #ea7b36ff
TEXT_COLOR = (217, 217, 217, 255) #d9d9d9ff
ALT_TEXT_COLOR = (115, 115, 115, 255) #737373ff
EMPTY_COLOR = (0, 0, 0, 0) #00000000

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
    BODY = pygame.font.Font(mainFont, 14)
    SUBSCRIPT1 = pygame.font.Font(mainFont, 11)

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

def stamp(screen, text, style, x, y, color:tuple=None, brightness:float=None, justification="left"):
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

def processImage(imageBytes):
    '''
    fields:
        imageBytes (buffer) - input image
    output: BytesIO object/buffer

    Takes in an image bytes and blurs it.
    '''
    image = cv2.imdecode(np.frombuffer(imageBytes, np.uint8), cv2.IMREAD_COLOR)
    blurredImage = cv2.GaussianBlur(image, (51, 51), 0) # apply a heavy blur to the image
    
    height, width = blurredImage.shape[:2]
    croppedImage = blurredImage[:, :300]
    
    _, buffer = cv2.imencode('.jpg', croppedImage) # encode the image to a BytesIO object
    imageIO = BytesIO(buffer)
    return imageIO

###### CLASSES ######

class Element():
    '''
    A generic GUI element. Contains no functionality.
    '''

    def __init__(self, pos, width, height):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.selected = False

    def setPosition(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def update(self, screen):
        return False
    
    def render(self, screen: pygame.Surface):
        None

class Interactive(Element):
    '''
    Class to contain clickable/draggable elements, which inherit an Element, adding clicking functionality.
    '''

    def __init__(self, pos, width, height):
        super().__init__(pos, width, height)

        # clickable properties
        self.mouseAlrDown = False

        self.onEnter = None
        self.onLeave = None
        self.onClick = None
        self.onClickOut = None
        self.onUnClick = None
        self.onDrag = None
        self.onScroll = None

        self.lastClickedPosition = None
        self.mouseInside = False
        self.mouseInsideLastFrame = False
        self.redraw = False

    def onMouseEnter(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is entered.
        '''

        self.onEnter = function

    def onMouseLeave(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the mouse exits the object.
        '''

        self.onLeave = function

    def onMouseClick(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is clicked.
        '''

        self.onClick = function

    def onMouseClickOut(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the mouse clicks outside the object.
        '''

        self.onClickOut = function

    def onMouseUnClick(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the mouse unclicks the object.
        '''

        self.onUnClick = function

    def onMouseDrag(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
                ^^^ takes exactly ONE argument: `tuple(value1, value2)`
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is dragged.
        '''

        self.onDrag = function

    def onHoverScroll(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
                ^^^ takes exactly ONE argument: `tuple(value1, value2)`
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is scrolled.
        '''

        self.onScroll = function

    def mouseEntered(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been entered
        '''

        self.isEntered = (not self.mouseInsideLastFrame) and (self.mouseInside)
        return self.isEntered

    def mouseLeft(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been left
        '''

        self.isLeft = (self.mouseInsideLastFrame) and (not self.mouseInside)
        return self.isLeft
    
    def mouseClicked(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the mouse has clicked the object
        '''

        self.isClick = (self.mouseInside) and pygame.mouse.get_pressed()[0] and not self.mouseAlrDown
        if self.isClick:
            self.mouseAlrDown = True
            self.lastClickedPosition = pygame.mouse.get_pos()
        return self.isClick
    
    def mouseClickedOut(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the mouse has clicked outside the object
        '''

        self.isOutClick = (not self.mouseInside) and pygame.mouse.get_pressed()[0] and not self.mouseAlrDown
        self.mouseAlrDown |= self.isOutClick
        return self.isOutClick
    
    def mouseUnClicked(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the mouse has unclicked the object (let go of clicking)
        '''

        self.isUnClick = (self.mouseInside) and (not pygame.mouse.get_pressed()[0]) and self.mouseAlrDown
        if self.isUnClick:
            self.mouseAlrDown = False
            self.lastClickedPosition = None
        return self.isUnClick
    
    def mouseDragged(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been dragged
        '''

        self.isDragged = self.mouseInside and pygame.mouse.get_pressed()[0] and self.mouseAlrDown
        self.isDragged = self.mouseAlrDown and pygame.mouse.get_pressed()[0] and \
           self.lastClickedPosition is not None and \
           dist(pygame.mouse.get_pos(), self.lastClickedPosition) > DRAG_THRESHOLD
        return ((pygame.mouse.get_pos()[0] - self.lastClickedPosition[0],
                 pygame.mouse.get_pos()[1] - self.lastClickedPosition[1]) if self.isDragged else False)
    
    def scrolled(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been scrolled within
        '''
        if not self.mouseInside:
            return False
        
        xy = [0, 0]

        for event in events.get():
            if event.type == pygame.QUIT:
                pygame.display.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    xy[1] += 10
                if event.key == pygame.K_DOWN:
                    xy[1] -= 10
                if event.key == pygame.K_LEFT:
                    xy[0] -= 10
                if event.key == pygame.K_RIGHT:
                    xy[0] += 10
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0: # Scroll up
                    xy[1] += 5
                if event.y < 0: # Scroll down
                    xy[1] -= 5
                if event.x > 0: # Scrub right
                    xy[0] += 5
                if event.x < 0: # Scrub left
                    xy[0] -= 5

        return False if xy == [0, 0] else xy

    def update(self, screen):
        '''
        fields: none\n
        outputs: nothing

        Updates the element on the screen (does not render it)
        '''
        self.mouseInside = mouseBounds((self.x, self.y, self.width, self.height))
        self.redraw = False

        if self.mouseEntered() and callable(self.onEnter):
            self.onEnter()
        if self.mouseLeft() and callable(self.onLeave):
            self.onLeave()
        if self.mouseClicked() and callable(self.onClick):
            self.onClick()
        if self.mouseClickedOut() and callable(self.onClickOut):
            self.onClickOut()
        if self.mouseUnClicked() and callable(self.onUnClick):
            self.onUnClick()

        xy = self.mouseDragged() # dragging is False if nothing happens, contains values if something did
        if callable(self.onDrag):
            if xy:
                self.onDrag(xy)

        xy = self.scrolled() # scrolling is False if nothing happens, contains values if something did
        if callable(self.onScroll):
            if xy:
                self.onScroll(xy)
        
        self.mouseInsideLastFrame = self.mouseInside
    
    def render(self, screen: pygame.Surface):
        None

class TextBox(Interactive):
    '''
    Class to contain text boxes, which inherit a clickable, storing text and adding editing, etc.
    '''
    def __init__(self, pos, width, height, text, font: pygame.font.Font=None):
        super().__init__(pos, width, height)

        # text box properties
        self.text = text
        self.temporaryText = text
        self.inputRestrict = None
        self.stateRestrict = None
        self.font = font if (font != None) else SUBHEADING1
        self.selected = False
        self.focus = None
        self.blurFocus = None

        def tempMouseClick():
            if callable(self.focus):
                self.focus()
            self.temporaryText = self.text if (self.selected == False) else self.temporaryText
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
            self.render(screen)
    
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
    
    def getText(self):
        return self.text
    
    def setText(self, text):
        self.text = str(text)
    
    def render(self, screen: pygame.Surface):
        pygame.draw.rect(screen, ALT_BG_COLOR_4,
                         (self.x, self.y, self.width, self.height), border_radius=3)
        if self.selected:
            pygame.draw.rect(screen, SELECTED_BORDER_COLOR,
                         (self.x, self.y, self.width, self.height), width=1, border_radius=3)

        #pygame.draw.rect(screen, SELECTED_BORDER_COLOR if self.selected else BORDER_COLOR,
                         #(self.x, self.y, self.width, self.height), width=1, border_radius=3)

        stamp(screen, self.temporaryText if self.selected else self.text, self.font, self.x + self.width/2, self.y + self.height/2, ALT_TEXT_COLOR, justification="center")

class Button(Interactive):
    '''
    Class to contain buttons, which inherit an interactive, having states and fully customizable function.
    '''
    def __init__(self, pos, width, height, states: list, font: pygame.font.Font=None):
        super().__init__(pos, width, height)

        # button properties
        self.states = states
        self.currentStateIdx = 0
        self.currentState = self.states[self.currentStateIdx]
        self.font = font if (font != None) else SUBHEADING1

        self.onMouseEnter(lambda: (setattr(self, "redraw", True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)))
        self.onMouseLeave(lambda: (setattr(self, "redraw", True), pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)))
        self.onMouseClick(lambda: (setattr(self, "redraw", True), self.cycleStates()))
        self.onMouseUnClick(lambda: (setattr(self, "redraw", True)))
    
    def update(self, screen):
        super().update(screen)
        if self.redraw:
            self.render(screen)

    def render(self, screen: pygame.Surface):
        pygame.draw.rect(screen, ALT_BG_COLOR_1 if self.mouseInside else ALT_BG_COLOR_4, (self.x, self.y, self.width, self.height), border_radius=3)
        if isinstance(self.currentState, pygame.Surface): # if it's an image (icon)
            loc = (self.x + self.width / 2 - self.currentState.get_width() / 2,
                   self.y + self.height / 2 - self.currentState.get_height() / 2)
            screen.blit(self.currentState, loc)
        else:
            stamp(screen, self.currentState, self.font, self.x + self.width/2, self.y + self.height/2, ALT_TEXT_COLOR, justification="center")

    def cycleStates(self):
        self.currentStateIdx = (self.currentStateIdx + 1) % len(self.states)
        self.currentState = self.states[self.currentStateIdx]
    
    def setCurrentState(self, idx):
        self.currentStateIdx = idx
        self.currentState = self.states[self.currentStateIdx]

class Dropdown(Interactive):
    '''
    Class to contain dropdowns, which inherit an interactive, having states and open/closed state.
    '''
    def __init__(self, pos, width, height, states: list, font: pygame.font.Font=None, image: pygame.Surface=None):
        super().__init__(pos, width, height)

        # button properties
        self.initHeight = height
        self.states = states
        self.currentStateIdx = 0
        self.currentState = self.states[self.currentStateIdx]
        self.font = font if (font != None) else SUBHEADING1
        self.image = image if (image != None) else pygame.Surface((16, 16), pygame.SRCALPHA)
        self.expanded = False

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
            if ((pygame.mouse.get_pos()[1] - self.y) // self.initHeight) - 1 == -1:
                self.handleClickOut() # if we select the top item (the placeholder), treat it like clicking out
            else:
                self.setCurrentState(((pygame.mouse.get_pos()[1] - self.y) // self.initHeight) - 1)
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
    
    def update(self, screen):
        super().update(screen)
        if self.redraw:
            self.render(screen)

    def render(self, screen: pygame.Surface):
        if not self.expanded:
            pygame.draw.rect(screen, ALT_BG_COLOR_1 if self.mouseInside else ALT_BG_COLOR_4, (self.x, self.y, self.width, self.height), border_radius=3)
            stamp(screen, self.currentState, self.font, self.x + self.width/2, self.y + self.height/2, ALT_TEXT_COLOR, justification="center")
        if self.expanded:
            pygame.draw.rect(screen, ALT_BG_COLOR_4, (self.x, self.y, self.width, self.height), border_radius=3)
            stamp(screen, self.currentState, self.font, self.x + self.width/2, self.y + self.initHeight/2, ALT_TEXT_COLOR, justification="center")
        
            # dropdown bg
            pygame.draw.rect(screen, ALT_BG_COLOR_4, (self.x, self.y + self.initHeight, self.width, self.height - self.initHeight), border_radius=3)
            # outline
            pygame.draw.rect(screen, BORDER_COLOR, (self.x, self.y + self.initHeight, self.width, self.height - self.initHeight), border_radius=3, width=1)
            # selected item highlight
            pygame.draw.rect(screen, ALT_BG_COLOR_1, (self.x, self.y + self.initHeight + (self.currentStateIdx * self.initHeight), self.width, self.initHeight), border_radius=3)
            for idx, state in enumerate(self.states):
                stamp(screen, state, self.font, self.x + self.width/2, self.y + self.initHeight/2 + ((idx + 1) * self.initHeight),
                      ALT_TEXT_COLOR, justification="center")

    def cycleStates(self):
        self.currentStateIdx = (self.currentStateIdx + 1) % len(self.states)
        self.currentState = self.states[self.currentStateIdx]
    
    def setCurrentState(self, idx):
        self.currentStateIdx = idx
        self.currentState = self.states[self.currentStateIdx]


class Scrollbar(Interactive):
    '''
    Class to contain scroll bars, which inherit an interactive, having interactive slidability.
    Need to define self.onMouseDrag to enable dragging functionality (specific to slider)
    '''
    def __init__(self, pos, width, height, maxWidth, orientation='horizontal'):
        super().__init__(pos, width, height)

        # scroll bar properties
        self.offset = []
        self.dragging = False
        self.maxWidth = maxWidth

        self.onMouseEnter(lambda: setattr(self, "redraw", True))
        self.onMouseLeave(lambda: setattr(self, "redraw", True))
        self.onMouseClick(lambda: (setattr(self, "redraw", True),
                                   self.setOffset(),
                                   setattr(self, "dragging", True)))
        
        self.onMouseUnClick(lambda: (setattr(self, "redraw", True),
                                     setattr(self, "dragging", False)))

    def setOffset(self):
        self.offset = [pygame.mouse.get_pos()[0] - self.x, pygame.mouse.get_pos()[1] - self.y]

    def update(self, screen):
        super().update(screen)