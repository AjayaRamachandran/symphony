from typing import Iterable, Callable, TypeVar, List
from pygame import Rect
import uuid

T = TypeVar('T')
K = TypeVar('K')

def dedup(iterable: Iterable[T], key: Callable[[T], K] = lambda x: x) -> List[T]:
    """
    fields:
        iterable (iterable) - Any iterable (list, tuple, generator, etc.)
        key (function) - Function to extract a comparison key from each element.
    outputs:
        List of unique elements in original order.

    Remove duplicates from an iterable while preserving order.
    Allows a `key` function to determine uniqueness.
    """
    seen = set()
    result = []
    for item in iterable:
        k = key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result

class Watchable():
    '''
    Master class to handle Watchable objects. Do not instantiate.
    '''
    def __init__(self):
        self.value = None
        self.watchId = None

    def set(self):
        None

class HeavyWatchable(Watchable):
    '''
    Class to manage watchable variables that are heavy.
    Any variables that need this behavior can inherit from this parent, and get light watchable behavior (via the `id` field).

    *Note*: not to be used with light watchables (ex. integers), where direct old/new comparison is simple enough.
    '''
    def __init__(self, initialValue):
        self.value = initialValue
        self.watchId = uuid.uuid4()

    def _change(self):
        '''
        Updates the internal id field to make heavy tracking available.
        '''
        self.watchId = uuid.uuid4()

    def set(self, newValue):
        '''
        Basic method for updating full value, exposed. Further update methods are defined in the children of this class.
        '''
        self.value = newValue
        self._change()

class LightWatchable(Watchable):
    '''
    Class to manage watchable variables that are light.
    This class exists to make it possible to pass references to variables without evaluating them.
    '''
    def __init__(self, initialValue):
        self.value = initialValue

    def set(self, newValue):
        self.value = newValue

    