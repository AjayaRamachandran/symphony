# events.py
# module for handling pygame events.
###### IMPORT ######

import pygame

###### INITIALIZE ######

_events = None
_transactionUpdate = False

###### FUNCTIONS ######

def pump():
    '''
    fields: none\n
    outputs: nothing

    Pumps the events and sets the transaction update flag to false.
    '''
    global _events, _transactionUpdate
    _events = pygame.event.get()
    _transactionUpdate = False

def get():
    '''
    fields: none\n
    outputs: list

    Returns the list of events.
    '''
    global _events
    return _events

def dirty():
    '''
    fields: none\n
    outputs: nothing

    Sets the transaction update flag to true.
    '''
    global _transactionUpdate
    _transactionUpdate = True

def getDirty():
    '''
    fields: none\n
    outputs: boolean
    
    Returns whether the transaction update flag is true.
    '''
    global _transactionUpdate
    if _transactionUpdate:
        _transactionUpdate = False
        return True
    return False