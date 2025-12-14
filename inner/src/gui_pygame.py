# gui_pygame.py
# module for handling gui rendering and interactions.
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

###### METHODS ######

def inBounds(coords1, coords2, point) -> bool:
    '''Returns whether a point is within the bounds of two other points. order is arbitrary.'''
    return point[0] > min(coords1[0], coords2[0]) and point[1] > min(coords1[1], coords2[1]) and point[0] < max(coords1[0], coords2[0]) and point[1] < max(coords1[1], coords2[1])

def mouseFunction(rect):
    '''Function that returns (2 things) whether or not the mouse is in the bounding box, as well as a color.'''
    isInside = rect[0] < pygame.mouse.get_pos()[0] < rect[0] + rect[2] and rect[1] < pygame.mouse.get_pos()[1] < rect[1] + rect[3]
    return isInside, ((20, 20, 20) if isInside and pygame.mouse.get_pressed()[0] else ((30, 30, 30) if isInside else (35, 35, 35)))

def stamp(screen, text, style, x, y, luminance, justification = "left"):
    '''Function to draw text to the screen abstracted, makes text drawing easy.'''
    text = style.render(text, True, (round(luminance*255), round(luminance*255), round(luminance*255)))
    if justification == "left":
        textRect = (x, y, text.get_rect()[2], text.get_rect()[3])
    elif justification == "right":
        textRect = (x - text.get_rect()[2], y, text.get_rect()[2], text.get_rect()[3])
    else:
        textRect = (x - (text.get_rect()[2]/2), y - (text.get_rect()[3]/2), text.get_rect()[2], text.get_rect()[3])
    screen.blit(text, textRect)

def unselectTextBoxes(globalTextBoxes):
    '''
    fields: none
    outputs: nothing

    Loops through all text boxes and unselects them.
    '''
    for tb in globalTextBoxes:
        tb.selected = False

def processImage(imageBytes):
    '''
    fields:
        imageBytes (buffer) - input image
    output: BytesIO object/buffer

    Takes in an image bytes and blurs it.
    '''
    image = cv2.imdecode(np.frombuffer(imageBytes, np.uint8), cv2.IMREAD_COLOR)
    blurredImage = cv2.GaussianBlur(image, (51, 51), 0) # apply a heavy blur to the image
    
    height, width = blurredImage.shape[:2]
    croppedImage = blurredImage[:, :300]
    
    _, buffer = cv2.imencode('.jpg', croppedImage) # encode the image to a BytesIO object
    imageIO = BytesIO(buffer)
    return imageIO

def renderScrollBar():
    '''
    fields: none
    outputs: nothing

    Function to draw the bottom scroll bar on the screen for navigating horizontally.
    '''
    scrollBarHeight = 15
    scrollBarColor = (100, 100, 100)
    progressLeft = viewColumn / noteCount
    progressRight = (viewColumn + viewScaleX) / noteCount
    mouseDel = pygame.mouse.get_rel()[0]/(width - leftColumn) * noteCount

    if pygame.mouse.get_pos()[1] > height - 80:
        if ((width - leftColumn) * progressLeft) + leftColumn < pygame.mouse.get_pos()[0] < ((width - leftColumn) * progressRight) + leftColumn and pygame.mouse.get_pos()[1] > height - scrollBarHeight - 15:
            # mouse is touching scroll bar
            if pygame.mouse.get_pressed()[0]:
                # mouse is dragging scroll bar
                scrollBarColor = (255, 255, 255)
                if not mouseTask:
                    viewColumn += mouseDel
            else:
                scrollBarColor = (150, 150, 150)
        else:
            # mouse is close to screen bottom
            scrollBarColor = (100, 100, 100)
    else:
        scrollBarHeight = 10

    pygame.draw.rect(screen, scrollBarColor, (((width - leftColumn) * progressLeft) + leftColumn,
                                                height - scrollBarHeight - 3,
                                                (width - leftColumn) * (progressRight - progressLeft),
                                                scrollBarHeight), 1, 3)

