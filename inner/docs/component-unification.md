# Unifying `Element` and `Panel` under a shared `Component`

Goal: stop maintaining two parallel copies of DOM/geometry state, and get dependency
watching (`watch` / `onDepChange`) on `Panel` for free — without redefining it twice
and without changing any current on-screen behavior.

## 1. What is actually duplicated today

`gui/element/base_element.py::Element.__init__` (L124-139) and
`gui/frame.py::Panel.__init__` (L29-44) already declare almost the same fields:

| Field | Element | Panel | Notes |
| --- | --- | --- | --- |
| `name` | yes | yes | identical |
| `width` / `height` | yes (ctor args) | yes (0, computed) | same meaning |
| `offsetX` / `offsetY` / `x` / `y` / `z` | yes | yes | identical |
| `domStatus` | yes | yes | identical |
| `surface` | yes (eager) | yes (lazy, `None`) | same role |
| `damageRects` | yes | yes | identical |
| `style` | no | yes | **only asymmetry that matters for layout** |
| `watching` / `oldWatching` / `depChange` | yes | no | **the feature being ported** |
| `selected` | yes | no | element-only, leave alone |
| `elements` / `selfRender` / `debug` | no | yes | panel-only, leave alone |

Methods that are **byte-for-byte duplicates**:

- `__str__` — `base_element.py:208` vs `frame.py:46`
- `dirty` — `base_element.py:222` vs `frame.py:49`
- `damage` — `base_element.py:228` vs `frame.py:52`
- `clean` — `base_element.py:232` vs `frame.py:56`
- `repair` — `base_element.py:236-252` vs `frame.py:224-241` (identical bodies)
- the tail of `render` (the `positioning == 'screen' | 'relative'` blit + `ValueError`)
  — `base_element.py:254-268` vs `frame.py:331-337`

Watching lives only on `Element`: `watch` (`base_element.py:141`), `onDepChange`
(`base_element.py:177`), and the polling loop in `Element.update`
(`base_element.py:187-206`). `Panel.update` (`frame.py:214-223`) only forwards to
children — it never polls anything.

## 2. Latent bugs the merge should fix (behavior-preserving)

These are worth knowing because the migration touches exactly these lines:

1. **`Element.update` has no `screen` parameter** (`base_element.py:187`) but
   `Panel.update` calls `el.update(screen)` (`frame.py:222`). Any bare `Element`
   placed in a panel raises `TypeError`. It works today only because every real
   child overrides `update(self, screen)` (`Interactive`, `Label`, `Button`,
   `Dropdown`, `TextBox`, `custom.PitchList`, `custom.NoteGrid`, `custom.PlayHead`).
   Unifying forces one signature.
2. **`Label.update` (`label.py:41`) never calls `super().update()`**, so a `Label`
   silently cannot watch anything. Fix while you are here.
3. **`hasattr(el, "style")` guards** at `frame.py:188-189` and `frame.py:205` exist
   purely because `Element` has no `style`. Give `Component` a `style` and these guards
   collapse to plain `el.style.get(...)`.
4. **`getattr(el, "display", "flex")`** at `frame.py:122` and `frame.py:204` — `display`
   is only ever assigned inside `Panel.calculateDimensions` (`frame.py:83`), so an
   element's `display` never resolves from its style. Setting `self.display` in
   `Component.__init__` from `style` makes elements honour `display: fixed/absolute` too.
   *(If you want strictly zero behavior change, keep defaulting `display` to `"flex"`
   for elements and treat this as a follow-up.)*

## 3. Where to put `Component` (minimum-effort, no new import cycle)

Put `Component` at the top of **`gui/element/base_element.py`**, above `class Element`.

Why there and not a new `gui/component.py`: `frame.py` already does
`import gui.element.base_element as gui` (`frame.py:15`), and `base_element.py` does
**not** import `frame`. So `Panel(gui.Component)` adds no new edge to the import graph.
A new module would work too but costs an extra file plus edits to `dom.py`'s imports.

`dom.py` imports both (`dom.py:16-17`) and can then be simplified to test `Component`.

## 4. The migration, file by file

### 4.1 `inner/src/gui/element/base_element.py`

**Add** (insert before `class Element` at L119):

