// Imperative canvas rendering for the note grid, structured like the old
// pygame editor's render path: one `drawFrame` repaints everything visible
// in draw order (grid, notes, ghosts, selection rect), and the React shell
// only calls it when something actually changed.
//
// The one optimization beyond a straight pygame port: the grid background
// repeats every measure horizontally and every octave (12 rows) vertically,
// so instead of filling thousands of little rects per frame we render that
// repeating block to an offscreen canvas once (like pre-rendering a pygame
// Surface) and blit it across the viewport with a handful of drawImage calls.

import { tile, view } from "./camera.js";
import { getCellFill } from "./cell-palette.js";
import {
  INACTIVE_NOTE_COLOR,
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  getChannelColor,
} from "./note-grid-ops.js";
import { getOverlayState } from "./gestures.js";

const TILE_GAP = 1;
const MAX_CELL_RADIUS = 3;
const NOTE_EDGE_OVERSCAN = 12; // px of off-screen slack before clipping note rects
const TAIL_AFFORDANCE_WIDTH = 2.5;
const TAIL_AFFORDANCE_INSET = 5;

/**
 * Returns the corner radius for cells at the current zoom.
 */
function cellRadius() {
  return Math.min(MAX_CELL_RADIUS, Math.max(2, Math.round(tile.size * 0.08))); // scale radius with cell, but cap it
}

/**
 * Traces a rounded rect path, falling back to a plain rect when unsupported.
 */
function pathRoundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(x, y, width, height, radius);
  } else {
    ctx.rect(x, y, width, height);
  }
}

// ---- GRID BACKGROUND ----

// offscreen canvas holding one measure x one octave of grid cells. rebuilt
// only when zoom, meter, key, theme, or pixel ratio changes.
let gridBlock = null;
let gridBlockKey = "";

/**
 * Forces the grid block to rebuild on the next frame (e.g. theme change).
 */
export function invalidateGridBlock() {
  gridBlockKey = "";
}

/**
 * Renders the repeating measure-by-octave block of grid cells. This is the
 * same double loop the pygame `NoteGrid.render` ran every frame — it just
 * runs once per zoom/key/meter change now.
 */
function buildGridBlock(grid, measureSize, pixelRatio) {
  const size = tile.size;
  const radius = cellRadius();
  const block = document.createElement("canvas");
  block.width = Math.ceil(measureSize * size * pixelRatio);
  block.height = Math.ceil(12 * size * pixelRatio);

  const ctx = block.getContext("2d");
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  for (let i = 0; i < 12; i += 1) {
    for (let j = 0; j < measureSize; j += 1) {
      ctx.fillStyle = getCellFill({
        column: j,
        row: 12 - i, // block row i holds grid rows = (multiple of 12) - i
        keyPitchClasses: grid.keyPitchClasses,
        beatLength: grid.beatLength,
        beatsPerMeasure: grid.beatsPerMeasure,
        cellPalette: grid.palette,
      });
      pathRoundRect(ctx, j * size, i * size, size - TILE_GAP, size - TILE_GAP, radius);
      ctx.fill();
    }
  }

  return block;
}

/**
 * Blits the pre-rendered grid block across the visible viewport.
 */
function drawGrid(ctx, grid, pixelRatio) {
  const size = tile.size;
  const measureSize =
    Math.max(1, Number(grid.beatLength) || 1) *
    Math.max(1, Number(grid.beatsPerMeasure) || 1);

  const key = [
    size,
    pixelRatio,
    grid.beatLength,
    grid.beatsPerMeasure,
    [...grid.keyPitchClasses].sort((a, b) => a - b).join(","),
    Object.values(grid.palette).join(","),
  ].join("|");
  if (key !== gridBlockKey) {
    gridBlock = buildGridBlock(grid, measureSize, pixelRatio);
    gridBlockKey = key;
  }

  const blockWidth = measureSize * size;
  const blockHeight = 12 * size;
  const startCol = Math.floor(view.col / measureSize) * measureSize; // first measure boundary left of the view
  const startRow = Math.ceil(view.row / 12) * 12; // first octave boundary above the view
  const startX = (startCol - view.col) * size;
  const startY = (view.row - startRow) * size;

  for (let y = startY; y < grid.viewport.height; y += blockHeight) {
    for (let x = startX; x < grid.viewport.width; x += blockWidth) {
      ctx.drawImage(gridBlock, x, y, blockWidth, blockHeight);
    }
  }
}

// ---- NOTES ----

/**
 * Projects a note rect into viewport pixels, or null when off-screen.
 * Long notes are clipped to the viewport so path sizes stay bounded.
 */
function projectNote(grid, time, gridRow, duration) {
  const size = tile.size;
  const viewEndCol = view.col + grid.viewport.width / size;
  if (time + duration <= view.col || time >= viewEndCol) return null;

  const y = (view.row - gridRow) * size;
  const height = size - TILE_GAP;
  if (y + height <= 0 || y >= grid.viewport.height) return null;

  const rawX = (time - view.col) * size;
  const x = Math.max(rawX, -NOTE_EDGE_OVERSCAN);
  const fullWidth = duration * size - TILE_GAP;
  const width = Math.min(fullWidth - (x - rawX), grid.viewport.width + NOTE_EDGE_OVERSCAN - x);
  if (width <= 0) return null;

  return {
    x,
    y,
    width,
    height,
    radius: Math.min(cellRadius() + 1, height / 2, width / 2),
  };
}

/**
 * Fills one note body, optionally with the selection / drag-preview outline.
 * The outline is stroked first and filled over, so half the stroke width
 * shows outside the note edge (the svg `paint-order: stroke fill` look).
 */