def renderToolBar():
    '''
    fields: none
    outputs: nothing

    Renders the top toolbar, and all of the elements inside of it.
    '''
    pygame.draw.rect(screen, (43, 43, 43), (0, 0, width, toolbarHeight))
    pygame.draw.line(screen, (0, 0, 0), (0, toolbarHeight), (width, toolbarHeight))
    pygame.draw.line(screen, (30, 30, 30), (0, toolbarHeight - 1), (width, toolbarHeight - 1))
    pygame.draw.line(screen, (49, 49, 49), (0, toolbarHeight - 2), (width, toolbarHeight - 2))
    pygame.draw.line(screen, (45, 45, 45), (0, toolbarHeight - 3), (width, toolbarHeight - 3))

    ### TRACK TITLE BAR
    if (width >= 1100):
        pygame.draw.rect(screen, (0, 0, 0), (475, toolbarHeight/2 - 14, width - 950, 28), 1, 3)
        if len(titleText) < (width - 950) / 10:
            stamp(titleText, SUBHEADING1, width/2, 40, 0.4, "center")
        else:
            stamp(titleText[:int((width - 950) / 10)] + '...', SUBHEADING1, width/2, 40, 0.4, "center")
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    ### PLAY/PAUSE BUTTON
    playPauseButton.x = 33
    if playPauseButton.mouseClicked():
        playing = not playing
        if playing:
            playHead.play()
            lastPlayTime = time.time()
        else:
            play_obj.stop()
        mouseTask = True
        playHead.tick = playHead.home
    playPauseButton.draw(pauseImage if playing else playImage)

    ### ACCIDENTALS BUTTON
    accidentalsButton.x = 120
    if accidentalsButton.mouseClicked():
        keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
        key = (NOTES_FLAT if accidentals == "sharps" else NOTES_SHARP)[keyIndex]
        accidentals = ("sharps" if accidentals == "flats" else "flats")
        mouseTask = True
    accidentalsButton.draw(accidentals)
    
    ### PLAYHEAD BUTTON
    playheadButton.x = 207
    if playheadButton.mouseClicked():
        head = not head
        mouseTask = True
    if head:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        playheadButton.draw(headImage, overrideDark=True)
    else:
        playheadButton.draw(headImage)

    ### COLOR BUTTON
    colorButton.x = width - 345
    if colorButton.mouseClicked():
        colorButton.nextColor()
        mouseTask = True
    if colorButton.getColorName() == "all":
        colorButton.draw(rainbowImage)
    else:
        colorButton.draw()

    ### WAVE BUTTON
    waveButton.x = width - 317
    if waveButton.mouseClicked():
        waveMap[colorName] = (waveMap[colorName] + 1) % len(waveTypes)
        mouseTask = True
    if colorName != 'all': # doesn't render the wave type for 'all' since it is irrelevant
        waveButton.draw(waveImages[waveMap[colorName]])

    ### KEY BUTTON
    keyButton.x = width - 260
    if keyButton.mouseClicked():
        keyIndex = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT).index(key)
        key = (NOTES_SHARP if accidentals == "sharps" else NOTES_FLAT)[keyIndex + 1 if keyIndex != 11 else 0]
        keyIndex = keyIndex + 1 if keyIndex != 11 else 0
        mouseTask = True
    keyButton.draw(key)

    ### MODE BUTTON
    modeButton.x = width - 220
    if modeButton.mouseClicked():
        modeIndex = next(i for i, (x, _) in enumerate(modesIntervals) if x == mode)
        mode = modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][0]
        modeIntervals = set(modesIntervals[modeIndex + 1 if modeIndex != 6 else 0][1])
        mouseTask = True
    modeButton.draw(mode)

    ### BRUSH/ERASER/NEGATER BUTTON
    brushButton.x = width - 93
    if brushButton.mouseClicked():
        if brushType == "brush":
            brushType = "eraser"
        elif brushType == "eraser":
            brushType = "select"
        else:
            brushType = "brush"
            for note in noteMap.items():
                note[1].selected = False
        mouseTask = True
    brushButton.draw("select" if brushType == "select" else brushImage if brushType == "brush" else eraserImage)

    ### TIME SIGNATURE CONTROLS
    timeSigUpButton.x = width - 395
    timeSigUpButton.draw(upChevronImage)
    if timeSigUpButton.mouseClicked():
        timeInterval += 1
        mouseTask = True
    timeSigTextBox.x = width - 425
    if timeSigTextBox.mouseBounds():
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
    if timeSigTextBox.mouseClicked():
        if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
            unselectTextBoxes()
        timeSigTextBox.selected = True
    timeSigTextBox.draw(str(timeSigTextBox.text))
    if timeSigTextBox.selected:
        timeInterval = 1 if (timeSigTextBox.text == '' or int(timeSigTextBox.text) == 0) else int(timeSigTextBox.text)
    else:
        timeSigTextBox.text = str(timeInterval)

    timeSigDownButton.x = width - 445
    timeSigDownButton.draw(downChevronImage)
    if timeSigDownButton.mouseClicked():
        timeInterval = max(1, timeInterval - 1)
        mouseTask = True

    ### TEMPO CONTROLS
    tempoUpButton.x = 425
    tempoUpButton.draw(upChevronImage)
    if tempoUpButton.mouseClicked():
        tempo += 1
        mouseTask = True

    tempoTextBox.x = 320
    if tempoTextBox.mouseBounds():
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
    if tempoTextBox.mouseClicked():
        if not pygame.key.get_pressed()[pygame.K_LSHIFT]:
            unselectTextBoxes()
        tempoTextBox.text = ''
        tempoTextBox.selected = True
    if tempoTextBox.selected:
        ticksPerTile = 3600 / tempo
        tempo = 1 if (tempoTextBox.text == '' or int(tempoTextBox.text) == 0) else int(tempoTextBox.text)
    else:
        tempoTextBox.text = str(tempo)
    tempoTextBox.draw(str(tempoTextBox.text) + ' tpm')

    tempoDownButton.x = 300
    tempoDownButton.draw(downChevronImage)
    if tempoDownButton.mouseClicked():
        tempo = max(1, tempo - 1)
        mouseTask = True

