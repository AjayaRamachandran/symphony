# utils/stack.py
# module for handling stack data structures.

###### IMPORT ######

import events

###### CLASSES ######

class Stack():
    '''
    Object to hold transaction stacks (undo/redo).
    '''
    def __init__(self, items=None):
        self.items = list(items) if (items != None) else []

    def push(self, value):
        '''
        fields:
            value (any) - value to add
        outputs: nothing

        Adds an item to the end/top of the stack.
        '''
        self.items.append(value)

    def pop(self):
        '''
        fields: none\n
        outputs: any

        Removes the end/top item and returns it.
        Returns None if the stack is empty.
        '''
        if len(self.items) == 0:
            return None
        return self.items.pop()

    def prepend(self, value):
        '''
        fields:
            value (any) - value to add
        outputs: nothing

        Adds an item to the start/bottom of the stack.
        '''
        self.items.insert(0, value)

    def snag(self):
        '''
        fields: none\n
        outputs: any

        Removes the start/bottom item and returns it.
        Returns None if the stack is empty.
        '''
        if len(self.items) == 0:
            return None
        return self.items.pop(0)

    def insert(self, idx, value):
        '''
        fields:
            idx (number) - index to insert at
            value (any) - value to insert
        outputs: nothing

        Inserts an item at a given index.
        '''
        self.items.insert(idx, value)

    def flush(self):
        '''
        fields: none\n
        outputs: nothing

        Deletes all elements.
        '''
        self.items = []

    def safeFlush(self):
        '''
        fields: none\n
        outputs: list

        Deletes all elements and returns them.
        '''
        old = self.items.copy()
        self.items = []
        return old

    def get(self, idx, default=None):
        '''
        fields:
            idx (number) - index to access
            default (any) - fallback value if index is invalid
        outputs: any

        Gets an element by index with optional default value.
        '''
        try:
            return self.items[idx]
        except IndexError:
            return default

    def getAll(self):
        '''
        fields: none\n
        outputs: list

        Returns all elements as a list copy.
        '''
        return self.items.copy()

    def indexOf(self, value):
        '''
        fields:
            value (any) - value to search for
        outputs: number

        Returns the first matching index, or -1 if not found.
        '''
        try:
            return self.items.index(value)
        except ValueError:
            return -1

    def tail(self, count=10):
        '''
        fields:
            count (number) - how many items to return from the end/top
        outputs: list

        Returns the end/top values as a list.
        '''
        if count <= 0:
            return []
        return self.items[-count:]

    def head(self, count=10):
        '''
        fields:
            count (number) - how many items to return from the start/bottom
        outputs: list

        Returns the start/bottom values as a list.
        '''
        if count <= 0:
            return []
        return self.items[:count]
