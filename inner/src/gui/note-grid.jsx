import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Navigator,
  NoteGridCanvas,
  OverlayScrollbar,
  PitchList,
  Ticker,
} from "./note-grid-components.jsx";
import "./note-grid.css";

const ZOOM_LEVELS = [20, 26, 32, 40, 48];
const DEFAULT_ZOOM_INDEX = 2;
const TILE_GAP = 1;
const CELL_RADIUS = 3;
const MAX_COLUMN = 128;
const MIN_COLUMN = 0;
const MAX_ROW = 96;
const MIN_BOTTOM_ROW = 12;
const DEFAULT_TOP_ROW = 96;
const DEFAULT_COLUMN = 0;
const OVERLAY_SCROLLBAR_TRACK_INSET = 6;
const MIN_SCROLLBAR_THUMB_WIDTH = 44;

const KEY_ROOTS = {
  C: 0,
  Db: 1,
  D: 2,
  Eb: 3,
  E: 4,
  F: 5,
  Gb: 6,
  G: 7,
  Ab: 8,
  A: 9,
  Bb: 10,
  B: 11,
};

const MODE_INTERVALS = {
  Lydian: [0, 2, 4, 6, 7, 9, 11],
  "Ionian (maj.)": [0, 2, 4, 5, 7, 9, 11],
  Mixolydian: [0, 2, 4, 5, 7, 9, 10],
  Dorian: [0, 2, 3, 5, 7, 9, 10],
  "Aeolian (min.)": [0, 2, 3, 5, 7, 8, 10],
  Phrygian: [0, 1, 3, 5, 7, 8, 10],
  Locrian: [0, 1, 3, 5, 6, 8, 10],
};

function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function getViewportCellCounts(size, cellSize) {
  return {
    columns: Math.ceil(size.width / cellSize) + 1,
    rows: Math.ceil(size.height / cellSize) + 1,
  };
}

function getMaxScrollX(viewportWidth, cellSize) {
  const contentWidth = (MAX_COLUMN - MIN_COLUMN + 1) * cellSize;
  return Math.max(0, contentWidth - viewportWidth);
}

function getMaxScrollY(viewportHeight, cellSize) {
  const contentHeight = (MAX_ROW - MIN_BOTTOM_ROW + 1) * cellSize;
  return Math.max(0, contentHeight - viewportHeight);
}

function getKeyPitchClasses(key, mode) {
  const root = KEY_ROOTS[key] ?? KEY_ROOTS.C;
  const intervals = MODE_INTERVALS[mode] ?? MODE_INTERVALS["Ionian (maj.)"];
  return new Set(intervals.map((interval) => (root + interval) % 12));
}

function getCellFill({ column, row, keyPitchClasses, beatLength, beatsPerMeasure }) {
  const beatSize = Math.max(1, Number(beatLength) || 1);
  const measureSize = beatSize * Math.max(1, Number(beatsPerMeasure) || 1);
  const isBeatStart = positiveModulo(column, beatSize) === 0;
  const isDownBeat = positiveModulo(column, measureSize) === 0;
  const isInKey = keyPitchClasses.has(positiveModulo(row, 12));
  const lightness = 12 + (isBeatStart ? 4 : 0) + (isInKey ? 5 : 0) + (isDownBeat ? 7 : 0);

  return `hsl(0 0% ${lightness}%)`;
}

/**
 * Tracks frame pacing without coupling the grid canvas to React's render loop.
 */
