// Pointer gesture handling for the note grid, structured like the old
// pygame editor's `handleClick` / `handleDrag` / `handleUnClick` in main.py:
// module-level mutable gesture state plus plain functions the React shell
// calls from its pointer events. The one structural difference from pygame
// is that edits are committed through the async `editorAPI` bridge instead
// of mutating the note map directly, so drag previews ("ghosts") are kept
// on screen until the backend echoes the change back.
//
// Every handler takes `grid` — the bag of current props and callbacks the
// shell rebuilds each render (notes, activeChannel, brushId, markDirty, ...).

import editorAPI from "../../editor-bridge.js";
import { convertWorldToGrid } from "./camera.js";
import {
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  SELECT_RECT_MIN_DRAG_PX,
  buildMoveProposal,
  buildResizeProposal,
  findNoteAtPoint,
  findNotesInWorldRect,
  getChannelNameFromHotkey,
  isPointNearNoteTail,
  mergeClickSelection,
  noteKey,
  serializeSelectionEntries,
  snapDelta,
} from "./note-grid-ops.js";

// ---- MODULE STATE ----
// like main.py's `selectingAnything` / `draggingSelection` / ... globals

let gesture = null; // the in-flight pointer gesture, or null
let ghosts = null; // ghost notes drawn above the grid
let hiddenKeys = null; // committed notes hidden under a drag preview
let selectionRect = null; // box-select rect in viewport px
let selectionOverride = null; // keys shown selected before the backend confirms
let pendingCommit = null; // retained drag visuals awaiting backend echo
let commitId = 0;
let altDown = false;
let lastDragPoint = null; // last grid point seen mid-drag, for hotkey re-proposals

/**
 * Exposes the transient visual state for the canvas draw pass.
 */
export function getOverlayState() {
  return { ghosts, hiddenKeys, selectionRect, selectionOverride };
}

/**
 * Returns the kind of the active gesture ("draw", "move-drag", ...) or null.
 */
export function getGestureKind() {
  return gesture?.kind ?? null;
}

/**
 * Builds a stable backend-position signature for commit reconciliation.
 */
function notePositionSignature(color, note) {
  return `${color}:${note.time}:${note.pitch}:${note.duration}`;
}

// ---- OVERLAY DERIVATION ----

/**
 * Rebuilds ghost notes and hidden keys from the current gesture, then asks
 * the shell for a repaint. Called after every gesture mutation.
 */
function refreshOverlay(grid) {
  ghosts = buildGhosts();
  // hide originals for in-place moves/resizes so the ghost reads as the note
  // being moved; duplicate-drag keeps originals visible alongside the ghost
  hiddenKeys = buildHiddenKeys();
  grid.markDirty();
}

/**
 * Converts the in-flight gesture into the ghost notes the canvas draws.
 */
function buildGhosts() {
  if (!gesture) return null;

  if (gesture.kind === "move-drag" || gesture.kind === "resize-drag") {
    const moveVariant = gesture.duplicate ? "ghost" : "preview"; // ghost = copy, preview = move
    return gesture.proposed.map((note) => ({
      color: gesture.targetColor,
      pitch: note.pitch,
      time: note.time,
      duration: note.duration,
      variant: gesture.kind === "resize-drag" ? "preview" : moveVariant,
    }));
  }
  if (gesture.kind === "draw") {
    return [
      {
        color: gesture.color,
        pitch: gesture.pitch,
        time: gesture.time,
        duration: gesture.duration,
        variant: "ghost",
      },
    ];
  }
  return null;
}

/**
 * Returns the keys of original notes a drag preview should hide, or null
 * when the originals stay visible (duplicate drags, draws, erases).
 */
function buildHiddenKeys() {
  if (
    gesture?.kind !== "resize-drag" &&
    (gesture?.kind !== "move-drag" || gesture.duplicate)
  ) {
    return null;
  }
  return new Set(
    gesture.originals.map((note) =>
      noteKey(gesture.originalColor, note.time, note.pitch),
    ),
  );
}

// ---- DRAG PROPOSALS ----

/**
 * Recomputes proposed positions/durations for a move or resize drag from
 * the latest grid point and modifier state.
 */
function updateDragProposal(grid, exactCol, exactRow) {
  if (!gesture) return;
  lastDragPoint = { exactCol, exactRow };

  if (gesture.kind === "move-drag") {
    gesture.deltaCol = snapDelta(exactCol - gesture.startExactCol);
    gesture.deltaRow = snapDelta(exactRow - gesture.startExactRow);
    gesture.duplicate = altDown; // alt held mid-drag switches to copy mode
    gesture.proposed = buildMoveProposal({
      originals: gesture.originals,
      deltaColumn: gesture.deltaCol,
      deltaRow: gesture.deltaRow,
    }).proposed;
  } else if (gesture.kind === "resize-drag") {
    gesture.deltaDuration = snapDelta(exactCol - gesture.startExactCol);
    gesture.proposed = buildResizeProposal({
      originals: gesture.originals,
      deltaDuration: gesture.deltaDuration,
    }).proposed;
  }

  refreshOverlay(grid);
}

