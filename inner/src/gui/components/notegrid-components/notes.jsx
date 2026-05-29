import { useCallback, useLayoutEffect, useRef } from "react";
import {
  INACTIVE_NOTE_COLOR,
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  getChannelColor,
} from "../notegrid-utils.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const NOTE_RIGHT_EDGE_OVERSCAN = 12;
const NOTE_LEFT_EDGE_OVERSCAN = 12;
const TAIL_AFFORDANCE_WIDTH = 2.5;
const TAIL_AFFORDANCE_INSET = 5;

/**
 * Projects a note from grid coordinates into visible svg coordinates.
 */
function projectNoteToScreen({
  note,
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  bounds,
  scrollPosition,
}) {
  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize;
  const viewRow = bounds.maxRow - scrollPosition.y / cellSize;
  const viewEndColumn = viewColumn + viewportSize.width / cellSize;
  const maxVisibleRight = viewportSize.width + NOTE_RIGHT_EDGE_OVERSCAN;
  const minVisibleLeft = -NOTE_LEFT_EDGE_OVERSCAN;

  const noteEnd = note.time + note.duration;
  if (noteEnd <= viewColumn || note.time >= viewEndColumn) return null;

  const rawX = (note.time - viewColumn) * cellSize;
  const y = (viewRow - note.gridRow) * cellSize;
  if (y + tileSize <= 0 || y >= viewportSize.height) return null;

  const fullWidth = note.duration * cellSize - Math.max(1, cellSize - tileSize); // remove inter-cell gap
  const x = Math.max(rawX, minVisibleLeft);
  const width = Math.min(fullWidth - (x - rawX), maxVisibleRight - x);
  if (width <= 0) return null;

  return {
    x,
    y,
    width,
    height: tileSize,
    radius: Math.min(cellRadius + 1, tileSize / 2, width / 2),
  };
}

/**
 * Filters, projects, and sorts notes that should be drawn in the viewport.
 */
function getVisibleNotes({
  notes,
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  bounds,
  scrollPosition,
  activeChannel,
  selectionOverride,
  hiddenKeys,
}) {
  if (!viewportSize.width || !viewportSize.height || !cellSize) return [];

  const result = [];
  for (const note of notes) {
    if (hiddenKeys && hiddenKeys.has(note.key)) continue;

    const projection = projectNoteToScreen({
      note,
      viewportSize,
      cellSize,
      tileSize,
      cellRadius,
      bounds,
      scrollPosition,
    });
    if (!projection) continue;

    const inactive = activeChannel != null && note.color !== activeChannel;
    const fill = inactive ? INACTIVE_NOTE_COLOR : getChannelColor(note.color);
    const selected =
      note.selected ||
      (selectionOverride ? selectionOverride.has(note.key) : false);

    result.push({
      key: note.key,
      ...projection,
      color: fill,
      selected,
      inactive,
    });
  }

  result.sort((a, b) => {
    if (a.inactive !== b.inactive) return a.inactive ? -1 : 1;
    if (a.selected !== b.selected) return a.selected ? 1 : -1;
    return 0;
  });

  return result;
}

/**
 * Builds a cheap render signature for visible note changes.
 */
function getVisibleNoteSignature(visibleNotes, selectMode) {
  return (
    `${selectMode ? "S" : "N"}|` +
    visibleNotes
      .map(
        (note) =>
          `${note.key}:${note.x.toFixed(2)}:${note.y.toFixed(2)}:${note.width.toFixed(2)}:${note.height.toFixed(2)}:${note.color}:${note.selected ? 1 : 0}:${note.inactive ? 1 : 0}`,
      )
      .join("|")
  );
}

/**
 * Replaces the note svg contents with the supplied visible notes.
 */
