# gui/custom.py
# module for holding data for custom gui elements, bespoke interfaces.
###### IMPORT ######

import pygame
import time
import numpy as np
import cv2
from io import BytesIO
import copy

###### INTERNAL MODULES ######

from console_controls.console import *
import gui.element as gui
import gui.frame as frame

###### INITIALIZE ######

colors = [(235, 144, 74, 255),
        (184, 125, 227, 255),
        (108, 207, 198, 255),
        (154, 222, 138, 255),
        (106, 122, 214, 255),
        (214, 106, 155, 255)]

def getColorStates(width, height, source_path):
    rainbowImage = pygame.image.load(f"{source_path}/assets/rainbow.png")
    outputs = []
    for idx, color in enumerate(colors):
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(surf, color, (0, 0, width, height), border_radius=3)
        gui.stamp(surf, str(idx + 1), gui.SUBHEADING1, width/2, height/2, gui.BG_COLOR, justification='center')
        outputs.append(surf)
    
    gui.stamp(rainbowImage, '7', gui.SUBHEADING1, rainbowImage.get_width()/2, rainbowImage.get_height()/2, gui.BG_COLOR, justification='center')
    outputs.append(rainbowImage)
    return outputs

###### CLASSES ######

class NotePanel(frame.Panel):
    def __init__(self, pos, width, height):
        super().__init__((*pos, width, height), gui.BG_COLOR, [NoteGrid])

class NoteGrid(gui.Interactive):
    '''
    Class that holds a list of the visual notes on the screen, and their rendering state.
    '''
    def __init__(self, pos, width, height):
        super().__init__(pos, width, height)

class Note(gui.Interactive):
    '''
    Class to contain notes, which are interactive and rendered. Their data is also
    exposed as a dict when saving.
    '''
    def __init__(self, noteData: dict):
        super().__init__((0, 0), 10, 10)

        # note properties
        self.pitch = noteData.get('pitch', 1)
        self.time = noteData.get('time', 1)
        self.duration = noteData.get('duration', 1)
        self.dataFields = noteData.get('data_fields', {})

    def getData(self):
        return {
            "pitch" : self.pitch,
            "time" : self.time,
            "duration" : self.duration,
            "data_fields" : self.dataFields
        }
    
    def update(self, screen):
        super().update(screen)
        if self.redraw:
            self.render(screen)

    def render(self, screen: pygame.Surface):
        None