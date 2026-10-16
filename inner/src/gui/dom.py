# gui/dom.py
# module for handling document object model dirtying and damaging
###### IMPORT ######

from __future__ import annotations

from typing import TYPE_CHECKING

import copy
import pygame
from math import *
import random

###### INTERNAL MODULES ######

from console_controls.console import *
import sound.sound_processing as sp
import gui.element.base_element as gui
# `gui.frame` imports this module's dependency chain, so it is imported lazily
# inside the functions that need it to avoid a circular import at load time.
import gui.element as element
from utils.util import dedup
import events

###### INITIALIZE ######

DRAG_THRESHOLD = 2
LG_ROUND = 10
SM_ROUND = 2

Z_INDEX = 0

MASTER_PANEL = None
DIRTY_ELEMENTS: list[gui.Element] = []
DAMAGED_ELEMENTS: list[gui.Element] = []

def init(masterPanel: element.Panel):
    global MASTER_PANEL
    MASTER_PANEL = masterPanel

def setZOrderRecursively(curr: gui.Element):
    global Z_INDEX
    curr.z = Z_INDEX
    Z_INDEX += 1
    if isinstance(curr, element.Panel):
        for el in curr.elements:
            setZOrderRecursively(el)

def damageIntersectingRecursively(
    damageRects: list[pygame.Rect],
    currPanel: element.Panel,
    damager: gui.Element,
):
    '''
    fields:
        damageRects (list[pygame.Rect]) - the screen space rects to damage based on\n
        currPanel (element.Panel) - the currently tracked panel to make decisions on\n
        damager (gui.Element) - the element that is doing the damaging\n
    outputs: nothing

    Recursively damages every element that intersects the damage rects, regardless of z:
    lower elements reconstruct what was underneath, higher elements re-occlude.
    '''
    global DAMAGED_ELEMENTS

    for el in currPanel.elements:
        if el is damager:
            continue

        hits = [rect for rect in damageRects if rect.colliderect((el.x, el.y, el.width, el.height))]
        if hits:
            if el.domStatus != 'dirty':
                for rect in hits:
                    el.damage(rect)
            DAMAGED_ELEMENTS.append(el)

        if isinstance(el, element.Panel):
            damageIntersectingRecursively(damageRects, el, damager)

def dirty(el: gui.Element):
    global DIRTY_ELEMENTS
    DIRTY_ELEMENTS.append(el)

    el.dirty()
    currentRect = pygame.Rect(el.x, el.y, el.width, el.height)
    if el.paintedRect is None:
        damageRects = [currentRect]
    elif el.paintedRect.colliderect(currentRect):
        damageRects = [el.paintedRect.union(currentRect)]
    else:
        damageRects = [el.paintedRect, currentRect]
    damageIntersectingRecursively(damageRects, MASTER_PANEL, el)

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