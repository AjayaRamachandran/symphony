# gui/frame.py
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
import gui.element as gui
import gui.vfx as vfx
import events

###### INITIALIZE ######

DRAG_THRESHOLD = 2

class Panel():
    '''
    Rectangular object that can render as a surface and hold elements within it. 
    '''
    def __init__(self, rect: list | tuple, bgColor, elements: list):
        self.x = rect[0]
        self.y = rect[1]
        self.width = rect[2]
        self.height = rect[3]
        self.bgColor = bgColor
        self.elements = elements

        self.selfRender = None

    def setRect(self, rect):
        self.x = rect[0]
        self.y = rect[1]
        self.width = rect[2]
        self.height = rect[3]
    
    def addElement(self, el):
        '''
        fields:
            el (gui.Element or Panel) - element to add to list
        
        Adds an element or panel to the list of objects stored within this panel.
        '''
        self.elements.append(el)

    def update(self, screen):
        '''
        fields: none\n
        outputs: nothing

        Informs all children of this element to update (poll for changes), elements will
        automatically rerender themselves if there is need for it. ("self-awareness")

        Ex. hovering over a button should only make that button re-render with tint.
        '''
        for element in self.elements:
            element.update(screen)
    
    def onSelfRender(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
                ^^^ takes exactly ONE argument: `pygame.Surface`
        outputs: nothing

        Takes in a function or lambda, and sets it internally as how to render the panel beneath its children.
        '''
        self.selfRender = function
        
    
    def render(self, screen: pygame.Surface, blurRadius: int = None):
        '''
        fields: screen (pygame.Surface) - surface to blit to\n
        outputs: nothing

        Callable method to force render all sub-panels and elements of this panel. This
        is to allow for remote coupling between elements ("remote control")

        ## Note
        When a panel is rendered, it renders all internal elements into a surface that is maximum size (size of window).
        It then crops the surface at the coordinate boundaries of the panel, then blits it to the provided screen.

        Ex. updating the beats per measure requires the grid panel to re-render.
        '''
        mySurface = pygame.Surface((pygame.display.get_window_size()), pygame.SRCALPHA)
        mySurface.fill(self.bgColor)

        if callable(self.selfRender):
            self.selfRender(mySurface)

        for element in self.elements:
            element.render(mySurface)

        if mySurface.get_rect() == pygame.rect.Rect(self.x, self.y, self.width, self.height):
            screen.blit(mySurface, (self.x, self.y))
        else:
            rect = pygame.Rect(self.x, self.y, self.width, self.height)
            rect = rect.clip(mySurface.get_rect())

            if rect.width > 0 and rect.height > 0:
                sub = mySurface.subsurface(rect)
                screen.blit(sub, (rect.x, rect.y))
        
        if blurRadius:
            screen.blit(vfx.surfaceBlur(screen, blurRadius=blurRadius), (0, 0))

        


