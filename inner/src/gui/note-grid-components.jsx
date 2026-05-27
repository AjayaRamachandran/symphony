import { ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useLayoutEffect, useMemo, useRef } from "react";
import flatIcon from "@/assets/editor-icons/flat.svg?raw";

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

function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

const OVERLAY_SCROLLBAR_TRACK_INSET = 6;

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

  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize;
  const viewRow = bounds.maxRow - scrollPosition.y / cellSize;
  const startColumn = Math.floor(viewColumn);
  const startRow = Math.ceil(viewRow);
  let drawCount = 0;

  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, canvasWidth, canvasHeight);

  for (let planeRow = startRow; (viewRow - planeRow) * cellSize < viewportSize.height; planeRow -= 1) {
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
  context.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  context.lineTo(x + safeRadius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  context.lineTo(x, y + safeRadius);
  context.quadraticCurveTo(x, y, x + safeRadius, y);
  context.closePath();
  context.fill();
}

function getPitchLabel(row) {
  const pitchClass = PITCH_CLASS_LABELS[positiveModulo(row, 12)];
  const octave = Math.floor(row / 12) - 1;
  return { ...pitchClass, octave };
}

/**
 * Updates fixed ticker slots using modular camera movement. The layer transform
 * changes every frame, while labels only change when the integer column changes.
 */
function updateTickerSlots({ slots, layer, scrollPosition, bounds, cellSize, beatLength, beatsPerMeasure }) {
  const beatSize = Math.max(1, Number(beatLength) || 1);
  const measureSize = beatSize * Math.max(1, Number(beatsPerMeasure) || 1);
  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize;
  const startColumn = Math.floor(viewColumn);
  const fractionalColumn = viewColumn - startColumn;

  if (layer.current) {
    layer.current.style.transform = `translate3d(${-fractionalColumn * cellSize}px, 0, 0)`;
  }

  if (slots.baseColumn === startColumn && slots.cellSize === cellSize && slots.measureSize === measureSize) {
    return;
  }

  slots.baseColumn = startColumn;
  slots.cellSize = cellSize;
  slots.measureSize = measureSize;

  slots.current.forEach((slot, visualColumn) => {
    if (!slot) return;

    const planeColumn = startColumn + visualColumn;
    const isMeasureStart = positiveModulo(planeColumn, measureSize) === 0;
    slot.style.left = `${visualColumn * cellSize}px`;
    slot.style.display = isMeasureStart ? "" : "none";
    slot.textContent = isMeasureStart ? String(Math.floor(planeColumn / measureSize) + 1) : "";
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
    layer.current.style.transform = `translate3d(0, ${fractionalRow * cellSize}px, 0)`;
  }

  if (slots.baseRow === startRow && slots.cellSize === cellSize) {
    return;
  }

  slots.baseRow = startRow;
  slots.cellSize = cellSize;

  slots.current.forEach((slot, visualRow) => {
    if (!slot) return;

    const planeRow = startRow - visualRow;
    const { note, accidental, octave } = getPitchLabel(planeRow);
    const noteElement = slot.querySelector("[data-pitch-note]");
    const flatElement = slot.querySelector("[data-pitch-flat]");
    const octaveElement = slot.querySelector("[data-pitch-octave]");

    slot.style.top = `${visualRow * cellSize}px`;
    slot.style.height = `${cellSize}px`;
    if (noteElement) noteElement.textContent = note;
    if (flatElement) flatElement.style.display = accidental === "flat" ? "" : "none";
    if (octaveElement) octaveElement.textContent = octave;
  });
}

function FlatIcon() {
  return <span className="note-grid-pitch-flat" dangerouslySetInnerHTML={{ __html: flatIcon }} />;
}

function PitchLabel({ row }) {
  const { note, accidental, octave } = getPitchLabel(row);

  return (
    <span className="note-grid-pitch-label">
      <span className="note-grid-pitch-note">{note}</span>
      {accidental === "flat" && <FlatIcon />}
      <span className="note-grid-pitch-octave">{octave}</span>
    </span>
  );
}

export function NoteGridCanvas({
  viewportSize,
  cellSize,
  tileSize,
  cellRadius,
  keyPitchClasses,
  beatLength,
  beatsPerMeasure,
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

export function Ticker({ slotCount, cellSize, beatLength, beatsPerMeasure, bounds, initialScrollPosition, layerRef, tickerApiRef }) {
  const slotsRef = useRef([]);

  useLayoutEffect(() => {
    if (!tickerApiRef) return undefined;

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
  }, [beatLength, beatsPerMeasure, bounds, cellSize, initialScrollPosition, tickerApiRef]);

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

export function PitchList({ slotCount, cellSize, bounds, initialScrollPosition, layerRef, pitchApiRef }) {
  const slotsRef = useRef([]);

  useLayoutEffect(() => {
    if (!pitchApiRef) return undefined;

    pitchApiRef.current = {
      update: (scrollPosition) =>
        updatePitchSlots({
          slots: slotsRef,
          layer: layerRef,
          scrollPosition,
          bounds,
          cellSize,
        }),
    };
    pitchApiRef.current.update(initialScrollPosition);

    return () => {
      if (pitchApiRef.current?.update) {
        pitchApiRef.current = null;
      }
    };
  }, [bounds, cellSize, initialScrollPosition, pitchApiRef]);

  return (
    <div className="note-grid-pitch-list" aria-label="Pitches">
      <div ref={layerRef} className="note-grid-pitch-list-layer">
        {Array.from({ length: slotCount }, (_, visualRow) => (
          <div
            key={visualRow}
            ref={(node) => {
              slotsRef.current[visualRow] = node;
            }}
            className="note-grid-pitch-row"
          >
            <span className="note-grid-pitch-label">
              <span data-pitch-note className="note-grid-pitch-note" />
              <span data-pitch-flat className="note-grid-pitch-flat" dangerouslySetInnerHTML={{ __html: flatIcon }} />
              <span data-pitch-octave className="note-grid-pitch-octave" />
            </span>
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

export function Navigator({ zoomIndex, zoomLevels, onZoomChange, debugStats }) {
  const {
    frameStats,
    canvasStats,
    cellSize,
    interactionStats,
  } = debugStats;

  return (
    <div className="note-grid-navigator">
      <div className="note-grid-zoom-control" aria-label="Zoom level">
        <ZoomOut size={15} strokeWidth={2.1} aria-hidden="true" />
        <div className="note-grid-zoom-slider">
          <div className="note-grid-zoom-ticks" aria-hidden="true">
            {zoomLevels.map((level, index) => (
              <span
                key={level}
                className={index === zoomIndex ? "note-grid-zoom-tick note-grid-zoom-tick-active" : "note-grid-zoom-tick"}
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
      <div className="note-grid-debug" aria-label="Grid debug information">
        <span>{frameStats.fps} fps</span>
        <span>{formatNumber(frameStats.averageFrameMs, 1)} ms avg</span>
        <span>{formatNumber(frameStats.worstFrameMs, 1)} ms worst</span>
        <span>{frameStats.longFrames} long</span>
        <span>{interactionStats.renders} renders</span>
        <span>{interactionStats.commits} commits</span>
        <span>{formatNumber(interactionStats.worstCommitMs, 1)} ms max commit</span>
        <span>{formatNumber(canvasStats.drawMs, 1)} ms draw</span>
        <span>{interactionStats.wheelEvents} wheels</span>
        <span>{interactionStats.originChanges} origins</span>
        <span>{interactionStats.visualRequests} visual req</span>
        <span>{interactionStats.visualFrames} visual frames</span>
        <span>{interactionStats.visualCoalesces} coalesced</span>
        <span>{interactionStats.longTasks} long tasks</span>
        <span>{formatNumber(interactionStats.worstLongTaskMs, 1)} ms max task</span>
        <span>{cellSize}px zoom</span>
      </div>
    </div>
  );
}

export function OverlayScrollbar({ viewportWidth, scrollX, maxScrollX, onScrollXChange, thumbRef }) {
  const trackRef = useRef(null);
  const dragOffsetRef = useRef(0);
  const trackWidth = Math.max(0, viewportWidth - OVERLAY_SCROLLBAR_TRACK_INSET * 2);

  const thumbWidth = useMemo(() => {
    if (trackWidth <= 0 || maxScrollX <= 0) return trackWidth;
    const contentWidth = viewportWidth + maxScrollX;
    return clamp((viewportWidth / contentWidth) * trackWidth, 44, trackWidth);
  }, [maxScrollX, trackWidth, viewportWidth]);

  const thumbLeft = useMemo(() => {
    if (maxScrollX <= 0 || trackWidth <= thumbWidth) return 0;
    return (scrollX / maxScrollX) * (trackWidth - thumbWidth);
  }, [maxScrollX, scrollX, thumbWidth, trackWidth]);

  const syncPointer = useCallback(
    (clientX) => {
      const track = trackRef.current;
      if (!track || maxScrollX <= 0) return;

      const rect = track.getBoundingClientRect();
      const maxThumbLeft = Math.max(0, rect.width - thumbWidth);
      const nextLeft = clamp(clientX - rect.left - dragOffsetRef.current, 0, maxThumbLeft);
      const nextScrollX = (nextLeft / Math.max(1, maxThumbLeft)) * maxScrollX;
      onScrollXChange(nextScrollX);
    },
    [maxScrollX, onScrollXChange, thumbWidth],
  );

  return (
    <div
      ref={trackRef}
      className="note-grid-overlay-scrollbar"
      aria-hidden="true"
    >
      <div
        ref={thumbRef}
        className="note-grid-overlay-scrollbar-thumb"
        onPointerDown={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          if (!rect) return;

          event.currentTarget.setPointerCapture(event.pointerId);
          dragOffsetRef.current = clamp(event.clientX - rect.left, 0, thumbWidth);
        }}
        onPointerMove={(event) => {
          if (event.buttons !== 1) return;
          syncPointer(event.clientX);
        }}
        style={{
          width: thumbWidth,
          transform: `translateX(var(--note-grid-scrollbar-thumb-x, ${thumbLeft}px))`,
        }}
      />
    </div>
  );
}
