# gui_pygame.py
# module for handling gui rendering and interactions.
###### IMPORT ######

import pygame
import time
import numpy as np
from math import *

###### INTERNAL MODULES ######

from console_controls.console import *
import utils.sound_processing as sp
import values as v

###### METHODS ######

def inBounds(coords1, coords2, point) -> bool:
    '''Returns whether a point is within the bounds of two other points. order is arbitrary.'''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def mouseFunction(rect):
    '''Function that returns (2 things) whether or not the mouse is in the bounding box, as well as a color.'''
    isInside = rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]
    return isInside, ((20, 20, 20) if isInside and pygame.mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

def stamp(text, style, x, y, luminance, justification = "left"):
    '''Function to draw text to the screen abstracted, makes text drawing easy.'''
    text = style.render(text, True, (round(luminance*255), round(luminance*255), round(luminance*255)))
    if justification == "left":
        textRect = (x, y, text.get_rect()[2], text.get_rect()[3])
    elif justification == "right":
        textRect = (x - text.get_rect()[2], y, text.get_rect()[2], text.get_rect()[3])
    else:
        textRect = (x - (text.get_rect()[2]/2), y - (text.get_rect()[3]/2), text.get_rect()[2], text.get_rect()[3])
    v.screen.blit(text, textRect)

###### CLASSES ######

class TextBox():
    '''Class to contain text boxes, which are used for interactivity.'''

    def __init__(self, pos, width, height, text, textSize = v.SUBHEADING1, endBarOffset=0):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.selected = False
        self.text = text
        self.endBarOffset = endBarOffset
        v.globalTextBoxes.append(self)

    def mouseClicked(self):
        '''Method to return whether the textbox has been clicked'''
        return mouseFunction((self.x, v.toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not v.mouseTask
    
    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, v.toolbarHeight/2 - 14, self.width, self.height))[0]

    def draw(self, text):
        '''Method to draw a textbox.'''
        pygame.draw.rect(v.screen, mouseFunction((self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        if self.selected:
            showBar = round(time.time())%2 == 0 #  + showBar*2.5 for xOffset
            stamp((text[:(-self.endBarOffset)] if self.endBarOffset != 0 else text) + ("|" if showBar else " ") + (text[-self.endBarOffset+1:] if self.endBarOffset != 0 else ''), self.textSize, self.x + self.width/2, self.y - showBar*1, 0.4, "center")
        else:
            stamp(text, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
        pygame.draw.rect(v.screen, (self.selected * 80, self.selected * 80, self.selected * 80), (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)

class Button():
    '''Class to contain buttons, which are used for interactivity.'''

    def __init__(self, pos, width, height, textSize = v.SUBHEADING1, color = (30, 30, 30), colorCycle = None):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.colorCycle = colorCycle
        self.color = colorCycle[0] if colorCycle != None else color
        self.colorIndex = 0

    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, v.toolbarHeight/2 - 14, self.width, self.height))[0]

    def mouseClicked(self):
        '''Method to return whether the button has been clicked'''
        return mouseFunction((self.x, v.toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not v.mouseTask
    
    def draw(self, itemToDraw = None, overrideDark = False):
        '''Method to draw a button.'''
        if self.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

        if self.colorCycle != None:
            pygame.draw.rect(v.screen, self.color, (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
            stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")
        else:
            pygame.draw.rect(v.screen, (25, 25, 25) if overrideDark else mouseFunction((self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        pygame.draw.rect(v.screen, (0, 0, 0), (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
    
        if self.colorCycle == None:
            if type(itemToDraw) == str:
                stamp(itemToDraw, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
            else:
                v.screen.blit(itemToDraw, (self.x + self.width/2 - 8, self.y - 8))
        else:
            if type(itemToDraw) == pygame.Surface:
                v.screen.blit(itemToDraw, (self.x + self.width/2 - 14, self.y - 14))
                pygame.draw.rect(v.screen, (0, 0, 0), (self.x, v.toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
                stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")

    def setColor(self, index):
        '''Sets to given color'''
        self.color = v.justColors[index]
        self.colorIndex = index

    def nextColor(self):
        '''Switches to next color (color switcher)'''
        nextIndex = (v.justColors.index(self.color) + 1) % (len(v.colors.items()))
        self.color = v.justColors[nextIndex]
        self.colorIndex = (self.colorIndex + 1) % 7

    def getColorName(self):
        '''Returns the color in string form of the Button (used for color switching)'''
        i = v.justColors.index(self.color)
        return v.justColorNames[i]

class Head():
    '''Class to contain the playhead, which plays the music.'''

    def __init__(self, speed:int, tick:int, home:int = 0):
        self.speed = speed
        self.tick = tick
        self.home = home # home is the time that the head returns to when restarted (default 0)

    def draw(self, screen, viewRow, viewColumn, leftColW, tileW, drawHead=False): # by default, only draws home
        '''Method to draw the playhead.'''
        if drawHead:
            top = [((((time.time() - v.lastPlayTime) * 60)/v.ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, v.toolbarHeight]
            bottom = [((((time.time() - v.lastPlayTime) * 60)/v.ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, v.height]

            pygame.draw.line(screen, (0, 255, 255), top, bottom, 1)

        if self.home != 0:
            top = [(self.home * tileW) - (viewColumn * tileW) + leftColW, v.toolbarHeight]
            bottom = [(self.home * tileW) - (viewColumn * tileW) + leftColW, v.height]

            pygame.draw.line(screen, (255, 255, 0), top, bottom, 1)

    def play(self):
        '''Method to play the playhead -- contains audio playback'''
        phases = {}
        finalWave = np.array([], dtype=np.int16)

        for tempTick in range(floor(self.home) + 1, v.noteCount):
            playingNotes = [
                (note.key, note.lead, note.color)
                for note in v.noteMap.values()
                if note.time == tempTick and (note.color == v.colorName or v.colorName == 'all')
            ]
            chunk, phases = sp.assembleNotes(playingNotes, phases, duration=v.ticksPerTile/60)
            finalWave = np.concatenate([finalWave, chunk])

        sound = sp.toSound(finalWave)
        v.play_obj = sound.play()

class Note():
    '''Class to contain the Note, which represents a grid element that *does* have a sound when played.'''

    def __init__(self, key:int, time:int, lead:bool, color:str = "orange"):
        self.key = key
        self.time = time
        self.lead = lead
        self.color = color
        self.originalKey = key
        self.originalTime = time
        self.selected = False
        self.extending = False
        self.SScoords = [0, 0]
    
    def __str__(self):
        '''String representation of Note'''
        return f'''Note object with attrs: [key: {self.key}, time: {self.time}, lead: {self.lead}, selected: {self.selected}, originalKey: {self.originalKey}, originalTime: {self.originalTime}]'''

    def setSScoords(self, x, y):
        '''Sets the screenspace coordinates of a note to the given arguments'''
        self.SScoords = [x, y]

    def draw(self, screen, viewRow, viewColumn, noteMap, transparent = False):
        '''Method to draw the note.'''

        opacity = 130
        def darkenColor(init, amt):
            return [init[n] - (amt * (n!=3)) for n in range(len(init))] # darkens a tuple by a constant n, if init is a quadtuple with opacity, alpha is untouched.
        if self.color == colorButton.getColorName() or colorButton.getColorName() == "all":
            leadColor = v.colors[self.color] if not transparent else (*v.colors[self.color], opacity)
            outlineColor = (255, 255, 255) if not transparent else (0, 0, 0, 0)
            tailsDarkness = 20
        else:
            leadColor = (80, 80, 80) if not transparent else (80, 80, 80, opacity)
            outlineColor = (255, 255, 255) if not transparent else (0, 0, 0, 0)
            tailsDarkness = 5
        tailColor = darkenColor(leadColor, tailsDarkness)
        black = (0, 0, 0) if not transparent else (0, 0, 0, 0)

        numToOffset = 0
        nextKeyNumToOffset = 0
        if v.colorName == 'all':
            colorsToSearch = v.justColorNames[:v.justColorNames.index(self.color)]
            for colorI in colorsToSearch:
                if (self.key, self.time, colorI) in noteMap:
                    numToOffset += 1
                if (self.key, self.time, colorI) in noteMap:
                    nextKeyNumToOffset += 1

        headerY = v.toolbarHeight + ((viewRow - self.key) * v.innerHeight/v.viewScaleY) - numToOffset * 3
        headerX = v.leftColumn + ((self.time - viewColumn - 1) * (v.width - v.leftColumn)/v.viewScaleX) - numToOffset * 3
        self.setSScoords(headerX + (v.width - v.leftColumn)/v.viewScaleX/2, headerY + v.innerHeight/v.viewScaleY/2)

        if self.lead:
            pygame.draw.rect(screen, leadColor,
                         (headerX - 1, headerY - 1, (v.width - v.leftColumn)/v.viewScaleX + 2, v.innerHeight/v.viewScaleY + 2), border_radius=3)
            pygame.draw.rect(screen, black,
                         (headerX - 1, headerY - 1, (v.width - v.leftColumn)/v.viewScaleX + 2, v.innerHeight/v.viewScaleY + 2), 1, 3)
            if self.selected:
                pygame.draw.line(screen, outlineColor, # top edge
                         (headerX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX + 1, headerY - 1), 2)
                pygame.draw.line(screen, outlineColor, # left edge
                         (headerX - 1, headerY - 1), (headerX - 1, headerY + v.innerHeight/v.viewScaleY - 1), 2)
                pygame.draw.line(screen, outlineColor, # bottom edge
                         (headerX - 1, headerY + v.innerHeight/v.viewScaleY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX + 1, headerY + v.innerHeight/v.viewScaleY - 1), 2)
                if not (self.key, self.time + 1, self.color) in noteMap:
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + v.innerHeight/v.viewScaleY - 1), 2)
        else:
            pygame.draw.rect(screen, tailColor,
                         (headerX - 1, headerY, (v.width - v.leftColumn)/v.viewScaleX + 1, v.innerHeight/v.viewScaleY))
            pygame.draw.line(screen, black, # top edge
                        (headerX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY - 1), 1)
            pygame.draw.line(screen, black, # bottom edge
                        (headerX - 1, headerY + floor(v.innerHeight/v.viewScaleY)), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY + floor(v.innerHeight/v.viewScaleY)), 1)
            if (self.key, self.time + 1, self.color) in noteMap and noteMap[(self.key, self.time + 1, self.color)].lead == False:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + v.innerHeight/v.viewScaleY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY + v.innerHeight/v.viewScaleY - 1), 2)
                if nextKeyNumToOffset < numToOffset:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY + v.innerHeight/v.viewScaleY - 1), 1)
            else:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX + 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + v.innerHeight/v.viewScaleY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + v.innerHeight/v.viewScaleY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX + 1, headerY + v.innerHeight/v.viewScaleY - 1), 2)
                else:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY - 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX - 1, headerY + v.innerHeight/v.viewScaleY - 1), 1)
        
        if self.extending:
            pygame.draw.line(screen, (0, 255, 0), # right edge
                            (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + 1), (headerX + (v.width - v.leftColumn)/v.viewScaleX, headerY + v.innerHeight/v.viewScaleY - 1), 2)
            

colorButton = Button(pos=(v.width - 345, 40), width=28, height=28, colorCycle=v.justColors)