// Pure helpers for note-grid pointer behavior. Keeps coordinate math, hit
// testing, selection bookkeeping, drag/duplicate/resize proposal shapes, and
// channel filtering out of the React surface so the surface can stay focused
// on event wiring and rendering.

export const NOTE_PITCH_TO_GRID_ROW_OFFSET = 35;

export const NOTE_CHANNEL_COLORS = {
  orange: "#eb904a",
  purple: "#b87de3",
  cyan: "#6ccfc6",
  lime: "#9ade8a",
  blue: "#6a7ad6",
  pink: "#d66a9b",
};

export const CHANNEL_NAMES = ["orange", "purple", "cyan", "lime", "blue", "pink"];
export const ALL_CHANNEL_INDEX = 6;
export const INACTIVE_NOTE_COLOR = "#5a5a5a";
export const TAIL_TOLERANCE_COLUMNS = 0.28;
export const SELECT_RECT_MIN_DRAG_PX = 2;

/**
 * Resolves a channel name to its display color.
 */
export function getChannelColor(name) {
  return NOTE_CHANNEL_COLORS[name] ?? name;
}

/**
 * Returns the active channel name, or null when all channels are active.
 */
export function getActiveChannelName(currentColorIdx) {
  const idx = Math.max(0, Math.min(ALL_CHANNEL_INDEX, Number(currentColorIdx) || 0));
  if (idx === ALL_CHANNEL_INDEX) return null;
  return CHANNEL_NAMES[idx];
}

/**
 * Maps number-row hotkeys to editable channel names.
 */
export function getChannelNameFromHotkey(key) {
  if (!/^[1-6]$/.test(key)) return null;
  return CHANNEL_NAMES[Number(key) - 1];
}

/**
 * Builds the stable frontend identity for a note.
 */
export function noteKey(color, time, pitch) {
  return `${color}:${time}:${pitch}`;
}

/**
 * Builds a flat list of frontend note records from the backend note map.
 * Each record keeps the raw backend coordinates (pitch, time, duration) so
 * intents like draw/erase/select can round-trip without coordinate drift,
 * plus a precomputed grid row (= pitch + offset) for rendering and hit tests.
 */
export function normalizeNoteMap(noteMap) {
  if (!noteMap || typeof noteMap !== "object") return [];

  const result = [];
  for (const [color, notes] of Object.entries(noteMap)) {
    if (!Array.isArray(notes)) continue;

    for (const note of notes) {
      const pitch = Number(note?.pitch);
      const time = Number(note?.time);
      const duration = Number(note?.duration);

      if (!Number.isFinite(pitch) || !Number.isFinite(time) || !Number.isFinite(duration) || duration <= 0) {
        continue;
      }

      result.push({
        color,
        pitch,
        gridRow: pitch + NOTE_PITCH_TO_GRID_ROW_OFFSET,
        time,
        duration,
        selected: Boolean(note?.selected),
        dataFields: note?.data_fields ?? {},
        key: noteKey(color, time, pitch),
      });
    }
  }
  return result;
}

/**
 * Translates a viewport-relative pointer position into grid world coordinates.
 * `column` and `row` are integer cell indices; `exactColumn` and `exactRow`
 * are floats that callers can use for tail-proximity and rectangle math.
 */
export function viewportToWorldPoint({ viewportX, viewportY, scrollPosition, cellSize, bounds }) {
  const exactColumn = bounds.minColumn + (scrollPosition.x + viewportX) / cellSize; // viewport px to world column
  const exactRow = bounds.maxRow - (scrollPosition.y + viewportY) / cellSize; // viewport px to world row

  return {
    exactColumn,
    exactRow,
    column: Math.floor(exactColumn),
    row: Math.ceil(exactRow),
  };
}

/**
 * Translates a world cell position back into a viewport pixel position. Used
 * by overlays (selection rect ghosts, drag ghost notes) that draw in viewport
 * coordinates while reasoning in world cells.
 */
export function worldCellToViewportPoint({ column, gridRow, scrollPosition, cellSize, bounds }) {
  const x = (column - bounds.minColumn) * cellSize - scrollPosition.x; // world column to viewport px
  const y = (bounds.maxRow - gridRow) * cellSize - scrollPosition.y; // world row to viewport px
  return { x, y };
}

/**
 * Checks whether a world point falls inside a note body.
 */
function pointInNote(note, exactColumn, exactRow) {
  if (exactColumn < note.time || exactColumn >= note.time + note.duration) return false;
  if (exactRow > note.gridRow) return false;
  if (exactRow <= note.gridRow - 1) return false;
  return true;
}

/**
 * Picks the topmost note at the supplied world point. When an active channel
 * is supplied we prefer notes on that channel so users do not accidentally
 * grab visible-but-inactive context notes.
 */
export function findNoteAtPoint({ notes, exactColumn, exactRow, activeChannel }) {
  let activeHit = null;
  let inactiveHit = null;

  for (const note of notes) {
    if (!pointInNote(note, exactColumn, exactRow)) continue;
    if (activeChannel && note.color === activeChannel) {
      activeHit = note;
    } else if (!activeHit) {
      inactiveHit = note;
    }
  }

  return activeHit ?? inactiveHit ?? null;
}

/**
 * Returns true when the supplied world point is within tail tolerance of the
 * note's right edge. Used to switch the cursor to a horizontal-resize variant
 * and to start a tail-resize gesture instead of a move gesture.
 */