/**
 * Updates the box-select rectangle end point and unions newly-enclosed
 * notes into the draft selection. Also re-run by the shell's frame loop so
 * notes scrolling through the rectangle are captured between pointer moves.
 */
export function recaptureBoxSelect(grid) {
  if (gesture?.kind !== "box-select") return;

  selectionRect = {
    startX: gesture.startX,
    startY: gesture.startY,
    endX: gesture.endX,
    endY: gesture.endY,
  };
  const start = convertWorldToGrid(gesture.startX, gesture.startY);
  const end = convertWorldToGrid(gesture.endX, gesture.endY);
  const captured = findNotesInWorldRect({
    notes: grid.notes,
    rect: {
      startColumn: start.exactCol,
      endColumn: end.exactCol,
      startRow: start.exactRow,
      endRow: end.exactRow,
    },
    activeChannel: grid.activeChannel,
  });
  for (const note of captured) {
    gesture.capturedKeys.add(note.key);
  }

  // union with preserved keys so the user still sees pre-gesture selection
  const union = new Set(gesture.capturedKeys);
  for (const key of gesture.preservedKeys) union.add(key);
  selectionOverride = union;
  grid.markDirty();
}

// ---- POINTER HANDLERS ----

/**
 * Starts the gesture for a pointer-down, routed by the current brush.
 * Port of the pygame editor's `handleClick`.
 */
export function handleClick(grid, point, event) {
  if (grid.interactionBlocked) return; // all-channel view blocks editing

  const hit = findNoteAtPoint({
    notes: grid.notes,
    exactColumn: point.exactCol,
    exactRow: point.exactRow,
    activeChannel: grid.activeChannel,
  });

  if (grid.brushId === "pencil") {
    if (!grid.activeChannel) return;
    // clicking an existing note on the active channel does nothing — the
    // select tool handles note interaction; pencil only draws new ones
    if (hit && hit.color === grid.activeChannel) return;
    const pitch = point.row - NOTE_PITCH_TO_GRID_ROW_OFFSET;
    gesture = {
      kind: "draw",
      color: grid.activeChannel,
      pitch,
      time: Math.max(0, point.col),
      startExactCol: point.exactCol,
      duration: 1,
    };
    grid.previewPitch(pitch, grid.activeChannel);
    refreshOverlay(grid);
    return;
  }

  if (grid.brushId === "eraser") {
    const erasedKeys = new Set();
    if (hit) {
      erasedKeys.add(hit.key);
      editorAPI.eraseNoteAt(hit.color, hit.time, hit.pitch).catch(() => {});
    }
    gesture = { kind: "erase", erasedKeys };
    return;
  }

  if (grid.brushId !== "select") return;

  const currentSelection = grid.notes.filter((note) => note.selected);

  if (hit && hit.selected && hit.color === grid.activeChannel && !event.shiftKey) {
    const originals = currentSelection.filter(
      (note) => note.color === grid.activeChannel,
    );
    if (isPointNearNoteTail({ note: hit, exactColumn: point.exactCol, exactRow: point.exactRow })) {
      // near the tail of a selected note: start a resize drag
      gesture = {
        kind: "resize-drag",
        originalColor: grid.activeChannel,
        targetColor: grid.activeChannel,
        originals,
        proposed: [],
        startExactCol: point.exactCol,
        deltaDuration: 0,
      };
    } else {
      // on the body of a selected note: start a move drag
      gesture = {
        kind: "move-drag",
        originalColor: grid.activeChannel,
        targetColor: grid.activeChannel,
        originals,
        proposed: [],
        startExactCol: point.exactCol,
        startExactRow: point.exactRow,
        deltaCol: 0,
        deltaRow: 0,
        duplicate: event.altKey,
      };
      altDown = event.altKey;
    }
    grid.refreshCursor();
    return;
  }

  if (hit) {
    // click on an unselected note: select it and preview the pitch
    const nextSelection = mergeClickSelection({
      currentSelection,
      target: hit,
      additive: event.shiftKey,
    });
    grid.previewPitch(hit.pitch, hit.color);
    editorAPI.setSelection(serializeSelectionEntries(nextSelection)).catch(() => {});
    return;
  }

  // clicked empty space: start a box select
  if (!event.shiftKey && currentSelection.length > 0) {
    editorAPI.clearSelection().catch(() => {});
  }
  const preservedKeys = event.shiftKey
    ? new Set(currentSelection.map((note) => note.key))
    : new Set();
  gesture = {
    kind: "box-select",
    startX: point.x,
    startY: point.y,
    endX: point.x,
    endY: point.y,
    moved: false,
    capturedKeys: new Set(),
    preservedKeys,
  };
  selectionRect = { startX: point.x, startY: point.y, endX: point.x, endY: point.y };
  selectionOverride = preservedKeys;
  grid.markDirty();
}

