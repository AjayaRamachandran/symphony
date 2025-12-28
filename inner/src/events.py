# events.py
# module for handling pygame events.
###### IMPORT ######

import pygame

###### INITIALIZE ######

_events = None

###### FUNCTIONS ######

def pump():
    global _events
    _events = pygame.event.get()

def get():
    return _events