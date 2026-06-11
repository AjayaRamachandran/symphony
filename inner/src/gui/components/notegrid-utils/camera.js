// The grid camera. Like the old pygame editor's `custom.viewCol` /
// `custom.viewRow` / `custom.tileWidth`, this is shared mutable module
// state: the gesture code, the draw code, and the React shell all read
// and write the same `view` and `tile` objects directly.
//
// Coordinate model:
//   - grid space: `col` is a time column (0 at project start, growing right),
//     `gridRow` is a pitch row (rows grow upward; a cell at gridRow r spans
//     exact rows (r-1, r]).
//   - screen space: viewport pixels with (0, 0) at the top-left of the grid
//     viewport. `view.col` / `view.row` is the grid position of that corner.

export const ZOOM_LEVELS = [14, 16, 20, 26, 32, 40, 48];
export const DEFAULT_ZOOM_INDEX = 4; // 32px cells

export const MIN_COLUMN = 0;
export const MAX_ROW = 96; // top of the pitch range
export const MIN_BOTTOM_ROW = 12; // bottom of the pitch range

// the camera itself: top-left visible grid corner (fractional) and cell size
export const view = { col: MIN_COLUMN, row: MAX_ROW };
export const tile = { size: ZOOM_LEVELS[DEFAULT_ZOOM_INDEX] };

/**
 * Converts a grid position to viewport pixel coordinates.
 * Mirror of the pygame editor's `convertGridToWorld`.
 */
export function convertGridToWorld(col, gridRow) {
  return {
    x: (col - view.col) * tile.size,
    y: (view.row - gridRow) * tile.size,
  };
}

/**
 * Converts viewport pixel coordinates to grid coordinates.
 * Mirror of the pygame editor's `convertWorldToGrid`. `col`/`row` are the
 * integer cell under the point; `exactCol`/`exactRow` keep the fraction for
 * tail-proximity checks and rectangle math.
 */
export function convertWorldToGrid(x, y) {
  const exactCol = view.col + x / tile.size;
  const exactRow = view.row - y / tile.size;
  return {
    exactCol,
    exactRow,
    col: Math.floor(exactCol),
    row: Math.ceil(exactRow),
  };
}

/**
 * Clamps the camera so it never scrolls past the project bounds.
 * Mirror of the pygame editor's `NoteGrid.viewBounds`.
 */
export function viewBounds(viewportWidth, viewportHeight, maxColumn) {
  const colsVisible = viewportWidth / tile.size;
  const rowsVisible = viewportHeight / tile.size;
  const maxColScroll = Math.max(0, maxColumn - MIN_COLUMN + 1 - colsVisible); // columns hidden off-screen
  const maxRowScroll = Math.max(0, MAX_ROW - MIN_BOTTOM_ROW + 1 - rowsVisible); // rows hidden off-screen

  view.col = Math.min(MIN_COLUMN + maxColScroll, Math.max(MIN_COLUMN, view.col));
  view.row = Math.max(MAX_ROW - maxRowScroll, Math.min(MAX_ROW, view.row));
}

/**
 * Expresses the camera as pixel scroll offsets from the top-left of the
 * project. The ticker, pitch list, playhead, and scrollbar chrome still
 * think in scroll pixels, so this is the adapter for them.
 */
export function getScrollPosition() {
  return {
    x: (view.col - MIN_COLUMN) * tile.size,
    y: (MAX_ROW - view.row) * tile.size,
  };
}

/**
 * Returns the maximum horizontal scroll offset in pixels for the scrollbar.
 */
export function getMaxScrollX(viewportWidth, maxColumn) {
  const contentWidth = (maxColumn - MIN_COLUMN + 1) * tile.size;
  return Math.max(0, contentWidth - viewportWidth);
}