/**
 * Advances the active gesture as the pointer moves.
 * Port of the pygame editor's `handleDrag`.
 */
export function handleDrag(grid, point, event) {
  altDown = event.altKey;
  if (!gesture) return;

  if (gesture.kind === "draw") {
    const extension = Math.max(0, snapDelta(point.exactCol - gesture.startExactCol)); // rightward drag distance
    const nextDuration = Math.max(1, extension + 1);
    if (nextDuration !== gesture.duration) {
      gesture.duration = nextDuration;
      refreshOverlay(grid);
    }
    return;
  }

  if (gesture.kind === "erase") {
    const hit = findNoteAtPoint({
      notes: grid.notes,
      exactColumn: point.exactCol,
      exactRow: point.exactRow,
      activeChannel: grid.activeChannel,
    });
    if (hit && !gesture.erasedKeys.has(hit.key)) {
      gesture.erasedKeys.add(hit.key);
      editorAPI.eraseNoteAt(hit.color, hit.time, hit.pitch).catch(() => {});
    }
    return;
  }

  if (gesture.kind === "box-select") {
    if (
      !gesture.moved &&
      Math.abs(point.x - gesture.startX) < SELECT_RECT_MIN_DRAG_PX &&
      Math.abs(point.y - gesture.startY) < SELECT_RECT_MIN_DRAG_PX
    ) {
      return;
    }
    gesture.moved = true;
    gesture.endX = point.x;
    gesture.endY = point.y;
    recaptureBoxSelect(grid);
    return;
  }

  if (gesture.kind === "move-drag" || gesture.kind === "resize-drag") {
    updateDragProposal(grid, point.exactCol, point.exactRow);
  }
}

/**
 * Finalizes the gesture on pointer-up and commits it to the backend.
 * Port of the pygame editor's `handleUnClick`. Move/resize previews are
 * retained on screen until the backend echoes the committed positions.
 */
export function handleUnClick(grid, point) {
  if (!gesture) return;
  if (point) {
    if (gesture.kind === "move-drag" || gesture.kind === "resize-drag") {
      updateDragProposal(grid, point.exactCol, point.exactRow);
    } else if (gesture.kind === "draw") {
      const extension = Math.max(0, snapDelta(point.exactCol - gesture.startExactCol));
      gesture.duration = Math.max(1, extension + 1);
    }
  }

  let retainedVisual = false;

  if (gesture.kind === "draw") {
    editorAPI
      .drawNote(gesture.color, {
        time: gesture.time,
        pitch: gesture.pitch,
        duration: gesture.duration,
        data_fields: {},
      })
      .catch(() => {});
  } else if (gesture.kind === "box-select") {
    const draftKeys = new Set(gesture.capturedKeys);
    for (const key of gesture.preservedKeys) draftKeys.add(key);
    const selectedNotes = grid.notes.filter((note) => draftKeys.has(note.key));
    selectionOverride = draftKeys;
    editorAPI
      .setSelection(serializeSelectionEntries(selectedNotes))
      .catch(() => {})
      .finally(() => {
        selectionOverride = null;
        grid.markDirty();
      });
  } else if (gesture.kind === "move-drag") {
    const changed =
      gesture.deltaCol !== 0 ||
      gesture.deltaRow !== 0 ||
      gesture.duplicate ||
      gesture.targetColor !== gesture.originalColor; // channel retarget counts
    if (changed) {
      retainedVisual = true;
      commitTempDrag(
        grid,
        gesture.duplicate ? "duplicate" : "move",
        buildMoveProposal({
          originals: gesture.originals,
          deltaColumn: gesture.deltaCol,
          deltaRow: gesture.deltaRow,
        }),
      );
    } else {
      editorAPI.cancelTempNotes().catch(() => {}); // no-op drag
    }
  } else if (gesture.kind === "resize-drag") {
    if (gesture.deltaDuration !== 0) {
      retainedVisual = true;
      commitTempDrag(
        grid,
        "move",
        buildResizeProposal({
          originals: gesture.originals,
          deltaDuration: gesture.deltaDuration,
        }),
      );
    } else {
      editorAPI.cancelTempNotes().catch(() => {}); // zero-delta resize
    }
  }

  gesture = null;
  selectionRect = null;
  lastDragPoint = null;
  if (!retainedVisual) {
    ghosts = null;
    hiddenKeys = null;
  }
  grid.markDirty();
  grid.refreshCursor();
}

