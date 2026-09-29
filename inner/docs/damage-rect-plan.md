# Damage Rectangles: Painted-Rect Plan

Plan for making the DOM damage system correctly repair regions vacated by elements that
move, grow, or shrink (originally surfaced by dropdown collapse leaving a ghost).

## Current Problems

1. **Damage rect is read too late.** `dom.dirty` (`gui/dom.py`) builds the damage rect from
   `el.x / el.y / el.width / el.height` at call time. Handlers like `Dropdown.handleClick`
   already reset `self.height` to `initHeight` during `Interactive.update`, so the tall
   expanded region is never damaged.
2. **`damagerName` only matches panels.** In `damageClippingAbovePanelsRecursively`, the
   `el.name == damagerName` check sits inside the `isinstance(el, frame.Panel)` branch. When
   the damager is a plain element, `isAbove` never becomes `True` and *nothing* is damaged.
3. **Only elements above are damaged.** A vacated region also needs whatever sits *below* it
   in z-order to repaint, since those pixels were overwritten by the damager.

## The Fix, In Three Parts

### 1. Track the last painted rect (`gui/element/base_element.py`)

- Add `self.paintedRect: pygame.Rect | None = None` to `Element.__init__`.
- Set it where pixels actually land — at the tail of `Element.blit` (and therefore every
  `render`): `self.paintedRect = pygame.Rect(self.x, self.y, self.width, self.height)`.
- Why at paint time, not per frame: correctness then does not depend on *when* geometry
  changed during the frame. A stale `paintedRect` can only cause overdraw, never missing
  pixels.
- In `Panel.render` (`gui/frame.py`), also refresh descendants' `paintedRect`, since children
  drawn into the panel surface never go through their own `blit(screen)` path.

### 2. Damage the old rect *and* the new rect (`gui/dom.py`)

- In `dirty(el)`, collect both `el.paintedRect` (skip if `None`) and the current rect.
- Pass them as a **list of rects**, not a union — a large move would make the union a huge,
  mostly-empty rect. Merge into one rect only when the two overlap. `Element.damageRects` is
  already a list, so this needs no change downstream.
- Optionally expose an explicit form (`dom.damage(el, rects)`) for callers that already know
  the old geometry.

### 3. Fix the traversal (`gui/dom.py`)

- Rename `damageClippingAbovePanelsRecursively` to reflect the new behaviour, and:
  - Move the `el.name == damagerName` check out of the `Panel`-only branch so elements can
    be damagers too. Better: compare identity (`el is damager`) instead of name.
  - Damage **every** element intersecting the rects regardless of z — lower-z to reconstruct
    what was underneath, higher-z to re-occlude. The `isAbove` flag can go away.
- `flip` already sorts by `z` and dedups, so paint order is correct once the right elements
  are queued.

## What This Removes

- `WaveDropdown.onClose(lambda: MasterPanel.render(screen, 'screen'))` in `main.py` and
  similar hard-coded full-screen repaints (`AccidentalsButton`, `finalize*`, keydown handlers)
  become unnecessary.
- `Dropdown` needs no special-case rect bookkeeping — `handleClick` / `handleClickOut` keep
  mutating `self.height` and setting `self.redraw`.

## Related, But Out Of Scope

An expanded dropdown only escapes its ~30px-tall parent panel because `flip` renders it with
`positioning='screen'`; a normal `Panel.render` clips it to the parent surface. "Element paints
outside its parent" should eventually be an explicit style/flag rather than an artifact of
which code path drew it.

## How To Verify (UI check — needs a human)

1. Open `KeyDropdown` and re-select the value that is *already* current. Nothing repaints
   today (no watched value changes), so the expanded list should ghost; after the fix the
   toolbar strip and grid beneath should be clean.
2. Open `KeyDropdown` and dismiss it by clicking the placeholder row, then by clicking well
   outside it. Both go through `handleClickOut` and should leave no ghost.
3. Repeat for `ModeDropdown` and `WaveDropdown` (the latter no longer has its `onClose`
   full repaint).
