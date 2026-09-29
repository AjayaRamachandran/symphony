# gui/frame.py
# module for handling gui element hierarchy and framing.
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
import events

###### INITIALIZE ######

DRAG_THRESHOLD = 2
LG_ROUND = 10
SM_ROUND = 2

class Panel(gui.Element):
    '''
    Rectangular component that can render as a surface and hold other components within it.
    Geometry, damage tracking, and dependency watching all come from Element.
    '''
    def __init__(self, elements: list[gui.Element], style: dict = {}, name: str = ""):
        super().__init__(1, 1, style, name)
        self.elements: list[gui.Element] = elements
        self.debug = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]

    def addElement(self, el: gui.Element):
        '''
        fields:
            el (gui.Element) - component to add to list
        
        Adds an element or panel to the list of objects stored within this panel.
        '''
        self.elements.append(el)

    def calculateDimensions(self, parentDimensions: list[int] | tuple[int]):
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
        validElements = [el for el in self.elements if isinstance(el, gui.Element)]
        for el in validElements:
            if isinstance(el, Panel):
                el.calculateDimensions(effectiveDimensions)

        flexedChildren = [el for el in validElements if el.display == "flex"]

        # CALCULATE THE WIDTH AND HEIGHT OF THE CURRENT ELEMENT, BASED ON THE CHILDREN
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

        for el in validElements:
            if not isinstance(el, Panel):
                el.calculateDimensions([self.width, self.height])

        # if the panel has no surface yet, or it does not match its new dimensions, (re)build it.
        self.rebuildSurface()

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
            elDisplay = el.style.get("display", "flex")
            elOffset = el.style.get("offset", [0, 0])
            if elDisplay == "flex":
                el.offsetX += elOffset[0]
                el.offsetY += elOffset[1]
            elif elDisplay == "absolute":
                el.offsetX, el.offsetY = elOffset[0], elOffset[1]

    def relativeToScreenSpace(self, runningOffset: list[int]):
        '''
        fields:
            runningOffset (list<int, int>) - screen-space origin of this element's content box
        outputs: nothing
        '''
        validElements = [el for el in self.elements if isinstance(el, gui.Element)]
        for el in validElements:
            if el.display == "fixed":
                fixedOffset = el.style.get("offset", [0, 0])
                el.x, el.y = fixedOffset[0], fixedOffset[1]
            else:
                el.x = runningOffset[0] + el.offsetX
                el.y = runningOffset[1] + el.offsetY

            if isinstance(el, Panel):
                el.relativeToScreenSpace([el.x, el.y])

    def update(self, screen):
        '''
        fields:
            screen (pygame.Surface) - surface this panel is being updated against
        outputs: nothing

        Informs all children to update (poll for changes), then polls this panel's own
        watched dependencies. Elements automatically queue themselves to render if there
        is need for it. ("self-awareness")

        Ex. hovering over a button should only make that button re-render with tint.
        '''
        for el in self.elements:
            el.update(screen)

        super().update(screen)

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        '''
        fields:
            screen (pygame.Surface) - surface to blit to\n
            positioning ('screen' | 'relative') - whether or not to render in screen space or relative space
        outputs: nothing

        Callable method to force render all sub-panels and elements of this panel.
        When a panel is rendered, it renders all internal elements into a surface that encapsulates their bounds, if they are a part of the flexbox.
        It then blits that surface to the provided screen.
        '''
        # SET DEFAULTS
        background = self.style.get("background", gui.COLOR_TRANSPARENT)
        border = self.style.get("border", 0)
        borderColor = self.style.get("border-color", gui.COLOR_BORDER)
        rounding = self.style.get("rounding", 0)
        effectiveBorder = None

        if isinstance(rounding, str):
            if rounding == "sm":
                roundingTR = SM_ROUND
                roundingBR = SM_ROUND
                roundingBL = SM_ROUND
                roundingTL = SM_ROUND
            elif rounding == "lg":
                roundingTR = LG_ROUND
                roundingBR = LG_ROUND
                roundingBL = LG_ROUND
                roundingTL = LG_ROUND
        elif isinstance(rounding, int):
            roundingTR = rounding
            roundingBR = rounding
            roundingBL = rounding
            roundingTL = rounding
        else:
            roundingTR = rounding[0]
            roundingBR = rounding[1]
            roundingBL = rounding[2]
            roundingTL = rounding[3]

        # self.surface.fill(background)
        pygame.draw.rect(self.surface, background, (0, 0, self.width, self.height),
                            border_top_right_radius=roundingTR,
                            border_bottom_right_radius=roundingBR,
                            border_bottom_left_radius=roundingBL,
                            border_top_left_radius=roundingTL
                            )

        if isinstance(border, list):
            if not (border[0] == border[1] == border[2] == border[3]):
                pygame.draw.line(self.surface, borderColor, (0, ceil(border[0]/2)), (self.width, ceil(border[0]/2)), border[0])
                pygame.draw.line(self.surface, borderColor, (self.width - ceil(border[1]/2), 0), (self.width - ceil(border[1]/2), self.height), border[1])
                pygame.draw.line(self.surface, borderColor, (self.width, self.height - ceil(border[2]/2)), (0, self.height - ceil(border[2]/2)), border[2])
                pygame.draw.line(self.surface, borderColor, (ceil(border[3]/2), self.height), (ceil(border[3]/2), 0), border[3])
            effectiveBorder = border[0]
        if effectiveBorder != None and effectiveBorder > 0:
            pygame.draw.rect(self.surface, borderColor, (ceil(effectiveBorder / 2), ceil(effectiveBorder / 2), self.width - ceil(effectiveBorder / 2), self.height - ceil(effectiveBorder / 2)), effectiveBorder,
                             border_top_right_radius=roundingTR,
                             border_bottom_right_radius=roundingBR,
                             border_bottom_left_radius=roundingBL,
                             border_top_left_radius=roundingTL
                             )

        for el in self.elements:
            el.render(self.surface, positioning='relative')

        self.blit(screen, positioning)


    def visualizeHierarchy(self, nestLevel = 0):
        prefix = ''
        for _i in range(nestLevel):
            prefix = prefix + '    '
        console.warn(prefix + f'<{self.__str__()} {self.style}>')
        for el in self.elements:
            if isinstance(el, Panel):
                el.visualizeHierarchy(nestLevel+1)
            elif isinstance(el, gui.Element):
                console.warn(prefix + '    ' + f'<{el.__str__()} />')
        console.warn(prefix + f'</{self.__str__()}>')