/**
 * Cancels the gesture and discards all transient visuals (escape, pointer
 * capture loss).
 */
export function cancelGesture(grid) {
  gesture = null;
  ghosts = null;
  hiddenKeys = null;
  selectionRect = null;
  selectionOverride = null;
  lastDragPoint = null;
  editorAPI.cancelTempNotes().catch(() => {});
  grid.markDirty();
  grid.refreshCursor();
}

// ---- COMMIT & RECONCILIATION ----

/**
 * Sends a move/duplicate/resize through the temp-notes flow while freezing
 * the drag preview so notes do not flicker back to their old positions
 * before the backend state arrives.
 */
function commitTempDrag(grid, action, { originals, proposed }) {
  const sourceColor = gesture.originalColor;
  const targetColor = gesture.targetColor;

  commitId += 1;
  const id = commitId;
  pendingCommit = {
    id,
    proposedSignatures: new Set(
      proposed.map((note) => notePositionSignature(targetColor, note)), // positions the backend should confirm
    ),
    hiddenOriginalSignatures: buildHiddenKeys()
      ? new Set(
          gesture.originals.map((note) =>
            notePositionSignature(sourceColor, note), // originals to hide until replaced
          ),
        )
      : null,
  };
  ghosts = buildGhosts();
  hiddenKeys = buildHiddenKeys();

  editorAPI
    .beginTempNotes(action, sourceColor, originals, targetColor)
    .then(() => editorAPI.setTempNotes(proposed))
    .then(() => editorAPI.commitTempNotes())
    .catch(() => {
      editorAPI.cancelTempNotes().catch(() => {});
      clearPendingCommit(grid, id);
    });
}

/**
 * Drops the retained commit preview, by id or unconditionally.
 */
function clearPendingCommit(grid, id = null) {
  if (!pendingCommit || (id !== null && pendingCommit.id !== id)) return;
  pendingCommit = null;
  ghosts = null;
  hiddenKeys = null;
  grid.markDirty();
}

/**
 * Clears the retained commit preview once the backend note map contains all
 * proposed positions. The shell calls this whenever fresh notes arrive.
 */
export function reconcileCommitVisual(grid) {
  if (!pendingCommit) return;

  const visible = new Set(
    grid.notes.map((note) => notePositionSignature(note.color, note)),
  );
  const proposedReady = [...pendingCommit.proposedSignatures].every((sig) =>
    visible.has(sig),
  );
  const originalsReplaced =
    !pendingCommit.hiddenOriginalSignatures ||
    [...pendingCommit.hiddenOriginalSignatures].every(
      (sig) => !visible.has(sig) || pendingCommit.proposedSignatures.has(sig), // replaced in place
    );

  if (proposedReady && originalsReplaced) {
    clearPendingCommit(grid, pendingCommit.id);
  }
}

// ---- KEYBOARD MODIFIERS ----

/**
 * Handles alt (duplicate toggle), 1-6 (channel retarget mid-drag), and
 * escape (cancel) while a gesture is active. Returns true when consumed.
 */
export function handleHotkeyDown(grid, event) {
  if (event.key === "Alt" || event.key === "AltGraph") {
    altDown = true;
    if (gesture?.kind === "move-drag" && lastDragPoint) {
      updateDragProposal(grid, lastDragPoint.exactCol, lastDragPoint.exactRow);
    }
    return false;
  }

  if (gesture?.kind === "move-drag") {
    const channel = getChannelNameFromHotkey(event.key);
    if (channel) {
      gesture.targetColor = channel;
      refreshOverlay(grid);
      return true;
    }
    if (event.key === "7") {
      // the "all" channel is not a valid drag target; swallow the key so a
      // mistyped hotkey cannot yank the channel mid-drag
      return true;
    }
  }

  if (event.key === "Escape" && gesture) {
    cancelGesture(grid);
    return true;
  }
  return false;
}

/**
 * Clears duplicate-drag mode when alt is released mid-gesture.
 */
export function handleHotkeyUp(grid, event) {
  if (event.key !== "Alt" && event.key !== "AltGraph") return;
  altDown = false;
  if (gesture?.kind === "move-drag" && lastDragPoint) {
    updateDragProposal(grid, lastDragPoint.exactCol, lastDragPoint.exactRow);
  }
}
