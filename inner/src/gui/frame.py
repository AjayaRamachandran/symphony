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
    
    def render(self, screen):
        '''
        fields: none\n
        outputs: nothing

        Callable method to force render all sub-panels and elements of this panel. This
        is to allow for remote coupling between elements ("remote control")

        Ex. updating the beats per measure requires the grid panel to re-render.
        '''
        mySurface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        mySurface.fill(self.bgColor)

        for element in self.elements:
            element.render(mySurface)

        screen.blit(mySurface, (self.x, self.y))
    


