##### test_tooltips.py ######

# unit tests for Label hover hints, the Interactive tooltip hook, and the save message.
# run from inner/src: python -m unittest discover -s tests -p "test_tooltips.py" -t tests

###### IMPORT ######

import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
pygame.init()

import events
import gui.element.base_element as base
import gui.element.base_interactive as base_interactive
from gui.element.base_interactive import Interactive
from gui.element.label import Label
import utils.file_io as fio
import utils.state_loading as sl

if getattr(base, 'BODY', None) is None:
    base.BODY = pygame.font.Font(None, 16)

###### HELPERS ######

def hover(element, inside: bool):
    '''Runs one update frame with the mouse inside/outside the element.'''
    events.pump()
    with mock.patch.object(base_interactive, 'mouseBounds', return_value=inside):
        element.update(None)

###### TESTS ######

class TestLabelHints(unittest.TestCase):
    def setUp(self):
        self.label = Label(100, 20, text='Last saved')

    def test_own_text_shows_when_not_hovering(self):
        self.assertEqual(self.label.displayText(), 'Last saved')

    def test_hint_overrides_and_restores_text(self):
        owner = object()
        self.label.showHint(owner, 'Play or pause')
        self.assertEqual(self.label.displayText(), 'Play or pause')
        self.label.clearHint(owner)
        self.assertEqual(self.label.displayText(), 'Last saved')

    def test_set_text_during_hover_does_not_clobber_hint(self):
        owner = object()
        self.label.showHint(owner, 'Play or pause')
        self.label.setText('Last saved later')
        self.assertEqual(self.label.displayText(), 'Play or pause')
        self.label.clearHint(owner)
        self.assertEqual(self.label.displayText(), 'Last saved later')

    def test_stale_leave_does_not_clear_neighbour_hint(self):
        a, b = object(), object()
        self.label.showHint(a, 'A')
        self.label.showHint(b, 'B')   # entered B before A's leave fired
        self.label.clearHint(a)
        self.assertEqual(self.label.displayText(), 'B')

    def test_hint_marks_label_for_redraw(self):
        self.label.redraw = False
        self.label.showHint(object(), 'Hint')
        self.assertTrue(self.label.redraw)

class TestInteractiveTooltip(unittest.TestCase):
    def setUp(self):
        self.label = Label(100, 20, text='status')

    def test_hover_shows_and_leave_restores(self):
        el = Interactive(10, 10, name='el')
        el.setTooltip('Hint', self.label)
        hover(el, True)
        self.assertEqual(self.label.displayText(), 'Hint')
        hover(el, False)
        self.assertEqual(self.label.displayText(), 'status')

    def test_existing_hover_handlers_still_run(self):
        el = Interactive(10, 10, name='el')
        calls = []
        el.onMouseEnter(lambda: calls.append('enter'))
        el.onMouseLeave(lambda: calls.append('leave'))
        el.setTooltip('Hint', self.label)
        hover(el, True)
        hover(el, False)
        self.assertEqual(calls, ['enter', 'leave'])

    def test_no_tooltip_leaves_label_alone(self):
        el = Interactive(10, 10, name='el')
        hover(el, True)
        self.assertEqual(self.label.displayText(), 'status')

    def test_removing_tooltip_while_hovered_restores_text(self):
        el = Interactive(10, 10, name='el')
        el.setTooltip('Hint', self.label)
        hover(el, True)
        el.setTooltip(None)
        self.assertEqual(self.label.displayText(), 'status')

class TestSaveMessage(unittest.TestCase):
    def test_saving_reports_saved_not_unsaved(self):
        with tempfile.TemporaryDirectory() as tmp:
            projectFile = os.path.join(tmp, 'song.symphony')
            state = sl.newProgramState('C', 'Lydian', 360, {}, {}, 1, 4)
            msg = fio.dumpToFile(workingFile=projectFile, destFile=projectFile, programState=state)
            self.assertTrue(msg.startswith('Last saved'))
            self.assertIn(projectFile, msg)
            self.assertNotIn('unsaved', msg.lower())
            self.assertTrue(os.path.exists(projectFile))

if __name__ == '__main__':
    unittest.main()
