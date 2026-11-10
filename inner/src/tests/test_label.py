##### test_label.py ######

# unit tests for Label text handling, including Watchable-backed text.
# run from inner/src: python -m unittest tests.test_label

###### IMPORT ######

import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
pygame.init()

import gui.element.base_element as base
from gui.element.label import Label
import utils.util as utils

###### TESTS ######

class TestLabel(unittest.TestCase):
    def setUp(self):
        if getattr(base, 'BODY', None) is None:
            base.BODY = pygame.font.Font(None, 16)

    def test_plain_string(self):
        label = Label(100, 20, text='hello')
        self.assertEqual(label.displayText(), 'hello')

    def test_watchable_text_resolves_value(self):
        message = utils.LightWatchable('')
        label = Label(100, 20, text=message)
        self.assertEqual(label.displayText(), '')
        message.value = 'Saved'
        self.assertEqual(label.displayText(), 'Saved')
        self.assertIn(message, label.watching)

    def test_render_with_watchable_does_not_raise(self):
        message = utils.LightWatchable('Saved project')
        label = Label(100, 20, text=message)
        label.render(pygame.Surface((200, 50)), positioning='relative')

    def test_none_value_renders_empty(self):
        label = Label(100, 20, text=utils.LightWatchable(None))
        self.assertEqual(label.displayText(), '')

if __name__ == '__main__':
    unittest.main()
