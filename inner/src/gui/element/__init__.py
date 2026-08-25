# gui/element/__init__.py
# package that exposes the gui element classes and the shared element helpers.

import gui.element.base_element as base_element
from gui.element.base_element import Component, Element
from gui.element.base_interactive import Interactive
from gui.element.button import Button
from gui.element.dropdown import Dropdown
from gui.element.label import Label
from gui.element.textbox import TextBox

def __getattr__(name):
    '''
    Forwards any other attribute access (helpers, colors, and the fonts that are only
    populated once `init` runs) to `base_element`.
    '''
    return getattr(base_element, name)
