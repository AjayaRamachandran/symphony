import { Hand, HandGrab, ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import flatIcon from "@/assets/editor-icons/flat.svg?raw";
import {
  INACTIVE_NOTE_COLOR,
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  getChannelColor,
  selectionRectViewportPixels,
} from "./note-grid-note-behavior.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const NOTE_RIGHT_EDGE_OVERSCAN = 12;
const NOTE_LEFT_EDGE_OVERSCAN = 12;

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

  const viewColumn = bounds.minColumn + scrollPosition.x / cellSize;
  const viewRow = bounds.maxRow - scrollPosition.y / cellSize;
  const startColumn = Math.floor(viewColumn);
  const startRow = Math.ceil(viewRow);
  const cellPalette = getCellPalette();
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

function projectNoteToScreen({ note, viewportSize, cellSize, tileSize, cellRadius, bounds, scrollPosition }) {
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

  const fullWidth = note.duration * cellSize - Math.max(1, cellSize - tileSize);
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

function getVisibleNotes({ notes, viewportSize, cellSize, tileSize, cellRadius, bounds, scrollPosition, activeChannel, selectionOverride, hiddenKeys }) {
  if (!viewportSize.width || !viewportSize.height || !cellSize) return [];

  const result = [];
  for (const note of notes) {
    if (hiddenKeys && hiddenKeys.has(note.key)) continue;

    const projection = projectNoteToScreen({ note, viewportSize, cellSize, tileSize, cellRadius, bounds, scrollPosition });
    if (!projection) continue;

    const inactive = activeChannel != null && note.color !== activeChannel;
    const fill = inactive ? INACTIVE_NOTE_COLOR : getChannelColor(note.color);
    const selected = note.selected || (selectionOverride ? selectionOverride.has(note.key) : false);

    result.push({
      key: note.key,
      ...projection,
      color: fill,
      selected,
      inactive,
    });
  }

  // Inactive context notes render first so the active channel sits on top.
  result.sort((a, b) => {
    if (a.inactive !== b.inactive) return a.inactive ? -1 : 1;
    if (a.selected !== b.selected) return a.selected ? 1 : -1;
    return 0;
  });

  return result;
}

const TAIL_AFFORDANCE_WIDTH = 2.5;
const TAIL_AFFORDANCE_INSET = 5;

function getVisibleNoteSignature(visibleNotes, selectMode) {
  return `${selectMode ? "S" : "N"}|` + visibleNotes
    .map(
      (note) =>
        `${note.key}:${note.x.toFixed(2)}:${note.y.toFixed(2)}:${note.width.toFixed(2)}:${note.height.toFixed(2)}:${note.color}:${note.selected ? 1 : 0}:${note.inactive ? 1 : 0}`,
    )
    .join("|");
}

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

    // Tail-resize affordance: a darker bar inset from the right edge of the
    // note fill. Visible in select mode so users discover they can drag the
    // tail to extend/retract selected notes.
    if (selectMode && !note.inactive && note.width > TAIL_AFFORDANCE_INSET + TAIL_AFFORDANCE_WIDTH + 1) {
      const tail = document.createElementNS(SVG_NS, "rect");
      tail.setAttribute("class", "note-grid-note-tail-affordance");
      tail.setAttribute("x", String(note.x + note.width - TAIL_AFFORDANCE_INSET - TAIL_AFFORDANCE_WIDTH));
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

function drawGhostNotes(svg, ghosts) {
  if (!svg) return;

  const fragment = document.createDocumentFragment();
  ghosts.forEach((ghost) => {
    const rect = document.createElementNS(SVG_NS, "rect");
    const classes = ["note-grid-note"];
    classes.push(ghost.variant === "preview" ? "note-grid-note-drag-preview" : "note-grid-note-ghost");
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

    slot.dataset.pitch = String(planeRow - NOTE_PITCH_TO_GRID_ROW_OFFSET);
    slot.style.top = `${visualRow * cellSize}px`;
    slot.style.height = `${cellSize}px`;
    if (noteElement) noteElement.textContent = note;
    if (flatElement) flatElement.style.display = accidental === "flat" ? "" : "none";
    if (octaveElement) octaveElement.textContent = octave;
  });
}

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

export function NoteGridNotes({
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
      const nextSignature = getVisibleNoteSignature(nextVisibleNotes, selectMode);

      if (nextSignature === visibleSignatureRef.current) return;

      visibleSignatureRef.current = nextSignature;
      drawVisibleNotes(svgRef.current, nextVisibleNotes, selectMode);
    },
    [activeChannel, bounds, cellRadius, cellSize, hiddenKeysRef, initialScrollPosition, notes, selectMode, selectionOverrideRef, tileSize, viewportSize],
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

export function NoteGridOverlay({
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
          const projection = projectNoteToScreen({ note, viewportSize, cellSize, tileSize, cellRadius, bounds, scrollPosition });
          if (!projection) continue;
          ghostList.push({
            ...projection,
            color: getChannelColor(ghost.color),
            variant: ghost.variant,
          });
        }
      }
      const ghostSignature = ghostList
        .map((g) => `${g.x.toFixed(2)}:${g.y.toFixed(2)}:${g.width.toFixed(2)}:${g.color}:${g.variant ?? "ghost"}`)
        .join("|");
      if (ghostSignature !== ghostSignatureRef.current || (ghostSignature === "" && svgRef.current?.childNodes.length)) {
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
    [bounds, cellRadius, cellSize, ghostNotesRef, initialScrollPosition, selectionRectRef, tileSize, viewportSize],
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

export function NoteGridPlayhead({
  viewportSize,
  cellSize,
  bounds,
  initialScrollPosition,
  playheadApiRef,
  playheadHomeTime = 0,
  isPlaying = false,
  playbackClock = null,
  tempo = 360,
}) {
  const lineRef = useRef(null);
  const scrollPositionRef = useRef(initialScrollPosition);
  const homeTimeRef = useRef(Number(playheadHomeTime) || 0);
  const playbackRef = useRef({
    isPlaying,
    playbackClock,
    tempo,
  });

  const placePlayhead = useCallback(
    (time) => {
      const line = lineRef.current;
      if (!line || !viewportSize.width || !cellSize) return;

      const scrollPosition = scrollPositionRef.current;
      const x = (time - bounds.minColumn) * cellSize - scrollPosition.x;
      const overscan = 2;
      const visible = x >= -overscan && x <= viewportSize.width + overscan;

      line.dataset.visible = visible ? "true" : "false";
      line.style.transform = `translate3d(${x}px, 0, 0)`;
    },
    [bounds.minColumn, cellSize, viewportSize.width],
  );

  useLayoutEffect(() => {
    homeTimeRef.current = Number(playheadHomeTime) || 0;
    placePlayhead(homeTimeRef.current);
  }, [placePlayhead, playheadHomeTime]);

  useLayoutEffect(() => {
    playbackRef.current = {
      isPlaying,
      playbackClock,
      tempo,
    };

    if (!isPlaying || !playbackClock) {
      placePlayhead(homeTimeRef.current);
    }
  }, [isPlaying, playbackClock, placePlayhead, tempo]);

  useLayoutEffect(() => {
    if (!playheadApiRef) return undefined;

    playheadApiRef.current = {
      update: (scrollPosition) => {
        scrollPositionRef.current = scrollPosition;
        const { isPlaying: playing, playbackClock: clock, tempo: currentTempo } = playbackRef.current;
        if (!playing || !clock) {
          placePlayhead(homeTimeRef.current);
          return;
        }

        const elapsedSeconds = Math.max(0, (performance.now() - clock.startedAtMs) / 1000);
        placePlayhead(clock.fromTime + elapsedSeconds * (Math.max(1, Number(currentTempo) || 1) / 60));
      },
      setHome: (time) => {
        homeTimeRef.current = Number(time) || 0;
        placePlayhead(homeTimeRef.current);
      },
    };

    playheadApiRef.current.update(initialScrollPosition);

    return () => {
      if (playheadApiRef.current?.update) {
        playheadApiRef.current = null;
      }
    };
  }, [initialScrollPosition, placePlayhead, playheadApiRef]);

  useEffect(() => {
    if (!isPlaying || !playbackClock) return undefined;

    let animationFrame = 0;
    const tick = () => {
      const elapsedSeconds = Math.max(0, (performance.now() - playbackClock.startedAtMs) / 1000);
      placePlayhead(playbackClock.fromTime + elapsedSeconds * (Math.max(1, Number(tempo) || 1) / 60));
      animationFrame = requestAnimationFrame(tick);
    };

    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, [isPlaying, playbackClock, placePlayhead, tempo]);

  return (
    <div
      ref={lineRef}
      className="note-grid-playhead"
      data-visible="false"
      style={{ height: viewportSize.height }}
      aria-hidden="true"
    />
  );
}

export function Ticker({ slotCount, cellSize, beatLength, beatsPerMeasure, bounds, initialScrollPosition, layerRef, tickerApiRef }) {
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
  }, [beatLength, beatsPerMeasure, bounds, cellSize, initialScrollPosition, slotCount, tickerApiRef]);

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

export function PitchList({ slotCount, cellSize, bounds, initialScrollPosition, layerRef, pitchApiRef, onPreviewPitch = null }) {
  const slotsRef = useRef([]);

  const handlePointerDown = useCallback(
    (event) => {
      if (event.button !== 0) return;
      const pitchRow = event.target.closest(".note-grid-pitch-row");
      const pitch = Number(pitchRow?.dataset.pitch);
      if (!Number.isFinite(pitch)) return;
      onPreviewPitch?.(pitch);
    },
    [onPreviewPitch],
  );

  useLayoutEffect(() => {
    if (!pitchApiRef) return undefined;

    slotsRef.current.length = slotCount;
    slotsRef.baseRow = undefined;
    slotsRef.cellSize = undefined;

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
  }, [bounds, cellSize, initialScrollPosition, pitchApiRef, slotCount]);

  return (
    <div className="note-grid-pitch-list" onPointerDown={handlePointerDown} aria-label="Pitches">
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

export function Navigator({ zoomIndex, zoomLevels, onZoomChange, debugStats, showDebugStats = true }) {
  const {
    frameStats,
    canvasStats,
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
      {showDebugStats ? (
        <div className="note-grid-debug" aria-label="Grid debug information">
          <span>{frameStats.fps} fps</span>
          <span>{formatNumber(frameStats.averageFrameMs, 1)} ms avg</span>
          <span>{formatNumber(frameStats.worstFrameMs, 1)} ms worst</span>
          <span>{interactionStats.renders} renders</span>
          <span>{interactionStats.commits} commits</span>
          <span>{formatNumber(interactionStats.worstCommitMs, 1)} ms max commit</span>
          <span>{formatNumber(canvasStats.drawMs, 1)} ms draw</span>
          <span>{interactionStats.visualRequests} visual req</span>
          <span>{interactionStats.visualFrames} visual frames</span>
          <span>{interactionStats.visualCoalesces} coalesced</span>
        </div>
      ) : null}
    </div>
  );
}

export function OverlayScrollbar({ viewportWidth, scrollX, maxScrollX, onScrollXChange, thumbRef }) {
  const trackRef = useRef(null);
  const dragOffsetRef = useRef(0);
  const [cursorState, setCursorState] = useState({ visible: false, grabbing: false, x: 0, y: 0 });
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

  const syncCursor = useCallback((event, nextState = {}) => {
    const track = trackRef.current;
    if (!track) return;

    const rect = track.getBoundingClientRect();
    setCursorState((current) => ({
      ...current,
      visible: true,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      ...nextState,
    }));
  }, []);

  const releaseCursor = useCallback((event) => {
    const track = trackRef.current;
    if (!track) {
      setCursorState((current) => ({ ...current, visible: false, grabbing: false }));
      return;
    }

    const rect = track.getBoundingClientRect();
    const pointerInside =
      event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;

    setCursorState((current) => ({
      ...current,
      visible: pointerInside,
      grabbing: false,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }));
  }, []);

  const ScrollbarCursorIcon = cursorState.grabbing ? HandGrab : Hand;

  return (
    <div
      ref={trackRef}
      className="note-grid-overlay-scrollbar"
      aria-hidden="true"
      onPointerEnter={syncCursor}
      onPointerMove={syncCursor}
      onPointerLeave={() => {
        setCursorState((current) => (current.grabbing ? current : { ...current, visible: false }));
      }}
    >
      <div
        ref={thumbRef}
        className="note-grid-overlay-scrollbar-thumb"
        onPointerDown={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          if (!rect) return;

          event.currentTarget.setPointerCapture(event.pointerId);
          dragOffsetRef.current = clamp(event.clientX - rect.left, 0, thumbWidth);
          syncCursor(event, { grabbing: true });
        }}
        onPointerMove={(event) => {
          if (event.buttons !== 1) return;
          syncPointer(event.clientX);
          syncCursor(event, { grabbing: true });
        }}
        onPointerUp={releaseCursor}
        onPointerCancel={() => {
          setCursorState((current) => ({ ...current, visible: false, grabbing: false }));
        }}
        onLostPointerCapture={releaseCursor}
        style={{
          width: thumbWidth,
          transform: `translateX(var(--note-grid-scrollbar-thumb-x, ${thumbLeft}px))`,
        }}
      />
      <div
        className="note-grid-overlay-scrollbar-cursor"
        data-visible={cursorState.visible ? "true" : "false"}
        style={{ left: cursorState.x, top: cursorState.y }}
      >
        <ScrollbarCursorIcon className="note-grid-overlay-scrollbar-cursor-outline" aria-hidden="true" />
        <ScrollbarCursorIcon className="note-grid-overlay-scrollbar-cursor-fill" aria-hidden="true" />
      </div>
    </div>
  );
}
