import { ZoomIn, ZoomOut } from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import flatIcon from "@/assets/editor-icons/flat.svg?raw";
import {
  INACTIVE_NOTE_COLOR,
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  getChannelColor,
  selectionRectViewportPixels,
} from "../notegrid-utils.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const PITCH_CLASS_LABELS = [
  { note: "C" },
  { note: "D", accidental: "flat" },
  { note: "D" },
  { note: "E", accidental: "flat" },
  { note: "E" },
  { note: "F" },
  { note: "G", accidental: "flat" },
  { note: "G" },
  { note: "A", accidental: "flat" },
  { note: "A" },
  { note: "B", accidental: "flat" },
  { note: "B" },
];

/**
 * Returns a non-negative modulo result for wrapped pitch and measure math.
 */
function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor;
}

/**
 * Draws the visible grid with the same camera model as the pygame editor:
 * screen position is derived directly from grid position minus view position.
 */
function drawVisibleGrid({
  canvas,
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  keyPitchClasses,
  beatLength,
  beatsPerMeasure,
  getCellPalette,
  getCellFill,
  scrollPosition,
  bounds,
  onRenderStats,
}) {
  const context = canvas?.getContext("2d");
  const canvasWidth = Math.ceil(viewportSize.width + cellSize);
  const canvasHeight = Math.ceil(viewportSize.height + cellSize);

  if (!canvas || !context || canvasWidth <= 0 || canvasHeight <= 0) return;

  const renderStart = performance.now();
  const pixelRatio = window.devicePixelRatio || 1;
  const backingWidth = Math.ceil(canvasWidth * pixelRatio);
  const backingHeight = Math.ceil(canvasHeight * pixelRatio);

  if (canvas.width !== backingWidth) {
    canvas.width = backingWidth;
  }

  if (canvas.height !== backingHeight) {
    canvas.height = backingHeight;
  }

  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize; // scroll px to grid column
  const viewRow = bounds.maxRow - scrollPosition.y / cellSize; // scroll px to grid row
  const startColumn = Math.floor(viewColumn);
  const startRow = Math.ceil(viewRow);
  const cellPalette = getCellPalette();
  let drawCount = 0;

  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, canvasWidth, canvasHeight);

  for (
    let planeRow = startRow;
    (viewRow - planeRow) * cellSize < viewportSize.height;
    planeRow -= 1
  ) {
    const screenY = (viewRow - planeRow) * cellSize;

    for (
      let planeColumn = startColumn;
      (planeColumn - viewColumn) * cellSize < viewportSize.width;
      planeColumn += 1
    ) {
      const screenX = (planeColumn - viewColumn) * cellSize;
      context.fillStyle = getCellFill({
        column: planeColumn,
        row: planeRow,
        keyPitchClasses,
        beatLength,
        beatsPerMeasure,
        cellPalette,
      });
      fillRoundedRect(
        context,
        screenX,
        screenY,
        tileSize,
        tileSize,
        cellRadius,
      );
      drawCount += 1;
    }
  }

  onRenderStats?.({
    drawMs: performance.now() - renderStart,
    drawCount,
    canvasWidth,
    canvasHeight,
    backingWidth,
    backingHeight,
    pixelRatio,
  });
}

/**
 * Fills a rounded rectangle, falling back to a square fill for tiny radii.
 */
