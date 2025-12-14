# gui/element.py
# module for handling gui element rendering and interactions.
###### IMPORT ######

import pygame
import time
import numpy as np
from math import *
import cv2
from io import BytesIO

###### INTERNAL MODULES ######

from console_controls.console import *
import utils.sound_processing as sp

###### INITIALIZE ######

source_path = 'inner/src'
DRAG_THRESHOLD = 2

BG_COLOR = (34, 34, 34, 255) #1c1c1cff
HOVERED_BG_COLOR = (40, 40, 40, 255) #282828ff
PRESSED_BG_COLOR = (24, 24, 24, 255) #181818ff
BORDER_COLOR = (60, 60, 60, 255) #3c3c3cff
SELECTED_BORDER_COLOR = (197, 110, 201, 255) #c56ec9ff
NIMBIAL_ORANGE = (234, 123, 54, 255) #ea7b36ff
TEXT_COLOR = (217, 217, 217, 255) #d9d9d9ff
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
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is dragged.
        '''

        self.onDrag = function

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
        return self.isDragged

    def update(self, screen):
        '''
        fields: none\n
        outputs: nothing

        Updates the element on the screen (does not render it)
        '''
        self.mouseInside = mouseBounds((self.x, self.y, self.width, self.height))
        self.redraw = False

        if self.mouseEntered() and (self.onEnter != None):
            self.onEnter()
        if self.mouseLeft() and (self.onLeave != None):
            self.onLeave()
        if self.mouseClicked() and (self.onClick != None):
            self.onClick()
        if self.mouseDragged() and (self.onDrag != None):
            self.onDrag()
        if self.mouseClickedOut() and (self.onClickOut != None):
            self.onClickOut()
        if self.mouseUnClicked() and (self.onUnClick != None):
            self.onUnClick()
        
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
        self.textRestrict = None
        self.font = font if (font != None) else SUBHEADING1
        self.selected = False

        self.onMouseClick(lambda: (setattr(self, "selected", True), setattr(self, "redraw", True)))
        self.onMouseClickOut(lambda: (setattr(self, "selected", False), setattr(self, "redraw", True)))
    
    def update(self, screen):
        super().update(screen)

        if self.selected:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.text = self.text[:-1]
                        self.redraw = True
                    elif event.key == pygame.K_RETURN:
                        self.selected = False
                        self.redraw = True
                    else:
                        self.text += event.unicode if (self.textRestrict == None) or (event.unicode in self.textRestrict) else ""
                        self.redraw = True
        
        if self.redraw:
            self.render(screen)

    def setTextRestrictions(self, restriction: list):
        self.textRestrict = restriction
    
    def getText(self):
        return self.text
    
    def render(self, screen: pygame.Surface):
        pygame.draw.rect(screen, BG_COLOR,
                         (self.x, self.y, self.width, self.height), border_radius=3)
        pygame.draw.rect(screen, SELECTED_BORDER_COLOR if self.selected else BORDER_COLOR,
                         (self.x, self.y, self.width, self.height), width=1, border_radius=3)

        stamp(screen, self.text, self.font, self.x + self.width/2, self.y + self.height/2, TEXT_COLOR, justification="center")

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

        self.onMouseEnter(lambda: (setattr(self, "redraw", True)))
        self.onMouseLeave(lambda: (setattr(self, "redraw", True)))
        self.onMouseClick(lambda: (setattr(self, "redraw", True), self.cycleStates()))
        self.onMouseUnClick(lambda: (setattr(self, "redraw", True)))
    
    def update(self, screen):
        super().update(screen)
        if self.redraw:
            self.render(screen)

    def render(self, screen: pygame.Surface):
        pygame.draw.rect(screen, HOVERED_BG_COLOR if self.mouseInside else BG_COLOR, (self.x, self.y, self.width, self.height), border_radius=3)
        if isinstance(self.currentState, pygame.Surface): # if it's an image (icon)
            loc = (self.x + self.width / 2 - self.currentState.get_width() / 2,
                   self.y + self.height / 2 - self.currentState.get_height() / 2)
            screen.blit(self.currentState, loc)
        else:
            stamp(screen, self.currentState, self.font, self.x + self.width/2, self.y + self.height/2, TEXT_COLOR, justification="center")

    def cycleStates(self):
        self.currentStateIdx = (self.currentStateIdx + 1) % len(self.states)
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