export function isPointNearNoteTail({ note, exactColumn, exactRow, tolerance = TAIL_TOLERANCE_COLUMNS }) {
  if (exactRow > note.gridRow || exactRow <= note.gridRow - 1) return false;
  const end = note.time + note.duration;
  return exactColumn >= note.time && exactColumn <= end && end - exactColumn <= tolerance;
}

/**
 * Checks whether two world-space rectangles intersect.
 */
function rectsOverlap(aMinCol, aMaxCol, aMinRow, aMaxRow, bMinCol, bMaxCol, bMinRow, bMaxRow) {
  if (aMaxCol < bMinCol || aMinCol > bMaxCol) return false;
  if (aMaxRow < bMinRow || aMinRow > bMaxRow) return false;
  return true;
}

/**
 * Finds every note whose bounds intersect the supplied world rectangle. Used
 * by the box-select gesture; the active channel limits which notes the box
 * can grab so inactive context notes never enter the selection.
 */
export function findNotesInWorldRect({ notes, rect, activeChannel }) {
  const minCol = Math.min(rect.startColumn, rect.endColumn);
  const maxCol = Math.max(rect.startColumn, rect.endColumn);
  const minRow = Math.min(rect.startRow, rect.endRow);
  const maxRow = Math.max(rect.startRow, rect.endRow);

  const result = [];
  for (const note of notes) {
    if (activeChannel && note.color !== activeChannel) continue;
    if (rectsOverlap(note.time, note.time + note.duration, note.gridRow - 1, note.gridRow, minCol, maxCol, minRow, maxRow)) {
      result.push(note);
    }
  }
  return result;
}

/**
 * Snaps raw drag deltas to whole grid cells.
 */
export function snapDelta(rawCells) {
  return Math.round(rawCells);
}

/**
 * Produces the {originals, proposed} payload pair used by the temp-note drag
 * API. `originals` mirrors the pre-drag note positions exactly so the backend
 * can find and remove them on a move commit; `proposed` carries the snapped
 * post-drag positions.
 */
export function buildMoveProposal({ originals, deltaColumn, deltaRow }) {
  return {
    originals: originals.map((note) => ({
      pitch: note.pitch,
      time: note.time,
      duration: note.duration,
      data_fields: note.dataFields ?? {},
    })),
    proposed: originals.map((note) => ({
      pitch: note.pitch + deltaRow,
      time: Math.max(0, note.time + deltaColumn),
      duration: note.duration,
      data_fields: note.dataFields ?? {},
    })),
  };
}

/**
 * Same shape as `buildMoveProposal` but resizes by a duration delta instead
 * of moving. Durations are clamped to one cell so resize cannot collapse a
 * note to zero width.
 */
export function buildResizeProposal({ originals, deltaDuration }) {
  return {
    originals: originals.map((note) => ({
      pitch: note.pitch,
      time: note.time,
      duration: note.duration,
      data_fields: note.dataFields ?? {},
    })),
    proposed: originals.map((note) => ({
      pitch: note.pitch,
      time: note.time,
      duration: Math.max(1, note.duration + deltaDuration),
      data_fields: note.dataFields ?? {},
    })),
  };
}

/**
 * Computes the world rectangle for a viewport-anchored selection box given
 * the current scroll position. Both corners are anchored to the viewport so
 * the box appears to stay put on screen; as the user scrolls, the underlying
 * world coordinates shift, letting notes scroll into or out of the box.
 */
export function selectionRectToWorldRect({ startViewportX, startViewportY, endViewportX, endViewportY, currentScroll, cellSize, bounds }) {
  const start = viewportToWorldPoint({
    viewportX: startViewportX,
    viewportY: startViewportY,
    scrollPosition: currentScroll,
    cellSize,
    bounds,
  });
  const end = viewportToWorldPoint({
    viewportX: endViewportX,
    viewportY: endViewportY,
    scrollPosition: currentScroll,
    cellSize,
    bounds,
  });
  return {
    startColumn: start.exactColumn,
    endColumn: end.exactColumn,
    startRow: start.exactRow,
    endRow: end.exactRow,
  };
}

/**
 * Returns the viewport pixel rectangle for a viewport-anchored selection
 * box. The rectangle stays in viewport space even as the user scrolls, so
 * the overlay can render with a fixed transform.
 */
export function selectionRectViewportPixels({ startViewportX, startViewportY, endViewportX, endViewportY }) {
  return {
    left: Math.min(startViewportX, endViewportX),
    top: Math.min(startViewportY, endViewportY),
    width: Math.abs(endViewportX - startViewportX),
    height: Math.abs(endViewportY - startViewportY),
  };
}

/**
 * Reduces selection bookkeeping for a click on a single note. Shift adds or
 * toggles, plain clicks replace. Returns an array of note records for the
 * caller to forward to `editorAPI.setSelection`.
 */
export function mergeClickSelection({ currentSelection, target, additive }) {
  if (!additive) return [target];

  const existingKeys = new Set(currentSelection.map((note) => note.key));
  if (existingKeys.has(target.key)) {
    return currentSelection.filter((note) => note.key !== target.key);
  }
  return [...currentSelection, target];
}

/**
 * Converts a list of frontend note records into the {color, time, pitch}
 * shape that `editorAPI.setSelection` expects.
 */
export function serializeSelectionEntries(selection) {
  return selection.map((note) => ({
    color: note.color,
    time: note.time,
    pitch: note.pitch,
  }));
}