```python
class Component():
    '''
    Shared base for anything that occupies a rect in the DOM: geometry, damage
    tracking, style, and dependency watching. Both Element and Panel inherit it.
    '''

    def __init__(self, width: int = 0, height: int = 0, style: dict | None = None, name: str = ''):
        self.name = name
        self.style = style if style is not None else {}
        self.width = width
        self.height = height
        self.offsetX = 0
        self.offsetY = 0
        self.x = 0
        self.y = 0
        self.z = 0
        self.display = self.style.get("display", "flex")
        self.domStatus = "clean"
        self.surface: pygame.Surface | None = None
        self.damageRects: list[pygame.Rect] = []
        self.watching: list[utils.Watchable] = []
        self.oldWatching: list = []
        self.depChange = None

    def __str__(self):
        return self.name

    # ---- watching (moved verbatim from Element) ----
    def watch(self, deps, operation: str = 'set'): ...        # body from base_element.py:141-175
    def onDepChange(self, function): ...                      # body from base_element.py:177-185

    def snapshotWatched(self):
        return [
            el.value if isinstance(el, utils.LightWatchable) else el.watchId
            for el in self.watching
        ]

    def pollWatched(self):
        '''
        Dirties this component and fires depChange if any watched dep changed since last frame.
        This is the whole of the old Element.update body.
        '''
        for idx, var in enumerate(self.watching):
            current = var.value if isinstance(var, utils.LightWatchable) else var.watchId
            if current != self.oldWatching[idx]:
                dom.dirty(self)
                self.depChange() if callable(self.depChange) else None
        self.oldWatching = self.snapshotWatched()

    def update(self, screen):
        '''
        Base update for every component. Subclasses must call super().update(screen).
        '''
        self.pollWatched()

    # ---- dom status (moved verbatim) ----
    def dirty(self): ...                 # from base_element.py:222-226
    def damage(self, damageRect): ...    # from base_element.py:228-230
    def clean(self): ...                 # from base_element.py:232-234
    def repair(self, screen): ...        # from base_element.py:236-252

    def calculateDimensions(self, parentDimensions):
        '''No-op by default; Panel and some custom elements override.'''
        None

    def blit(self, screen: pygame.Surface, positioning: str = 'relative'):
        '''The shared tail of every render(): places self.surface onto screen.'''
        if positioning == 'screen':
            screen.blit(self.surface, (self.x, self.y))
        elif positioning == 'relative':
            screen.blit(self.surface, (self.offsetX, self.offsetY))
        else:
            raise ValueError(f"Positioning must be either 'screen' or 'relative', not {positioning}")

    def render(self, screen: pygame.Surface, positioning: str = 'relative'):
        self.blit(screen, positioning)
```

Note `watch` (L141-175) ends by assigning `self.oldWatching = [...]`; replace that
tail with `self.oldWatching = self.snapshotWatched()`.

**Shrink `Element`** to:

```python
class Element(Component):
    def __init__(self, width: int, height: int, name: str = '', style: dict | None = None):
        super().__init__(width, height, style, name)
        self.selected = False
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
```

Delete from `Element`: `watch`, `onDepChange`, `update`, `__str__`,
`calculateDimensions`, `dirty`, `damage`, `clean`, `repair`, `render`
(i.e. everything from L141 through L268). All of it now lives on `Component`.

The **one signature change**: `Element.update()` becomes the inherited
`Component.update(self, screen)`.

### 4.2 `inner/src/gui/element/base_interactive.py`

- L296 `super().update()` → `super().update(screen)`.

Nothing else changes; `Interactive` keeps its own `update(self, screen)`.

### 4.3 `inner/src/gui/element/label.py`

- `update` (L41): add `super().update(screen)` as the first line. This is the
  behavior *fix* from §2.2 — a `Label` gains working `watch()`. Existing labels
  watch nothing, so the rendered result is unchanged.

`button.py:49`, `dropdown.py:100`, `textbox.py:150` already call
`super().update(screen)` and need no edit.

### 4.4 `inner/src/gui/element/__init__.py`

- Add `from gui.element.base_element import Component` next to the `Element` import
  (L6) so `gui.Component` is available to callers and to type hints.

### 4.5 `inner/src/gui/frame.py`

**Class header** (L27-44):

```python
class Panel(gui.Component):
    def __init__(self, elements, style: dict = {}, name: str = ""):
        super().__init__(0, 0, style, name)
        self.elements: list[Panel | gui.Element] = elements
        self.selfRender = None
        self.debug = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
```

**Delete** from `Panel`, now inherited: `__str__` (L46-47), `dirty` (L49-50),
`damage` (L52-54), `clean` (L56-58), `repair` (L224-241).

**`calculateDimensions` (L67-194)** — small edits only:

- L83 `self.display = display` may stay (it re-reads style each layout pass, which
  is what makes runtime style mutation work). Harmless either way now that
  `Component.__init__` seeds it.
- L188-189: drop the `hasattr` guards →
  `elDisplay = el.style.get("display", "flex")` and
  `elOffset = el.style.get("offset", [0, 0])`.
- L117 and L202 `validElements` filters become
  `[el for el in self.elements if isinstance(el, gui.Component)]`.
- L122 `getattr(el, "display", "flex")` → `el.display` **only after** you accept
  §2.4; otherwise leave the `getattr`.

**`relativeToScreenSpace` (L196-212)**: L205 `hasattr` guard →
`el.style.get("offset", [0, 0])`. L208-209 `getattr(el, "offsetX", 0)` → `el.offsetX`.

