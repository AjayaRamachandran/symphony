# values.py
# storage module to hold global values accessed by all files.
###### IMPORT ######

import time
import pygame

###### VARIABLES INITIALIZE ######

SAMPLE_RATE = 44100

play_obj = None # global to hold the last Channel/Sound so it doesn't get garbage-collected

width, height = (1100, 592)

page = "Editor"
noteMap = {}

tick = 0
tickInterval = 10

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT =  ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
noteCount = 128 # horizontal count of notes (beats) in the grid
noteRange = 72 # vertical count of notes (keys) in the grid
modesIntervals = [
    ["Lydian",        [0, 2, 4, 6, 7, 9, 11]],
    ["Ionian (maj.)", [0, 2, 4, 5, 7, 9, 11]],
    ["Mixolydian",    [0, 2, 4, 5, 7, 9, 10]],
    ["Dorian",        [0, 2, 3, 5, 7, 9, 10]],
    ["Aeolian (min.)",[0, 2, 3, 5, 7, 8, 10]],
    ["Phrygian",      [0, 1, 3, 5, 7, 8, 10]],
    ["Locrian",       [0, 1, 3, 5, 6, 8, 10]]
]
colors = {
    "orange" : (168, 136, 49),
    "purple" : (134, 48, 156),
    "cyan" : (20, 128, 150),
    "lime" : (102, 150, 20),
    "blue" : (61, 80, 156),
    "pink" : (168, 49, 94),
    "all" : (255, 255, 255)
}
colorsInd = {
    "orange" : 0,
    "purple" : 1,
    "cyan" : 2,
    "lime" : 3,
    "blue" : 4,
    "pink" : 5,
    "all" : 6
}
colorsList = colors.items()
justColors = [n[1] for n in colorsList]
justColorNames = [n[0] for n in colorsList]

waveTypes = ['square', 'triangle', 'sawtooth']

waveMap = {}
for index, color in enumerate(colorsList):
    waveMap[color[0]] = 0

accidentals = "flats"
head = False
playing = False
brushType = "brush"
worldMessage = ""

toolbarHeight = 80
leftColumn = 60
innerHeight = height - toolbarHeight
globalVolume = 0.3

viewRow = 50.01
viewColumn = 0.01
#console.log(innerHeight)
viewScaleX = (width - leftColumn) / 32 # old value = 32
viewScaleY = innerHeight // 32 # old value = 16
dRow = 0
dCol = 0
timeInterval = 4

notes = []
duplicatedNoteMap = {}
currentDraggingKey = 0
initialDraggingTime = 0

mouseTask = False
mouseDownTime = time.time()
mouseWOTask = True
mouseHoldStart = []
lastPlayTime = time.time()

timeOffset = 0
keyOffset = 0
oldKeyOffset = 0

saveFrame = 0

drawSelectBox = False

ticksPerTile = 10
globalTextBoxes = []

colorName = ""

pygame.font.init()

source_path = 'inner/src'
mainFont = f'{source_path}/assets/InterVariable.ttf'
TITLE1 = pygame.font.Font(mainFont, 60)
HEADING1 = pygame.font.Font(mainFont, 24)
SUBHEADING1 = pygame.font.Font(mainFont, 14)
BODY = pygame.font.Font(mainFont, 14)
SUBSCRIPT1 = pygame.font.Font(mainFont, 11)
screen = None


tempo = int(round(3600 / ticksPerTile))