import { useCallback, useLayoutEffect, useRef } from "react";
import {
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  getChannelColor,
  selectionRectViewportPixels,
} from "../notegrid-utils.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const NOTE_RIGHT_EDGE_OVERSCAN = 12;

/**
 * Projects a ghost note from grid coordinates into overlay coordinates.
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
  const minVisibleLeft = -NOTE_RIGHT_EDGE_OVERSCAN;

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
 * Replaces the ghost svg contents with projected drag or draw previews.
 */
function drawGhostNotes(svg, ghosts) {
  if (!svg) return;

  const fragment = document.createDocumentFragment();
  ghosts.forEach((ghost) => {
    const rect = document.createElementNS(SVG_NS, "rect");
    const classes = ["note-grid-note"];
    classes.push(
      ghost.variant === "preview"
        ? "note-grid-note-drag-preview"
        : "note-grid-note-ghost",
    );
    rect.setAttribute("class", classes.join(" "));
    rect.setAttribute("x", String(ghost.x));
    rect.setAttribute("y", String(ghost.y));
    rect.setAttribute("width", String(ghost.width));
    rect.setAttribute("height", String(ghost.height));
    rect.setAttribute("rx", String(ghost.radius));
    rect.setAttribute("ry", String(ghost.radius));
    rect.setAttribute("fill", ghost.color);
    fragment.appendChild(rect);
  });
  svg.replaceChildren(fragment);
}

/**
 * Renders transient ghost notes and selection rectangles above the grid.
 */
export function Overlay({
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  bounds,
  initialScrollPosition,
  overlayApiRef,
  ghostNotesRef,
  selectionRectRef,
}) {
  const svgRef = useRef(null);
  const rectRef = useRef(null);
  const ghostSignatureRef = useRef("");
  const rectSignatureRef = useRef("");
  const svgWidth = Math.ceil(viewportSize.width + NOTE_RIGHT_EDGE_OVERSCAN);
  const svgHeight = Math.ceil(viewportSize.height);

  /**
   * Synchronizes overlay visuals from mutable gesture refs.
   */
  const updateOverlay = useCallback(
    (scrollPosition = initialScrollPosition) => {
      const ghosts = ghostNotesRef?.current ?? null;
      const ghostList = [];
      if (ghosts && ghosts.length) {
        for (const ghost of ghosts) {
          const note = {
            ...ghost,
            gridRow: ghost.pitch + NOTE_PITCH_TO_GRID_ROW_OFFSET,
          };
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
          ghostList.push({
            ...projection,
            color: getChannelColor(ghost.color),
            variant: ghost.variant,
          });
        }
      }
      const ghostSignature = ghostList
        .map(
          (g) =>
            `${g.x.toFixed(2)}:${g.y.toFixed(2)}:${g.width.toFixed(2)}:${g.color}:${g.variant ?? "ghost"}`,
        )
        .join("|");
      if (
        ghostSignature !== ghostSignatureRef.current ||
        (ghostSignature === "" && svgRef.current?.childNodes.length)
      ) {
        ghostSignatureRef.current = ghostSignature;
        drawGhostNotes(svgRef.current, ghostList);
      }

      const rectState = selectionRectRef?.current ?? null;
      const rectElement = rectRef.current;
      if (rectElement) {
        if (!rectState) {
          rectSignatureRef.current = "";
          rectElement.style.display = "none";
        } else {
          const px = selectionRectViewportPixels({
            startViewportX: rectState.startViewportX,
            startViewportY: rectState.startViewportY,
            endViewportX: rectState.endViewportX,
            endViewportY: rectState.endViewportY,
          });
          const signature = `${px.left.toFixed(2)}:${px.top.toFixed(2)}:${px.width.toFixed(2)}:${px.height.toFixed(2)}`;
          if (signature !== rectSignatureRef.current) {
            rectSignatureRef.current = signature;
            rectElement.style.display = "";
            rectElement.style.transform = `translate3d(${px.left}px, ${px.top}px, 0)`;
            rectElement.style.width = `${px.width}px`;
            rectElement.style.height = `${px.height}px`;
          }
        }
      }
    },
    [
      bounds,
      cellRadius,
      cellSize,
      ghostNotesRef,
      initialScrollPosition,
      selectionRectRef,
      tileSize,
      viewportSize,
    ],
  );

  useLayoutEffect(() => {
    if (!overlayApiRef) return undefined;

    overlayApiRef.current = {
      update: updateOverlay,
      invalidate: () => {
        ghostSignatureRef.current = "";
        rectSignatureRef.current = "";
      },
    };
    updateOverlay(initialScrollPosition);
    return () => {
      if (overlayApiRef.current?.update === updateOverlay) {
        overlayApiRef.current = null;
      }
    };
  }, [initialScrollPosition, overlayApiRef, updateOverlay]);

  return (
    <>
      <svg
        ref={svgRef}
        className="note-grid-ghosts"
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        aria-hidden="true"
      />
      <div
        ref={rectRef}
        className="note-grid-selection-rect"
        style={{ display: "none" }}
        aria-hidden="true"
      />
    </>
  );
}