function drawVisibleNotes(svg, visibleNotes, selectMode) {
  if (!svg) return;

  const fragment = document.createDocumentFragment();

  visibleNotes.forEach((note) => {
    const rect = document.createElementNS(SVG_NS, "rect");
    const classes = ["note-grid-note"];
    if (note.inactive) classes.push("note-grid-note-inactive");
    if (note.selected) classes.push("note-grid-note-selected");
    rect.setAttribute("class", classes.join(" "));
    rect.setAttribute("x", String(note.x));
    rect.setAttribute("y", String(note.y));
    rect.setAttribute("width", String(note.width));
    rect.setAttribute("height", String(note.height));
    rect.setAttribute("rx", String(note.radius));
    rect.setAttribute("ry", String(note.radius));
    rect.setAttribute("fill", note.color);
    fragment.appendChild(rect);

    if (
      selectMode &&
      !note.inactive &&
      note.width > TAIL_AFFORDANCE_INSET + TAIL_AFFORDANCE_WIDTH + 1
    ) {
      const tail = document.createElementNS(SVG_NS, "rect");
      tail.setAttribute("class", "note-grid-note-tail-affordance");
      tail.setAttribute(
        "x",
        String(
          note.x + note.width - TAIL_AFFORDANCE_INSET - TAIL_AFFORDANCE_WIDTH,
        ),
      );
      tail.setAttribute("y", String(note.y + 5));
      tail.setAttribute("width", String(TAIL_AFFORDANCE_WIDTH));
      tail.setAttribute("height", String(Math.max(0, note.height - 10)));
      tail.setAttribute("rx", "2");
      tail.setAttribute("ry", "2");
      fragment.appendChild(tail);
    }
  });

  svg.replaceChildren(fragment);
}

/**
 * Renders the visible note layer and exposes imperative scroll updates.
 */
export function Notes({
  notes,
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  bounds,
  initialScrollPosition,
  notesApiRef,
  activeChannel = null,
  selectionOverrideRef = null,
  hiddenKeysRef = null,
  selectMode = false,
}) {
  const svgRef = useRef(null);
  const visibleSignatureRef = useRef("");
  const svgWidth = Math.ceil(viewportSize.width + NOTE_RIGHT_EDGE_OVERSCAN);
  const svgHeight = Math.ceil(viewportSize.height);

  /**
   * Synchronizes the svg note layer for the latest scroll position.
   */
  const syncVisibleNotes = useCallback(
    (scrollPosition = initialScrollPosition) => {
      const nextVisibleNotes = getVisibleNotes({
        notes,
        viewportSize,
        cellSize,
        tileSize,
        cellRadius,
        bounds,
        scrollPosition,
        activeChannel,
        selectionOverride: selectionOverrideRef?.current ?? null,
        hiddenKeys: hiddenKeysRef?.current ?? null,
      });
      const nextSignature = getVisibleNoteSignature(
        nextVisibleNotes,
        selectMode,
      );

      if (nextSignature === visibleSignatureRef.current) return;

      visibleSignatureRef.current = nextSignature;
      drawVisibleNotes(svgRef.current, nextVisibleNotes, selectMode);
    },
    [
      activeChannel,
      bounds,
      cellRadius,
      cellSize,
      hiddenKeysRef,
      initialScrollPosition,
      notes,
      selectMode,
      selectionOverrideRef,
      tileSize,
      viewportSize,
    ],
  );

  useLayoutEffect(() => {
    if (!notesApiRef) return undefined;

    notesApiRef.current = {
      update: syncVisibleNotes,
      invalidate: () => {
        visibleSignatureRef.current = "";
      },
    };
    visibleSignatureRef.current = "";
    syncVisibleNotes(initialScrollPosition);

    return () => {
      if (notesApiRef.current?.update === syncVisibleNotes) {
        notesApiRef.current = null;
      }
    };
  }, [initialScrollPosition, notesApiRef, syncVisibleNotes]);

  return (
    <svg
      ref={svgRef}
      className="note-grid-notes"
      width={svgWidth}
      height={svgHeight}
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      aria-hidden="true"
    />
  );
}