function fillNote(ctx, rect, fillColor, outlineWidth) {
  pathRoundRect(ctx, rect.x, rect.y, rect.width, rect.height, rect.radius);
  if (outlineWidth) {
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = outlineWidth;
    ctx.stroke();
  }
  ctx.fillStyle = fillColor;
  ctx.fill();
}

/**
 * Draws the dark grab strip near the tail of a resizable note.
 */
function fillTailAffordance(ctx, rect) {
  if (rect.width <= TAIL_AFFORDANCE_INSET + TAIL_AFFORDANCE_WIDTH + 1) return;
  const EFFECTIVE_INSET = Math.min(TAIL_AFFORDANCE_INSET, rect.height < 20 ? rect.height / 5 : Infinity)
  pathRoundRect(
    ctx,
    rect.x + rect.width - EFFECTIVE_INSET - TAIL_AFFORDANCE_WIDTH,
    rect.y + EFFECTIVE_INSET,
    TAIL_AFFORDANCE_WIDTH,
    Math.max(0, rect.height - (EFFECTIVE_INSET * 2)),
    2,
  );
  ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
  ctx.fill();
}

/**
 * Draws every visible note. Like the pygame `NoteGrid.render`, inactive
 * channels go down first, then the active channel, then selected notes on
 * top so their outlines are never covered.
 */
function drawNotes(ctx, grid, overlay) {
  const inactivePass = [];
  const activePass = [];
  const selectedPass = [];

  for (const note of grid.notes) {
    if (overlay.hiddenKeys && overlay.hiddenKeys.has(note.key)) continue; // hidden behind a drag preview

    const rect = projectNote(grid, note.time, note.gridRow, note.duration);
    if (!rect) continue;

    const inactive = grid.activeChannel != null && note.color !== grid.activeChannel;
    const selected =
      !inactive &&
      (note.selected || (overlay.selectionOverride?.has(note.key) ?? false));

    const entry = { rect, color: note.color };
    if (inactive) inactivePass.push(entry);
    else if (selected) selectedPass.push(entry);
    else activePass.push(entry);
  }

  ctx.globalAlpha = 0.4;
  for (const { rect } of inactivePass) {
    fillNote(ctx, rect, INACTIVE_NOTE_COLOR, 0);
  }

  ctx.globalAlpha = 0.96;
  for (const { rect, color } of activePass) {
    fillNote(ctx, rect, getChannelColor(color), 0);
    if (grid.selectMode) fillTailAffordance(ctx, rect);
  }
  for (const { rect, color } of selectedPass) {
    fillNote(ctx, rect, getChannelColor(color), 3);
    if (grid.selectMode) fillTailAffordance(ctx, rect);
  }
  ctx.globalAlpha = 1;

  return inactivePass.length + activePass.length + selectedPass.length;
}

/**
 * Draws drag previews and draw-stroke ghosts above the committed notes.
 */
function drawGhosts(ctx, grid, overlay) {
  if (!overlay.ghosts) return;

  for (const ghost of overlay.ghosts) {
    const rect = projectNote(
      grid,
      ghost.time,
      ghost.pitch + NOTE_PITCH_TO_GRID_ROW_OFFSET,
      ghost.duration,
    );
    if (!rect) continue;

    if (ghost.variant === "preview") {
      // solid preview of where a move/resize will land
      ctx.globalAlpha = 0.96;
      fillNote(ctx, rect, getChannelColor(ghost.color), 2);
    } else {
      // translucent dashed ghost for draw strokes and duplicate drags
      ctx.globalAlpha = 0.35;
      pathRoundRect(ctx, rect.x, rect.y, rect.width, rect.height, rect.radius);
      ctx.fillStyle = getChannelColor(ghost.color);
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
  ctx.globalAlpha = 1;
}

/**
 * Draws the box-select rectangle (kept in viewport pixels while scrolling).
 */
function drawSelectionRect(ctx, overlay, selectionStroke) {
  const rect = overlay.selectionRect;
  if (!rect) return;

  const left = Math.min(rect.startX, rect.endX);
  const top = Math.min(rect.startY, rect.endY);
  const width = Math.abs(rect.endX - rect.startX);
  const height = Math.abs(rect.endY - rect.startY);

  pathRoundRect(ctx, left + 0.5, top + 0.5, width, height, 2);
  ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
  ctx.fill();
  ctx.strokeStyle = selectionStroke;
  ctx.lineWidth = 1;
  ctx.stroke();
}

// ---- FRAME ----

/**
 * Repaints the whole grid canvas for the current camera and grid state.
 * Returns timing/count info for the optional debug readout.
 */
export function drawFrame(grid, canvas) {
  const ctx = canvas?.getContext("2d");
  if (!ctx || !grid.palette || !grid.viewport.width || !grid.viewport.height) {
    return { drawMs: 0, visibleNotes: 0 };
  }

  const start = performance.now();
  const pixelRatio = window.devicePixelRatio || 1;
  const backingWidth = Math.ceil(grid.viewport.width * pixelRatio);
  const backingHeight = Math.ceil(grid.viewport.height * pixelRatio);
  if (canvas.width !== backingWidth) canvas.width = backingWidth;
  if (canvas.height !== backingHeight) canvas.height = backingHeight;

  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  ctx.clearRect(0, 0, grid.viewport.width, grid.viewport.height);

  const overlay = getOverlayState();
  drawGrid(ctx, grid, pixelRatio);
  const visibleNotes = drawNotes(ctx, grid, overlay);
  drawGhosts(ctx, grid, overlay);
  drawSelectionRect(ctx, overlay, grid.selectionStroke);

  return { drawMs: performance.now() - start, visibleNotes };
}
