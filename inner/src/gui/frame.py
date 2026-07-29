# gui/frame.py
# module for handling gui element hierarchy and framing.
###### IMPORT ######

import copy
import pygame
from math import *
import random

###### INTERNAL MODULES ######

from console_controls.console import *
import sound.sound_processing as sp
import gui.element as gui
import events

###### INITIALIZE ######

DRAG_THRESHOLD = 2
LG_ROUND = 10
SM_ROUND = 2

class Panel():
    '''
    Rectangular object that can render as a surface and hold elements within it. 
    '''
    def __init__(self, elements: list[gui.Element], style: dict = {}, name: str = ""):
        self.style = style
        self.elements = elements
        self.name = name
        self.selfRender = None
        self.offsetX = 0
        self.offsetY = 0
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.debugBorder = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
    
    def __str__(self):
        return self.name
    
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
    
    # def onSelfRender(self, function):
    #     '''
    #     fields:
    #         function (function | lambda) - an action to do.
    #             ^^^ takes exactly ONE argument: `pygame.Surface`
    #     outputs: nothing

    #     Takes in a function or lambda, and sets it internally as how to render the panel beneath its children.
    #     '''
    #     self.selfRender = function

    def calculateDimensions(self, parentDimensions: list):
        '''
        fields:
            parentDimensions (list<int, int>) - width and height of the incoming parent el
        outputs: nothing

        Expresses all elements in a nested document object model in their true dimensions and
        relative offsets to their parents.
        '''
        # SET DEFAULTS
        display = self.style.get("display", "flex")
        # offset = self.style.get("offset", [0, 0])
        orient = self.style.get("orient", "row")
        align = self.style.get("align", "top")
        justify = self.style.get("justify", "left")
        sizing = self.style.get("sizing", ["fit", "fit"])
        padding = self.style.get("padding", 0)
        gap = self.style.get("gap", 0)

        self.display = display

        # SEPARATE DIMENSIONS
        if isinstance(padding, list):
            paddingT = padding[0]
            paddingR = padding[1]
            paddingB = padding[2]
            paddingL = padding[3]
        else:
            paddingT = padding
            paddingR = padding
            paddingB = padding
            paddingL = padding

        tempSizing = copy.copy(list(sizing))

        # parent fitting overpowers child fill
        for axis in (0, 1):
            if tempSizing[axis] == "fill" and parentDimensions[axis] == "fit":
                tempSizing[axis] = "fit"

        # RETRIEVE THE *DIMENSIONS* OF EVERY CHILD ELEMENT
        padX = paddingL + paddingR
        padY = paddingT + paddingB

        effectiveDimensions = [
            "fit" if tempSizing[0] == "fit" else max(0, (parentDimensions[0] if tempSizing[0] == "fill" else tempSizing[0]) - padX),
            "fit" if tempSizing[1] == "fit" else max(0, (parentDimensions[1] if tempSizing[1] == "fill" else tempSizing[1]) - padY),
        ]
        validElements = [el for el in self.elements if (isinstance(el, Panel) or isinstance(el, gui.Element))]
        for el in validElements:
            if isinstance(el, Panel):
                el.calculateDimensions(effectiveDimensions)

        flexedChildren = [el for el in validElements if getattr(el, "display", "flex") == "flex"]

        if tempSizing[0] == "fit":
            elementWidths = (el.width for el in flexedChildren)
            if orient == "row": # if row, then elements stacked horizontally
                self.width = paddingL + sum(elementWidths) + (gap * (len(flexedChildren) - 1)) + paddingR
            else:
                self.width = paddingL + max(elementWidths) + paddingR
        elif tempSizing[0] == "fill":
            self.width = parentDimensions[0]
        else:
            self.width = tempSizing[0]

        if tempSizing[1] == "fit":
            elementHeights = (el.height for el in flexedChildren)
            if orient == "col": # if col, then elements stacked vertically
                self.height = paddingT + sum(elementHeights) + (gap * (len(flexedChildren) - 1)) + paddingB
            else:
                self.height = paddingT + max(elementHeights) + paddingB
        elif tempSizing[1] == "fill":
            self.height = parentDimensions[1]
        else:
            self.height = tempSizing[1]

        # UPDATE THE *POSITIONS* OF EVERY CHILD ELEMENT
        contentWidth = self.width - paddingR - paddingL
        contentHeight = self.height - paddingB - paddingT

        if orient == "row":
            clusterWidth = sum(el.width for el in flexedChildren) + (gap * (len(flexedChildren) - 1))

            if tempSizing[0] == "fit" or justify in ["left", "spread"]:
                acc = paddingL            
            elif justify in ["center", "right"]:
                acc = paddingL + (contentWidth - clusterWidth) / 2 if justify == "center" else self.width - clusterWidth - paddingR
            for el in flexedChildren:
                el.offsetX = acc
                el.offsetY = paddingT if align == "top" else paddingT + (contentHeight - el.height) / 2 if align in ["center", "spread"] else self.height - el.height - paddingB
                acc += (el.width + gap)
                if justify == "spread":
                    acc += ((self.width - clusterWidth - paddingL - paddingR) / (len(flexedChildren) - 1))

        if orient == "col":
            clusterHeight = sum(el.height for el in flexedChildren) + (gap * (len(flexedChildren) - 1))

            if tempSizing[1] == "fit" or align in ["top", "spread"]:
                acc = paddingT
            elif align in ["center", "bottom"]:
                acc = paddingT + (contentHeight - clusterHeight) / 2 if align == "center" else self.height - clusterHeight - paddingB
            for el in flexedChildren:
                el.offsetX = paddingL if justify == "left" else paddingL + (contentWidth - el.width) / 2 if justify in ["center", "spread"] else self.width - el.width - paddingR
                el.offsetY = acc
                acc += (el.height + gap)
                if align == "spread":
                    acc += ((self.height - clusterHeight - paddingT - paddingB) / (len(flexedChildren) - 1))

        for el in validElements:
            elDisplay = el.style.get("display", "flex") if hasattr(el, "style") else "flex"
            elOffset = el.style.get("offset", [0, 0]) if hasattr(el, "style") else [0, 0]
            if elDisplay == "flex":
                el.offsetX += elOffset[0]
                el.offsetY += elOffset[1]
            elif elDisplay == "absolute":
                el.offsetX, el.offsetY = elOffset[0], elOffset[1]

    def relativeToScreenSpace(self, runningOffset: list):
        '''
        fields:
            runningOffset (list<int, int>) - screen-space origin of this element's content box
        outputs: nothing
        '''
        validElements = [el for el in self.elements if (isinstance(el, Panel) or isinstance(el, gui.Element))]
        for el in validElements:
            if getattr(el, "display", "flex") == "fixed":
                fixedOffset = el.style.get("offset", [0, 0]) if hasattr(el, "style") else [0, 0]
                el.x, el.y = fixedOffset[0], fixedOffset[1]
            else:
                el.x = runningOffset[0] + getattr(el, "offsetX", 0)
                el.y = runningOffset[1] + getattr(el, "offsetY", 0)

            if isinstance(el, Panel):
                el.relativeToScreenSpace([el.x, el.y])

    def render(self, screen: pygame.Surface):
        '''
        fields:
            screen (pygame.Surface) - surface to blit to
        outputs: nothing

        Callable method to force render all sub-panels and elements of this panel. This
        is to allow for remote coupling between elements ("tethering")

        ## Note
        When a panel is rendered, it renders all internal elements into a surface that is maximum size (size of window).
        It then crops the surface at the coordinate boundaries of the panel, then blits it to the provided screen.

        Ex. updating the beats per measure requires the grid panel to re-render.
        '''
        
        mySurface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        mySurface.fill(self.style.get('background', gui.EMPTY_COLOR))
        pygame.draw.rect(mySurface, self.debugBorder, (0, 0, self.width, self.height), 1)

        # if callable(self.selfRender):
        #     self.selfRender(mySurface)

        for el in self.elements:
            el.render(mySurface)

        screen.blit(mySurface, (self.offsetX, self.offsetY))

    def visualizeHierarchy(self, nestLevel = 0):
        prefix = ''
        for _i in range(nestLevel):
            prefix = prefix + '    '
        console.warn(prefix + f'<{self.__str__()}>')
        for el in self.elements:
            if isinstance(el, gui.Element):
                console.warn(prefix + '    ' + f'<{el.__str__()} />')
            elif isinstance(el, Panel):
                el.visualizeHierarchy(nestLevel+1)
        console.warn(prefix + f'</{self.__str__()}>')