###### CLASSES ######

class TextBox():
    '''Class to contain text boxes, which are used for interactivity.'''

    def __init__(self, pos, width, height, text, textSize = SUBHEADING1, endBarOffset=0):
        self.x = pos[0]
        self.y = pos[1]
        self.width = width
        self.height = height
        self.textSize = textSize
        self.selected = False
        self.text = text
        self.endBarOffset = endBarOffset
        globalTextBoxes.append(self)

    def mouseClicked(self):
        '''Method to return whether the textbox has been clicked'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not mouseTask
    
    def mouseBounds(self):
        '''Returns whether the mouse is in the bounds of the textbox'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0]

    def draw(self, text):
        '''Method to draw a textbox.'''
        pygame.draw.rect(screen, mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        if self.selected:
            showBar = round(time.time())%2 == 0 #  + showBar*2.5 for xOffset
            stamp((text[:(-self.endBarOffset)] if self.endBarOffset != 0 else text) + ("|" if showBar else " ") + (text[-self.endBarOffset+1:] if self.endBarOffset != 0 else ''), self.textSize, self.x + self.width/2, self.y - showBar*1, 0.4, "center")
        else:
            stamp(text, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
        pygame.draw.rect(screen, (self.selected * 80, self.selected * 80, self.selected * 80), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)

class Button():
    '''Class to contain buttons, which are used for interactivity.'''

    def __init__(self, pos, width, height, textSize = SUBHEADING1, color = (30, 30, 30), colorCycle = None):
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
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0]

    def mouseClicked(self):
        '''Method to return whether the button has been clicked'''
        return mouseFunction((self.x, toolbarHeight/2 - 14, self.width, self.height))[0] and pygame.mouse.get_pressed()[0] and not mouseTask
    
    def draw(self, itemToDraw = None, overrideDark = False):
        '''Method to draw a button.'''
        if self.mouseBounds():
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

        if self.colorCycle != None:
            pygame.draw.rect(screen, self.color, (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
            stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")
        else:
            pygame.draw.rect(screen, (25, 25, 25) if overrideDark else mouseFunction((self.x, toolbarHeight/2 - self.height/2, self.width, self.height))[1], (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
    
        if self.colorCycle == None:
            if type(itemToDraw) == str:
                stamp(itemToDraw, self.textSize, self.x + self.width/2, self.y, 0.4, "center")
            else:
                screen.blit(itemToDraw, (self.x + self.width/2 - 8, self.y - 8))
        else:
            if type(itemToDraw) == pygame.Surface:
                screen.blit(itemToDraw, (self.x + self.width/2 - 14, self.y - 14))
                pygame.draw.rect(screen, (0, 0, 0), (self.x, toolbarHeight/2 - self.height/2, self.width, self.height), 1, 3)
                stamp(str(self.colorIndex + 1), self.textSize, self.x + self.width/2, self.y, 0.1, "center")

    def setColor(self, index):
        '''Sets to given color'''
        self.color = justColors[index]
        self.colorIndex = index

    def nextColor(self):
        '''Switches to next color (color switcher)'''
        nextIndex = (justColors.index(self.color) + 1) % (len(colors.items()))
        self.color = justColors[nextIndex]
        self.colorIndex = (self.colorIndex + 1) % 7

    def getColorName(self):
        '''Returns the color in string form of the Button (used for color switching)'''
        i = justColors.index(self.color)
        return justColorNames[i]

class Head():
    '''Class to contain the playhead, which plays the music.'''

    def __init__(self, speed:int, tick:int, home:int = 0):
        self.speed = speed
        self.tick = tick
        self.home = home # home is the time that the head returns to when restarted (default 0)

    def draw(self, screen, viewRow, viewColumn, leftColW, tileW, drawHead=False): # by default, only draws home
        '''Method to draw the playhead.'''
        if drawHead:
            top = [((((time.time() - lastPlayTime) * 60)/ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [((((time.time() - lastPlayTime) * 60)/ticksPerTile + self.home) * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (0, 255, 255), top, bottom, 1)

        if self.home != 0:
            top = [(self.home * tileW) - (viewColumn * tileW) + leftColW, toolbarHeight]
            bottom = [(self.home * tileW) - (viewColumn * tileW) + leftColW, height]

            pygame.draw.line(screen, (255, 255, 0), top, bottom, 1)

    def play(self, ps : dict):
        '''
        Method to play the playhead -- contains audio playback
        '''

        phases = {}
        finalWave = np.array([], dtype=np.int16)

        for tempTick in range(floor(self.home) + 1, noteCount):
            playingNotes = [
                (note.key, note.lead, note.color)
                for note in ps["noteMap"].values()
                if note.time == tempTick and (note.color == colorName or colorName == 'all')
            ]
            chunk, phases = sp.assembleNotes(playingNotes, phases, ps["waveMap"], duration=ps["ticksPerTile"]/60)
            finalWave = np.concatenate([finalWave, chunk])

        sound = sp.toSound(finalWave)
        play_obj = sound.play()

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
            leadColor = colors[self.color] if not transparent else (*colors[self.color], opacity)
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
        if colorName == 'all':
            colorsToSearch = justColorNames[:justColorNames.index(self.color)]
            for colorI in colorsToSearch:
                if (self.key, self.time, colorI) in noteMap:
                    numToOffset += 1
                if (self.key, self.time, colorI) in noteMap:
                    nextKeyNumToOffset += 1

        headerY = toolbarHeight + ((viewRow - self.key) * innerHeight/viewScaleY) - numToOffset * 3
        headerX = leftColumn + ((self.time - viewColumn - 1) * (width - leftColumn)/viewScaleX) - numToOffset * 3
        self.setSScoords(headerX + (width - leftColumn)/viewScaleX/2, headerY + innerHeight/viewScaleY/2)

        if self.lead:
            pygame.draw.rect(screen, leadColor,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), border_radius=3)
            pygame.draw.rect(screen, black,
                         (headerX - 1, headerY - 1, (width - leftColumn)/viewScaleX + 2, innerHeight/viewScaleY + 2), 1, 3)
            if self.selected:
                pygame.draw.line(screen, outlineColor, # top edge
                         (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                pygame.draw.line(screen, outlineColor, # left edge
                         (headerX - 1, headerY - 1), (headerX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                pygame.draw.line(screen, outlineColor, # bottom edge
                         (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                if not (self.key, self.time + 1, self.color) in noteMap:
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
        else:
            pygame.draw.rect(screen, tailColor,
                         (headerX - 1, headerY, (width - leftColumn)/viewScaleX + 1, innerHeight/viewScaleY))
            pygame.draw.line(screen, black, # top edge
                        (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 1)
            pygame.draw.line(screen, black, # bottom edge
                        (headerX - 1, headerY + floor(innerHeight/viewScaleY)), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + floor(innerHeight/viewScaleY)), 1)
            if (self.key, self.time + 1, self.color) in noteMap and noteMap[(self.key, self.time + 1, self.color)].lead == False:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 2)
                if nextKeyNumToOffset < numToOffset:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
            else:
                if self.selected:
                    pygame.draw.line(screen, outlineColor, # top edge
                            (headerX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)
                    pygame.draw.line(screen, outlineColor, # bottom edge
                            (headerX - 1, headerY + innerHeight/viewScaleY - 1), (headerX + (width - leftColumn)/viewScaleX + 1, headerY + innerHeight/viewScaleY - 1), 2)
                else:
                    pygame.draw.line(screen, black, # right edge
                        (headerX + (width - leftColumn)/viewScaleX - 1, headerY - 1), (headerX + (width - leftColumn)/viewScaleX - 1, headerY + innerHeight/viewScaleY - 1), 1)
        
        if self.extending:
            pygame.draw.line(screen, (0, 255, 0), # right edge
                            (headerX + (width - leftColumn)/viewScaleX, headerY + 1), (headerX + (width - leftColumn)/viewScaleX, headerY + innerHeight/viewScaleY - 1), 2)