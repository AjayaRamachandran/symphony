# events.py
import pygame

_events = None

def pump():
    global _events
    _events = pygame.event.get()

def get():
    return _events