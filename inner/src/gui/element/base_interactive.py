# gui/element/base_interactive.py
# module for handling gui element rendering and interactions.
###### IMPORT ######

from __future__ import annotations

import pygame
from math import *

###### INTERNAL MODULES ######

from gui.element.base_element import Element, mouseBounds, DRAG_THRESHOLD

from console_controls.console import *
import events

###### CLASSES ######

class Interactive(Element):
    '''
    Class to contain clickable/draggable elements, which inherit an Element, adding clicking functionality.
    '''

    def __init__(self, width, height, name):
        super().__init__(width, height, name)

        # clickable properties
        self.mouseAlrDown = False

        self.onEnter = None
        self.onLeave = None
        self.onClick = None
        self.onClickOut = None
        self.onUnClick = None
        self.onDrag = None
        self.onUnDrag = None
        self.onScroll = None

        self.lastClickedPosition = None
        self.mouseInside = False
        self.mouseInsideLastFrame = False
        self.mousePressed = False
        self.mousePressedLastFrame = False
        self.mouseJustPressed = False
        self.mouseJustReleased = False
        self.mousePosition = (0, 0)
        self.wasDraggedSinceClick = False
        self.redraw = False

        self.name = name

    def _updateMouseState(self):
        '''
        fields: none\n
        outputs: nothing

        Captures mouse button state transitions for this frame.
        '''
        self.mousePosition = pygame.mouse.get_pos()
        self.mousePressed = bool(pygame.mouse.get_pressed()[0])
        self.mouseJustPressed = self.mousePressed and not self.mousePressedLastFrame
        self.mouseJustReleased = (not self.mousePressed) and self.mousePressedLastFrame

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

    def onMouseUnDrag(self, function):
        '''
        fields:
            function (function | lambda) - an action to do.
        outputs: nothing

        Takes in a function or lambda, and sets it internally as the action to do when the object is undragged.
        '''

        self.onUnDrag = function

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

        self.isClick = self.mouseInside and self.mouseJustPressed and not self.mouseAlrDown
        if self.isClick:
            self.mouseAlrDown = True
            self.lastClickedPosition = self.mousePosition
            self.wasDraggedSinceClick = False
        return self.isClick
    
    def mouseClickedOut(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the mouse has clicked outside the object
        '''

        self.isOutClick = (not self.mouseInside) and self.mouseJustPressed and not self.mouseAlrDown
        self.mouseAlrDown |= self.isOutClick
        return self.isOutClick
    
    def mouseUnClicked(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the mouse has unclicked the object (let go of clicking)
        '''

        didRelease = self.mouseAlrDown and self.mouseJustReleased
        self.isUnClick = self.mouseInside and didRelease
        if didRelease:
            self.mouseAlrDown = False
            self.lastClickedPosition = None
            self.wasDraggedSinceClick = False
        return self.isUnClick
    
    def mouseDragged(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been dragged
        '''

        self.isDragged = self.mouseAlrDown and self.mousePressed and self.lastClickedPosition is not None
        if not self.isDragged:
            return False

        delta = (
            self.mousePosition[0] - self.lastClickedPosition[0],
            self.mousePosition[1] - self.lastClickedPosition[1]
        )
        self.isDragged = dist(self.mousePosition, self.lastClickedPosition) > DRAG_THRESHOLD
        if self.isDragged:
            self.wasDraggedSinceClick = True
            return delta
        return False

    def mouseUnDragged(self):
        '''
        fields: none\n
        outputs: boolean

        Method to return whether the interactive element has been undragged
        '''

        self.isUnDragged = self.wasDraggedSinceClick and self.mouseJustReleased and self.mouseAlrDown
        return self.isUnDragged

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
        super().update(screen)

        self.mouseInside = mouseBounds((self.x, self.y, self.width, self.height))
        self._updateMouseState()
        self.redraw = False

        if self.mouseEntered() and callable(self.onEnter):
            self.onEnter()
        if self.mouseLeft() and callable(self.onLeave):
            self.onLeave()
        if self.mouseClicked() and callable(self.onClick):
            self.onClick()
        if self.mouseClickedOut() and callable(self.onClickOut):
            self.onClickOut()
        xy = self.mouseDragged() # dragging is False if nothing happens, contains values if something did
        if callable(self.onDrag):
            if xy:
                self.onDrag(xy)
        if callable(self.onUnDrag):
            if self.mouseUnDragged():
                self.onUnDrag()
        if self.mouseUnClicked() and callable(self.onUnClick):
            self.onUnClick()
        xy = self.scrolled() # scrolling is False if nothing happens, contains values if something did
        if callable(self.onScroll):
            if xy:
                self.onScroll(xy)
        
        self.mouseInsideLastFrame = self.mouseInside
        self.mousePressedLastFrame = self.mousePressed