function useFrameStats() {
  const [frameStats, setFrameStats] = useState({
    fps: 0,
    averageFrameMs: 0,
    worstFrameMs: 0,
    longFrames: 0,
  });

  useEffect(() => {
    let animationFrame = 0;
    let frames = 0;
    let measuredFrames = 0;
    let totalFrameMs = 0;
    let worstFrameMs = 0;
    let longFrames = 0;
    let lastSample = performance.now();
    let lastFrame = lastSample;

    const tick = (time) => {
      const frameMs = time - lastFrame;
      lastFrame = time;
      frames += 1;

      if (frameMs > 0) {
        measuredFrames += 1;
        totalFrameMs += frameMs;
        worstFrameMs = Math.max(worstFrameMs, frameMs);
        if (frameMs > 24) {
          longFrames += 1;
        }
      }

      if (time - lastSample >= 500) {
        setFrameStats({
          fps: Math.round((frames * 1000) / (time - lastSample)),
          averageFrameMs: totalFrameMs / Math.max(1, measuredFrames),
          worstFrameMs,
          longFrames,
        });
        frames = 0;
        measuredFrames = 0;
        totalFrameMs = 0;
        worstFrameMs = 0;
        longFrames = 0;
        lastSample = time;
      }

      animationFrame = requestAnimationFrame(tick);
    };

    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  return frameStats;
}

/**
 * Creates a fresh diagnostics bucket for one debug sampling window.
 */
function createInteractionStats() {
  return {
    renders: 0,
    commits: 0,
    averageCommitMs: 0,
    worstCommitMs: 0,
    resizeEvents: 0,
    wheelEvents: 0,
    scrollSyncs: 0,
    originChanges: 0,
    opticalUpdates: 0,
    scrollbarUpdates: 0,
    viewportUpdates: 0,
    scrollStateUpdates: 0,
    canvasStatUpdates: 0,
    debugStatUpdates: 0,
    visualRequests: 0,
    visualFrames: 0,
    visualCoalesces: 0,
    averageWheelMs: 0,
    worstWheelMs: 0,
    averageOffsetMs: 0,
    worstOffsetMs: 0,
    averageScrollbarMs: 0,
    worstScrollbarMs: 0,
    longTasks: 0,
    averageLongTaskMs: 0,
    worstLongTaskMs: 0,
    wheelTotalMs: 0,
    offsetTotalMs: 0,
    scrollbarTotalMs: 0,
    longTaskTotalMs: 0,
  };
}

/**
 * Records a measured duration into a diagnostics bucket.
 */
function recordTimedStat(stats, countKey, totalKey, averageKey, worstKey, duration) {
  stats[totalKey] += duration;
  stats[averageKey] = stats[totalKey] / Math.max(1, stats[countKey]);
  stats[worstKey] = Math.max(stats[worstKey], duration);
}

export default function NoteGridSurface({
  beatLength = 4,
  beatsPerMeasure = 4,
  keySignature = "C",
  mode = "Ionian (maj.)",
}) {
  const surfaceRef = useRef(null);
  const viewportRef = useRef(null);
  const tickerLayerRef = useRef(null);
  const pitchLayerRef = useRef(null);
  const tickerApiRef = useRef(null);
  const pitchApiRef = useRef(null);
  const canvasLayerRef = useRef(null);
  const canvasApiRef = useRef(null);
  const canvasStatsRef = useRef({
    drawMs: 0,
    drawCount: 0,
    canvasWidth: 0,
    canvasHeight: 0,
    backingWidth: 0,
    backingHeight: 0,
    pixelRatio: 1,
  });
  const scrollbarThumbRef = useRef(null);
  const scrollPositionRef = useRef({ x: DEFAULT_COLUMN * ZOOM_LEVELS[DEFAULT_ZOOM_INDEX], y: 0 });
  const originRef = useRef({ row: DEFAULT_TOP_ROW, column: DEFAULT_COLUMN });
  const visualDirtyRef = useRef(true);
  const visualLoopRef = useRef(0);
  const previousCellSizeRef = useRef(ZOOM_LEVELS[DEFAULT_ZOOM_INDEX]);
  const interactionCountersRef = useRef(createInteractionStats());
  const [zoomIndex, setZoomIndex] = useState(DEFAULT_ZOOM_INDEX);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [interactionStats, setInteractionStats] = useState(createInteractionStats);

  const renderStart = performance.now();
  interactionCountersRef.current.renders += 1;
  const frameStats = useFrameStats();
  const [sampledCanvasStats, setSampledCanvasStats] = useState({
    drawMs: 0,
    drawCount: 0,
    canvasWidth: 0,
    canvasHeight: 0,
    backingWidth: 0,
    backingHeight: 0,
    pixelRatio: 1,
  });

  /**
   * Stores canvas render diagnostics without scheduling a React update.
   */
  const updateCanvasStats = useCallback((nextCanvasStats) => {
    interactionCountersRef.current.canvasStatUpdates += 1;
    canvasStatsRef.current = nextCanvasStats;
  }, []);
  const cellSize = ZOOM_LEVELS[zoomIndex];
  const tileSize = cellSize - TILE_GAP;
  const cellRadius = Math.min(CELL_RADIUS, Math.max(2, Math.round(cellSize * 0.08)));
  const cellCounts = useMemo(() => getViewportCellCounts(viewportSize, cellSize), [cellSize, viewportSize]);
  const maxScrollX = useMemo(() => getMaxScrollX(viewportSize.width, cellSize), [cellSize, viewportSize.width]);
  const maxScrollY = useMemo(() => getMaxScrollY(viewportSize.height, cellSize), [cellSize, viewportSize.height]);
  const keyPitchClasses = useMemo(() => getKeyPitchClasses(keySignature, mode), [keySignature, mode]);
  const gridBounds = useMemo(
    () => ({
      minColumn: MIN_COLUMN,
      maxRow: MAX_ROW,
    }),
    [],
  );

  const objectCount = 1 + cellCounts.columns + cellCounts.rows;
  const visibleCellCount = cellCounts.columns * cellCounts.rows;
  const debugStats = useMemo(
    () => ({
      objectCount,
      frameStats,
      canvasStats: sampledCanvasStats,
      visibleCellCount,
      columns: cellCounts.columns,
      rows: cellCounts.rows,
      viewportWidth: viewportSize.width,
      viewportHeight: viewportSize.height,
      cellSize,
      interactionStats,
      row: originRef.current.row,
      column: originRef.current.column,
    }),
    [
      cellSize,
      cellCounts.columns,
      cellCounts.rows,
      frameStats,
      interactionStats,
      objectCount,
      sampledCanvasStats,
      viewportSize.height,
      viewportSize.width,
      visibleCellCount,
    ],
  );

  /**
   * Moves the overlay scrollbar thumb directly so wheel input does not commit React work.
   */
  const applyScrollbarOffset = useCallback(
    (scrollX) => {
      const thumb = scrollbarThumbRef.current;
      if (!thumb) return;

      const start = performance.now();
      const trackWidth = Math.max(0, viewportSize.width - OVERLAY_SCROLLBAR_TRACK_INSET * 2);
      const contentWidth = viewportSize.width + maxScrollX;
      const thumbWidth =
        trackWidth <= 0 || maxScrollX <= 0
          ? trackWidth
          : clamp((viewportSize.width / contentWidth) * trackWidth, MIN_SCROLLBAR_THUMB_WIDTH, trackWidth);
      const thumbLeft = maxScrollX <= 0 || trackWidth <= thumbWidth ? 0 : (scrollX / maxScrollX) * (trackWidth - thumbWidth);

      interactionCountersRef.current.scrollbarUpdates += 1;
      thumb.style.transform = `translateX(${thumbLeft}px)`;
      recordTimedStat(
        interactionCountersRef.current,
        "scrollbarUpdates",
        "scrollbarTotalMs",
        "averageScrollbarMs",
        "worstScrollbarMs",
        performance.now() - start,
      );
    },
    [maxScrollX, viewportSize.width],
  );

  /**
   * Marks scroll visuals dirty; the persistent rAF loop will draw the latest
   * scroll position once on the next frame.
   */
  const scheduleVisualUpdate = useCallback(() => {
    interactionCountersRef.current.visualRequests += 1;

    if (visualDirtyRef.current) {
      interactionCountersRef.current.visualCoalesces += 1;
    }

    visualDirtyRef.current = true;
  }, []);

  /**
   * Updates scroll refs, redraws the canvas from the current camera position,
   * and keeps hot-path movement out of React state.
   */
  const syncScrollPosition = useCallback(
    (nextScrollX, nextScrollY) => {
      interactionCountersRef.current.scrollSyncs += 1;
      const clampedX = clamp(nextScrollX, 0, maxScrollX);
      const clampedY = clamp(nextScrollY, 0, maxScrollY);
      const nextOrigin = {
        column: MIN_COLUMN + Math.floor(clampedX / cellSize),
        row: MAX_ROW - Math.floor(clampedY / cellSize),
      };

      const previousScrollPosition = scrollPositionRef.current;
      if (previousScrollPosition.x !== clampedX || previousScrollPosition.y !== clampedY) {
        scrollPositionRef.current = { x: clampedX, y: clampedY };
      }
      const originChanged = nextOrigin.row !== originRef.current.row || nextOrigin.column !== originRef.current.column;

      scheduleVisualUpdate();

      if (originChanged) {
        interactionCountersRef.current.originChanges += 1;
        originRef.current = nextOrigin;
      }
    },
    [cellSize, maxScrollX, maxScrollY, scheduleVisualUpdate],
  );

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;

    const resizeObserver = new ResizeObserver(([entry]) => {
      interactionCountersRef.current.resizeEvents += 1;
      const nextWidth = entry.contentRect.width;
      const nextHeight = entry.contentRect.height;

      setViewportSize((current) => {
        if (current.width === nextWidth && current.height === nextHeight) {
          return current;
        }

        interactionCountersRef.current.viewportUpdates += 1;
        return {
          width: nextWidth,
          height: nextHeight,
        };
      });
    });

    resizeObserver.observe(viewport);
    return () => resizeObserver.disconnect();
  }, []);

  useLayoutEffect(() => {
    const counters = interactionCountersRef.current;
    const commitMs = performance.now() - renderStart;
    counters.commits += 1;
    counters.averageCommitMs += commitMs;
    counters.worstCommitMs = Math.max(counters.worstCommitMs, commitMs);
  });

  useLayoutEffect(() => {
    const previousCellSize = previousCellSizeRef.current;

    if (previousCellSize !== cellSize) {
      const current = scrollPositionRef.current;
      scrollPositionRef.current = {
        x: (current.x / previousCellSize) * cellSize,
        y: (current.y / previousCellSize) * cellSize,
      };
      previousCellSizeRef.current = cellSize;
    }

    syncScrollPosition(scrollPositionRef.current.x, scrollPositionRef.current.y);
  }, [cellSize, syncScrollPosition, viewportSize.height, viewportSize.width]);

  useLayoutEffect(() => {
    scheduleVisualUpdate();
  }, [scheduleVisualUpdate]);

  useEffect(() => {
    /**
     * Flushes coalesced visual work at most once per animation frame.
     */
    const tick = () => {
      if (visualDirtyRef.current) {
        visualDirtyRef.current = false;
        const { x, y } = scrollPositionRef.current;
        interactionCountersRef.current.visualFrames += 1;
        applyScrollbarOffset(x);
        tickerApiRef.current?.update({ x, y });
        pitchApiRef.current?.update({ x, y });
        canvasApiRef.current?.draw({ x, y });
      }

      visualLoopRef.current = requestAnimationFrame(tick);
    };

    visualLoopRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(visualLoopRef.current);
      visualLoopRef.current = 0;
      visualDirtyRef.current = false;
    };
  }, [applyScrollbarOffset]);

  /**
   * Handles wheel input without storing the current scroll position in React state.
   */
  const handleWheel = useCallback((event) => {
    const start = performance.now();
    event.preventDefault();
    interactionCountersRef.current.wheelEvents += 1;
    syncScrollPosition(scrollPositionRef.current.x + event.deltaX, scrollPositionRef.current.y + event.deltaY);
    recordTimedStat(
      interactionCountersRef.current,
      "wheelEvents",
      "wheelTotalMs",
      "averageWheelMs",
      "worstWheelMs",
      performance.now() - start,
    );
  }, [syncScrollPosition]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  useEffect(() => {
    if (typeof PerformanceObserver === "undefined" || !PerformanceObserver.supportedEntryTypes?.includes("longtask")) {
      return undefined;
    }

    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        const counters = interactionCountersRef.current;
        counters.longTasks += 1;
        counters.longTaskTotalMs += entry.duration;
        counters.averageLongTaskMs = counters.longTaskTotalMs / Math.max(1, counters.longTasks);
        counters.worstLongTaskMs = Math.max(counters.worstLongTaskMs, entry.duration);
      });
    });

    observer.observe({ entryTypes: ["longtask"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      const counters = interactionCountersRef.current;
      counters.debugStatUpdates += 1;
      setSampledCanvasStats(canvasStatsRef.current);
      setInteractionStats({
        ...counters,
        averageCommitMs: counters.averageCommitMs / Math.max(1, counters.commits),
      });
      interactionCountersRef.current = createInteractionStats();
    }, 500);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleZoomShortcut = (event) => {
      if (!event.ctrlKey || event.altKey) return;

      const isZoomIn = event.key === "+" || event.key === "=";
      const isZoomOut = event.key === "-" || event.key === "_";

      if (!isZoomIn && !isZoomOut) return;

      event.preventDefault();
      event.stopPropagation();
      setZoomIndex((currentZoomIndex) =>
        clamp(currentZoomIndex + (isZoomIn ? 1 : -1), 0, ZOOM_LEVELS.length - 1),
      );
    };

    window.addEventListener("keydown", handleZoomShortcut, { capture: true });
    return () => window.removeEventListener("keydown", handleZoomShortcut, { capture: true });
  }, []);

  return (
    <div
      ref={surfaceRef}
      className="note-grid-surface"
      style={{
        "--note-grid-cell-size": `${cellSize}px`,
      }}
    >
      <div className="note-grid-corner" />
      <Ticker
        slotCount={cellCounts.columns}
        cellSize={cellSize}
        beatLength={beatLength}
        beatsPerMeasure={beatsPerMeasure}
        bounds={gridBounds}
        initialScrollPosition={scrollPositionRef.current}
        layerRef={tickerLayerRef}
        tickerApiRef={tickerApiRef}
      />
      <PitchList
        slotCount={cellCounts.rows}
        cellSize={cellSize}
        bounds={gridBounds}
        initialScrollPosition={scrollPositionRef.current}
        layerRef={pitchLayerRef}
        pitchApiRef={pitchApiRef}
      />
      <div
        ref={viewportRef}
        className="note-grid-viewport"
        data-row={originRef.current.row}
        data-column={originRef.current.column}
      >
        <NoteGridCanvas
          viewportSize={viewportSize}
          cellSize={cellSize}
          tileSize={tileSize}
          cellRadius={cellRadius}
          keyPitchClasses={keyPitchClasses}
          beatLength={beatLength}
          beatsPerMeasure={beatsPerMeasure}
          getCellFill={getCellFill}
          onRenderStats={updateCanvasStats}
          layerRef={canvasLayerRef}
          canvasApiRef={canvasApiRef}
          initialScrollPosition={scrollPositionRef.current}
          bounds={gridBounds}
        />
        <OverlayScrollbar
          viewportWidth={viewportSize.width}
          scrollX={scrollPositionRef.current.x}
          maxScrollX={maxScrollX}
          onScrollXChange={(nextScrollX) => syncScrollPosition(nextScrollX, scrollPositionRef.current.y)}
          thumbRef={scrollbarThumbRef}
        />
      </div>
      <Navigator
        zoomIndex={zoomIndex}
        zoomLevels={ZOOM_LEVELS}
        onZoomChange={setZoomIndex}
        debugStats={debugStats}
      />
    </div>
  );
}

export { MAX_COLUMN, ZOOM_LEVELS };