function fillRoundedRect(context, x, y, width, height, radius) {
  const safeRadius = Math.min(radius, width / 2, height / 2);

  if (safeRadius <= 0) {
    context.fillRect(x, y, width, height);
    return;
  }

  context.beginPath();
  context.moveTo(x + safeRadius, y);
  context.lineTo(x + width - safeRadius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  context.lineTo(x + width, y + height - safeRadius);
  context.quadraticCurveTo(
    x + width,
    y + height,
    x + width - safeRadius,
    y + height,
  );
  context.lineTo(x + safeRadius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  context.lineTo(x, y + safeRadius);
  context.quadraticCurveTo(x, y, x + safeRadius, y);
  context.closePath();
  context.fill();
}

/**
 * Formats a grid row as a pitch label and octave.
 */
function getPitchLabel(row) {
  const pitchClass = PITCH_CLASS_LABELS[positiveModulo(row, 12)];
  const octave = Math.floor(row / 12) - 1;
  return { ...pitchClass, octave };
}

/**
 * Updates fixed ticker slots using modular camera movement. The layer transform
 * changes every frame, while labels only change when the integer row changes.
 */
function updateTickerSlots({
  slots,
  layer,
  scrollPosition,
  bounds,
  cellSize,
  beatLength,
  beatsPerMeasure,
}) {
  const beatSize = Math.max(1, Number(beatLength) || 1);
  const measureSize = beatSize * Math.max(1, Number(beatsPerMeasure) || 1);
  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize;
  const startColumn = Math.floor(viewColumn);
  const fractionalColumn = viewColumn - startColumn;

  if (layer.current) {
    layer.current.style.transform = `translate3d(${-fractionalColumn * cellSize}px, 0, 0)`; // keep fixed slots aligned
  }

  if (
    slots.baseColumn === startColumn &&
    slots.cellSize === cellSize &&
    slots.measureSize === measureSize
  ) {
    return;
  }

  slots.baseColumn = startColumn;
  slots.cellSize = cellSize;
  slots.measureSize = measureSize;

  slots.current.forEach((slot, visualColumn) => {
    if (!slot) return;

    const planeColumn = startColumn + visualColumn; // visual slot to world column
    const isMeasureStart = positiveModulo(planeColumn, measureSize) === 0;
    slot.style.left = `${visualColumn * cellSize}px`;
    slot.style.display = isMeasureStart ? "" : "none";
    slot.textContent = isMeasureStart
      ? String(Math.floor(planeColumn / measureSize) + 1)
      : "";
  });
}

/**
 * Updates fixed pitch slots using modular camera movement. The layer transform
 * changes every frame, while label text only changes when the integer row changes.
 */
function updatePitchSlots({ slots, layer, scrollPosition, bounds, cellSize }) {
  const viewRow = bounds.maxRow - scrollPosition.y / cellSize;
  const startRow = Math.ceil(viewRow);
  const fractionalRow = viewRow - startRow;

  if (layer.current) {
    layer.current.style.transform = `translate3d(0, ${fractionalRow * cellSize}px, 0)`; // keep fixed slots aligned
  }

  if (slots.baseRow === startRow && slots.cellSize === cellSize) {
    return;
  }

  slots.baseRow = startRow;
  slots.cellSize = cellSize;

  slots.current.forEach((slot, visualRow) => {
    if (!slot) return;

    const planeRow = startRow - visualRow; // visual slot to world row
    const { note, accidental, octave } = getPitchLabel(planeRow);
    const noteElement = slot.querySelector("[data-pitch-note]");
    const flatElement = slot.querySelector("[data-pitch-flat]");
    const octaveElement = slot.querySelector("[data-pitch-octave]");

    slot.dataset.pitch = String(planeRow - NOTE_PITCH_TO_GRID_ROW_OFFSET);
    slot.style.top = `${visualRow * cellSize}px`;
    slot.style.height = `${cellSize}px`;
    if (noteElement) noteElement.textContent = note;
    if (flatElement)
      flatElement.style.display = accidental === "flat" ? "" : "none";
    if (octaveElement) octaveElement.textContent = octave;
  });
}

/**
 * Renders the base grid canvas and exposes imperative redraws.
 */
export function NoteGridCanvas({
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  keyPitchClasses,
  beatLength,
  beatsPerMeasure,
  getCellPalette,
  getCellFill,
  onRenderStats,
  layerRef,
  canvasApiRef,
  initialScrollPosition,
  bounds,
}) {
  const canvasRef = useRef(null);
  const canvasWidth = Math.ceil(viewportSize.width + cellSize);
  const canvasHeight = Math.ceil(viewportSize.height + cellSize);

  /**
   * Keeps the private canvas ref and parent layer ref pointed at the same node.
   */
  const setCanvasRefs = useCallback(
    (node) => {
      canvasRef.current = node;
      if (layerRef) {
        layerRef.current = node;
      }
    },
    [layerRef],
  );

  /**
   * Redraws the canvas for a specific scroll position without asking React to render.
   */
  const drawGrid = useCallback(
    (scrollPosition = initialScrollPosition) => {
      drawVisibleGrid({
        canvas: canvasRef.current,
        viewportSize,
        cellSize,
        tileSize,
        cellRadius,
        keyPitchClasses,
        beatLength,
        beatsPerMeasure,
        getCellPalette,
        getCellFill,
        scrollPosition,
        bounds,
        onRenderStats,
      });
    },
    [
      beatLength,
      beatsPerMeasure,
      bounds,
      cellRadius,
      cellSize,
      getCellPalette,
      getCellFill,
      initialScrollPosition,
      keyPitchClasses,
      onRenderStats,
      tileSize,
      viewportSize,
    ],
  );

  useLayoutEffect(() => {
    if (!canvasApiRef) return undefined;

    canvasApiRef.current = {
      draw: drawGrid,
    };

    return () => {
      if (canvasApiRef.current?.draw === drawGrid) {
        canvasApiRef.current = null;
      }
    };
  }, [canvasApiRef, drawGrid]);

  useLayoutEffect(() => {
    drawGrid(initialScrollPosition);
  }, [canvasHeight, canvasWidth, drawGrid, initialScrollPosition]);

  return (
    <div className="note-grid" role="grid" aria-label="Note grid">
      <canvas
        ref={setCanvasRefs}
        className="note-grid-canvas note-grid-layer"
        style={{
          width: canvasWidth,
          height: canvasHeight,
        }}
        aria-hidden="true"
      />
    </div>
  );
}

/**
 * Renders fixed measure labels that update as the grid scrolls.
 */
export function Ticker({
  slotCount,
  cellSize,
  beatLength,
  beatsPerMeasure,
  bounds,
  initialScrollPosition,
  layerRef,
  tickerApiRef,
}) {
  const slotsRef = useRef([]);

  useLayoutEffect(() => {
    if (!tickerApiRef) return undefined;

    slotsRef.current.length = slotCount;
    slotsRef.baseColumn = undefined;
    slotsRef.cellSize = undefined;
    slotsRef.measureSize = undefined;

    tickerApiRef.current = {
      update: (scrollPosition) =>
        updateTickerSlots({
          slots: slotsRef,
          layer: layerRef,
          scrollPosition,
          bounds,
          cellSize,
          beatLength,
          beatsPerMeasure,
        }),
    };
    tickerApiRef.current.update(initialScrollPosition);

    return () => {
      if (tickerApiRef.current?.update) {
        tickerApiRef.current = null;
      }
    };
  }, [
    beatLength,
    beatsPerMeasure,
    bounds,
    cellSize,
    initialScrollPosition,
    slotCount,
    tickerApiRef,
  ]);

  return (
    <div className="note-grid-ticker" aria-label="Measures">
      <div ref={layerRef} className="note-grid-ticker-layer">
        {Array.from({ length: slotCount }, (_, index) => (
          <div
            key={index}
            ref={(node) => {
              slotsRef.current[index] = node;
            }}
            className="note-grid-ticker-item"
          >
            <span />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Formats optional diagnostic numbers without leaking NaN into the debug strip.
 */
function formatNumber(value, digits = 0) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

/**
 * Renders zoom controls and optional note-grid diagnostics.
 */
export function Navigator({
  zoomIndex,
  zoomLevels,
  onZoomChange,
  debugStats,
  showDebugStats = true,
}) {
  const { frameStats, canvasStats, interactionStats } = debugStats;

  return (
    <div className="note-grid-navigator">
      <div className="note-grid-zoom-control" aria-label="Zoom level">
        <ZoomOut size={15} strokeWidth={2.1} aria-hidden="true" />
        <div className="note-grid-zoom-slider">
          <div className="note-grid-zoom-ticks" aria-hidden="true">
            {zoomLevels.map((level, index) => (
              <span
                key={level}
                className={
                  index === zoomIndex
                    ? "note-grid-zoom-tick note-grid-zoom-tick-active"
                    : "note-grid-zoom-tick"
                }
              />
            ))}
          </div>
          <input
            type="range"
            min="0"
            max={zoomLevels.length - 1}
            step="1"
            value={zoomIndex}
            onChange={(event) => onZoomChange(Number(event.target.value))}
            aria-label="Zoom level"
          />
        </div>
        <ZoomIn size={16} strokeWidth={2.1} aria-hidden="true" />
      </div>
      {showDebugStats ? (
        <div className="note-grid-debug" aria-label="Grid debug information">
          <span>{frameStats.fps} fps</span>
          <span>{formatNumber(frameStats.averageFrameMs, 1)} ms avg</span>
          <span>{formatNumber(frameStats.worstFrameMs, 1)} ms worst</span>
          <span>{interactionStats.renders} renders</span>
          <span>{interactionStats.commits} commits</span>
          <span>
            {formatNumber(interactionStats.worstCommitMs, 1)} ms max commit
          </span>
          <span>{formatNumber(canvasStats.drawMs, 1)} ms draw</span>
          <span>{interactionStats.visualRequests} visual req</span>
          <span>{interactionStats.visualFrames} visual frames</span>
          <span>{interactionStats.visualCoalesces} coalesced</span>
        </div>
      ) : null}
    </div>
  );
}
