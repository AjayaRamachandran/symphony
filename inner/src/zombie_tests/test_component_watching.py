# zombie_tests/test_component_watching.py
# headless checks that Panel and Element share the Component base and that both watch dependencies.
###### IMPORT ######

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.font.init()

import gui.dom as dom
import gui.element as gui
import gui.frame as frame
import utils.util as utils

###### HELPERS ######

def freshDom(root: frame.Panel):
    '''
    fields:
        root (Panel) - panel to treat as the master panel
    outputs: nothing

    Points the dom module at a throwaway tree and empties its queues.
    '''
    dom.init(root)
    dom.DIRTY_ELEMENTS = []
    dom.DAMAGED_ELEMENTS = []

###### TESTS ######

def testHierarchy():
    '''
    Both Panel and Element must resolve to the shared Component base.
    '''
    panel = frame.Panel([], name='panel')
    label = gui.Label(10, 10, name='label')

    assert isinstance(panel, gui.Component), 'Panel does not inherit Component'
    assert isinstance(label, gui.Component), 'Element does not inherit Component'
    assert not isinstance(panel, gui.Element), 'Panel should not be an Element'
    print('testHierarchy: pass')

def testPanelWatchesDependency():
    '''
    A Panel with a watched dependency dirties itself when that dependency changes.
    '''
    value = utils.LightWatchable(0)
    panel = frame.Panel([], name='watchingPanel')
    panel.watch([value])
    freshDom(panel)

    panel.update(None)
    assert dom.DIRTY_ELEMENTS == [], 'panel dirtied itself without a dependency change'

    value.set(1)
    panel.update(None)
    assert panel in dom.DIRTY_ELEMENTS, 'panel did not dirty itself after its dependency changed'
    assert panel.domStatus == 'dirty', f'expected dirty domStatus, got {panel.domStatus}'

    panel.clean()
    dom.DIRTY_ELEMENTS = []
    panel.update(None)
    assert dom.DIRTY_ELEMENTS == [], 'panel re-dirtied itself on an unchanged dependency'
    print('testPanelWatchesDependency: pass')

def testPanelDepChangeCallback():
    '''
    onDepChange fires on a Panel exactly as it does on an Element.
    '''
    value = utils.HeavyWatchable({'a': 1})
    panel = frame.Panel([], name='callbackPanel')
    calls = []

    panel.watch(value)
    panel.onDepChange(lambda: calls.append(True))
    freshDom(panel)

    panel.update(None)
    assert calls == [], 'depChange fired without a dependency change'

    value.set({'a': 2})
    panel.update(None)
    assert len(calls) == 1, f'expected one depChange call, got {len(calls)}'
    print('testPanelDepChangeCallback: pass')

def testNestedUpdatePropagates():
    '''
    A panel's update reaches both its own watchers and its children's.
    '''
    panelValue = utils.LightWatchable(0)
    labelValue = utils.LightWatchable(0)

    label = gui.Label(10, 10, name='child')
    label.watch([labelValue])

    inner = frame.Panel([label], name='inner')
    inner.watch([panelValue])
    root = frame.Panel([inner], name='root')
    freshDom(root)

    panelValue.set(1)
    labelValue.set(1)
    root.update(None)

    assert inner in dom.DIRTY_ELEMENTS, 'nested panel did not dirty from its own dependency'
    assert label in dom.DIRTY_ELEMENTS, 'child element did not dirty from its own dependency'
    print('testNestedUpdatePropagates: pass')

def testBarePanelAndElementUpdateSignature():
    '''
    A bare Element inside a Panel must not blow up on update (the old Element.update took no screen).
    '''
    element = gui.Element(5, 5, name='bare')
    root = frame.Panel([element], name='root')
    freshDom(root)

    root.update(None)
    print('testBarePanelAndElementUpdateSignature: pass')

def testLayoutStillResolves():
    '''
    Sanity check that the flexbox pass still sizes and positions a simple tree.
    '''
    element = gui.Element(30, 20, name='fixedSize')
    inner = frame.Panel([element], style={'padding': 5}, name='inner')
    root = frame.Panel([inner], style={'sizing': ['fill', 'fill']}, name='root')

    root.calculateDimensions([200, 100])
    root.relativeToScreenSpace([0, 0])

    assert (root.width, root.height) == (200, 100), f'root sized {root.width}x{root.height}'
    assert (inner.width, inner.height) == (40, 30), f'inner sized {inner.width}x{inner.height}'
    assert (element.x, element.y) == (5, 5), f'element placed at {element.x},{element.y}'
    print('testLayoutStillResolves: pass')

def testCustomComponentsReadThroughGetters():
    '''
    NoteGrid and PitchList must hold callables, not snapshots, and must see later mutations
    of the source value without anything re-pushing it.
    '''
    import gui.custom as custom

    noteMap = {'orange': []}
    beatLength = 4

    grid = custom.NoteGrid(100, 100, name='grid')
    grid.setNoteMap(lambda: noteMap)
    grid.setIntervals(lambda: beatLength, lambda: 4)

    assert grid.noteMapGetter() is noteMap, 'grid did not store a live getter'

    noteMap = {'cyan': []}          # rebinding the source, as main.py does on project load
    beatLength = 8
    assert grid.noteMapGetter() is noteMap, 'grid read a stale noteMap'
    assert grid.beatLengthGetter() == 8, 'grid read a stale beat length'

    pitches = custom.PitchList(80, 100, name='pitches')
    for name in ('modeGetter', 'keyGetter', 'noteGetter', 'waveGetter'):
        assert callable(getattr(pitches, name)), f'{name} is not callable by default'
    print('testCustomComponentsReadThroughGetters: pass')

def testViewStateIsWatchable():
    '''
    The shared view state is a single Watchable source of truth, so a panel can watch it.
    '''
    import gui.custom as custom

    for name in ('viewRow', 'viewCol', 'tileWidth', 'tileHeight'):
        assert isinstance(getattr(custom, name), utils.LightWatchable), f'custom.{name} is not Watchable'

    panel = frame.Panel([], name='viewPanel')
    panel.watch([custom.viewCol])
    freshDom(panel)

    startCol = custom.viewCol.value
    custom.viewCol.set(startCol + 5)
    panel.update(None)
    assert panel in dom.DIRTY_ELEMENTS, 'panel did not react to a view state change'
    custom.viewCol.set(startCol)
    print('testViewStateIsWatchable: pass')

def testChildUpdatesBeforeParentPolls():
    '''
    A panel must see a dependency its own subtree changed within the same frame.
    '''
    value = utils.LightWatchable(0)

    class Mutator(gui.Element):
        def update(self, screen):
            super().update(screen)
            value.set(value.value + 1)

    panel = frame.Panel([Mutator(1, 1, name='mutator')], name='parent')
    panel.watch([value])
    freshDom(panel)

    panel.update(None)
    assert panel in dom.DIRTY_ELEMENTS, 'panel polled before its child ran, so it missed the change'
    print('testChildUpdatesBeforeParentPolls: pass')

if __name__ == '__main__':
    testHierarchy()
    testPanelWatchesDependency()
    testPanelDepChangeCallback()
    testNestedUpdatePropagates()
    testBarePanelAndElementUpdateSignature()
    testLayoutStillResolves()
    testChildUpdatesBeforeParentPolls()
    testCustomComponentsReadThroughGetters()
    testViewStateIsWatchable()
    print('\nall component watching tests passed')