**`update` (L214-223)** — this is where Panels gain watching:

```python
    def update(self, screen):
        super().update(screen)   # <-- polls this panel's own watched deps
        for el in self.elements:
            el.update(screen)
```

**`render` (L243-337)**: replace the trailing `if positioning == 'screen': ...`
block (L331-337) with `self.blit(screen, positioning)`.

**Surface allocation** stays where it is (L150-152 in `calculateDimensions`) —
panels must size lazily, elements eagerly. That is the one legitimate divergence.

### 4.6 `inner/src/gui/dom.py`

Purely simplification; behavior identical.

- L37 `setZOrderRecursively(curr: frame.Panel | gui.Element)` → hint `gui.Component`.
- L30-31 `DIRTY_ELEMENTS` / `DAMAGED_ELEMENTS` type hints → `list[gui.Component]`.
- L65 `if isAbove and (isinstance(el, gui.Element) or isinstance(el, frame.Panel)):`
  → `if isAbove and isinstance(el, gui.Component):`.
- L85 `def dirty(element: gui.Element | frame.Panel)` → `def dirty(component: gui.Component)`.
- L41 / L71 keep `isinstance(curr, frame.Panel)` — those branches genuinely mean
  "has children", not "is a component". (Alternative: test `hasattr(el, 'elements')`
  and drop the `frame` import entirely. Optional.)

### 4.7 `inner/src/gui/custom.py`

- `PitchList.update` (L180) and `NoteGrid.update` (L322) already call
  `super().update(screen)`. No change.
- **`PlayHead` (L420)** is the odd one out: it is not an `Element` at all, yet it
  lives inside `NotePanel` (`main.py:411-418`) and defines `update`/`render` by
  duck typing. Make it `class PlayHead(gui.Element)` with
  `super().__init__(0, 0, name='PlayHead')`, and have `PlayHead.update` call
  `super().update(screen)`. Without this, the `isinstance(el, gui.Component)` filters in
  §4.5 would *exclude* it from `validElements` and change layout.
  **This is required, not optional.** Keep its `render` override as-is (it draws
  straight to the passed surface and never blits `self.surface`).
  Today `PlayHead` has no `width`/`height` at all, so it is skipped by
  `validElements` but still reached by the unguarded `self.elements` loops in
  `update` (L222) and `render` (L325) — inheriting `Element` gives it 0×0 and folds
  it into the flex pass harmlessly, but verify visually per §6.
- `Note` (L483) is not in the DOM tree; leave it alone.

### 4.8 `inner/src/main.py`

No required changes. `MasterPanel.update(screen)` (L1266) already passes `screen`.

**New capability** — panels can now watch, e.g. next to the existing element
watches at L552 / L587-588:

```python
NotePanel.watch([BeatsPerMeasure, BeatLength])
MessagePanel.watch(WorldMessage)
```

This replaces hand-rolled "dirty my linked panel" plumbing:
`custom.PitchList.setLinkedPanels` (L140), `NoteGrid.setLinkedPanels` (L296),
`PlayHead.setLinkedPanel` (L447) and the `dom.dirty(self.panel)` calls at
`custom.py:183`, `341-342`, `458`. Those can be retired incrementally by making the
panels watch the same `Watchable`s directly — **do that as a separate follow-up
commit**, not as part of the type merge.

## 5. Recommended commit split

1. **Commit A — introduce `Component`, no behavior change.** §4.1, §4.2, §4.3, §4.4,
   §4.5 (header + deleted duplicates + `render` tail), §4.6, §4.7 `PlayHead`.
2. **Commit B — Panel watching.** The one-line `super().update(screen)` in
   `Panel.update` (§4.5), plus a first real `watch()` call in `main.py`.
3. **Commit C — optional cleanups.** The `hasattr`/`getattr` guard removals, the
   `display` semantics fix (§2.4), and retiring `setLinkedPanel*`.

## 6. Verification

There is no test suite for the GUI layer (`inner/src/zombie_tests/` covers process
launch only), so:

- Add a headless unit test asserting that a `Panel` with
  `watch([LightWatchable(0)])` appends itself to `dom.DIRTY_ELEMENTS` after the
  watchable is `set()` and `update()` runs — this is the one piece of new logic and
  it needs no display surface beyond `pygame.Surface`.
- Assert `isinstance(Panel([], name='p'), gui.Component)` and
  `isinstance(gui.Label(1, 1), gui.Component)` to lock the hierarchy in.
- Layout is unchanged by construction (Commit A moves code without editing
  arithmetic), but the `PlayHead` reparenting in §4.7 is the real risk. **Please run
  the app after Commit A and confirm:** the toolbar sits flush at the top, the pitch
  column is 80px wide, the note grid fills the rest, and the playhead line still
  sweeps across the grid during playback without the grid shifting position.
