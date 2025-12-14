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

###### INITIALIZE ######

def getColorStates(width, height, source_path):
    rainbowImage = pygame.image.load(f"{source_path}/assets/rainbow.png")
    colors = [(237, 144, 68, 255),
            (158, 86, 207, 255),
            (108, 207, 198, 255),
            (154, 222, 138, 255),
            (106, 122, 214, 255),
            (214, 106, 155, 255)]
    outputs = []
    for idx, color in enumerate(colors):
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        surf.fill(color)
        gui.stamp(surf, str(idx), gui.SUBHEADING1, width/2, height/2, gui.BG_COLOR, justification='center')
        outputs.append(surf)
    
    gui.stamp(rainbowImage, '7', gui.SUBHEADING1, rainbowImage.get_width()/2, rainbowImage.get_height()/2, gui.BG_COLOR, justification='center')
    outputs.append(rainbowImage)
    return outputs
