# gui/dom.py
# module for handling document object model dirtying and damaging
###### IMPORT ######

from __future__ import annotations

import copy
import pygame
from math import *
import random

###### INTERNAL MODULES ######

from console_controls.console import *
import sound.sound_processing as sp
import gui.element.base_element as gui
import gui.frame as frame
from utils.util import dedup
import events

###### INITIALIZE ######

DRAG_THRESHOLD = 2
LG_ROUND = 10
SM_ROUND = 2

Z_INDEX = 0

MASTER_PANEL = None
DIRTY_ELEMENTS: list[gui.Element | frame.Panel] = []
DAMAGED_ELEMENTS: list[gui.Element | frame.Panel] = []

def init(masterPanel: frame.Panel):
    global MASTER_PANEL
    MASTER_PANEL = masterPanel

def setZOrderRecursively(curr: frame.Panel | gui.Element):
    global Z_INDEX
    curr.z = Z_INDEX
    Z_INDEX += 1
    if isinstance(curr, frame.Panel):
        for el in curr.elements:
            setZOrderRecursively(el)

def damageClippingAbovePanelsRecursively(
    damageRect: pygame.Rect,
    currPanel: frame.Panel,
    damagerName: str,
    isAbove: bool,
):
    '''
    fields:
        damageRect (pygame.Rect) - the screen space rect to damage based on\n
        currPanel (frame.Panel) - the currently tracked panel to make decisions on\n
        damagerName (string) - the name of the element that is doing the damaging\n
        isAbove (boolean) - tracks whether we are above the damaging element\n
    outputs: track of whether we are above the damaging element after checks

    Recursively damages the elements that clip an element and sit above it in the DOM.
    '''
    global DAMAGED_ELEMENTS

    for el in currPanel.elements:
        # if we've already reached the damaged panel, damage any overlapping panels
        if isAbove and (isinstance(el, gui.Element) or isinstance(el, frame.Panel)):
            if damageRect.colliderect((el.x, el.y, el.width, el.height)):
                if el.domStatus != 'dirty':
                    el.damage(damageRect)
                DAMAGED_ELEMENTS.append(el)

        if isinstance(el, frame.Panel):
            isAbove = damageClippingAbovePanelsRecursively(
                damageRect,
                el,
                damagerName,
                isAbove,
            )

            # if this panel is the damager panel, everything after it is above
            if el.name == damagerName:
                isAbove = True

    return isAbove

def dirty(element: gui.Element | frame.Panel):
    global DIRTY_ELEMENTS
    DIRTY_ELEMENTS.append(element)

    # el = self._searchForElementRecursively(elementName, self.masterPanel)
    element.dirty()
    damageRect = pygame.Rect(element.x, element.y, element.width, element.height)
    damageClippingAbovePanelsRecursively(damageRect, MASTER_PANEL, element.name, False)

def flip(screen):
    '''
    Re-renders all the dirtied elements on the screen, and repairs the damage rectangles
    of elements above them.
    '''
    global DIRTY_ELEMENTS, DAMAGED_ELEMENTS
    sortedElements = sorted([*DIRTY_ELEMENTS, *DAMAGED_ELEMENTS], key=lambda x:x.z)
    # not needed (redundant), but we remove all instaces of elements that are both dirty and damaged (should be none)
    # this process prioritized the dirtiness of an element over its damagedness (good)
    uniqueElements = dedup(sortedElements, key=lambda x:x.name)
    
    for el in uniqueElements:
        if el.domStatus == 'dirty':
            el.render(screen, positioning='screen')
        elif el.domStatus == 'damaged':
            el.repair(screen)
        el.clean()

    DIRTY_ELEMENTS = []
    DAMAGED_ELEMENTS = []