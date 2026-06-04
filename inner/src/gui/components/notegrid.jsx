import { ArrowRightFromLine, MoveHorizontal } from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import editorAPI from "../editor-bridge.js";
import {
  Navigator,
  NoteGridCanvas,
  PitchList,
  Ticker,
} from "./notegrid-components/canvas.jsx";
import {
  OverlayScrollbar,
  OVERLAY_SCROLLBAR_TRACK_INSET,
  MIN_SCROLLBAR_THUMB_WIDTH,
} from "./notegrid-components/scrollbar.jsx";
import { Notes } from "./notegrid-components/notes.jsx";
import { Overlay } from "./notegrid-components/overlay.jsx";
import { Playhead } from "./notegrid-components/playhead.jsx";
import {
  ALL_CHANNEL_INDEX,
  NOTE_PITCH_TO_GRID_ROW_OFFSET,
  SELECT_RECT_MIN_DRAG_PX,
  buildMoveProposal,
  buildResizeProposal,
  findNoteAtPoint,
  findNotesInWorldRect,
  getActiveChannelName,
  getChannelNameFromHotkey,
  isPointNearNoteTail,
  mergeClickSelection,
  noteKey,
  normalizeNoteMap,
  selectionRectToWorldRect,
  serializeSelectionEntries,
  snapDelta,
  viewportToWorldPoint,
} from "./notegrid-utils.js";
import "./universal-styling/note-grid.css";

const ZOOM_LEVELS = [20, 26, 32, 40, 48];
const DEFAULT_ZOOM_INDEX = 2;
const TILE_GAP = 1;
const CELL_RADIUS = 3;
const DEFAULT_PROJECT_MAX_COLUMN = 128;
const PROJECT_END_PADDING_COLUMNS = 10;
const MIN_COLUMN = 0;
const MAX_ROW = 96;
const MIN_BOTTOM_ROW = 12;
const DEFAULT_TOP_ROW = 96;
const DEFAULT_COLUMN = 0;
const NOTE_PREVIEW_SECONDS = 0.5;
const ROOT_THEME_COLORS = {
  background: "#fff",
};
const GRID_CELL_OFFSET_FALLBACKS = {
  base: 4,
  inKey: 8,
  beat: 9,
  beatInKey: 26,
  downBeat: 12,
  downBeatInKey: 18,
};

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

/**
 * Returns a non-negative modulo result for wrapped grid math.
 */
function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor;
}

/**
 * Bounds a number between a minimum and maximum value.
 */
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Calculates how many grid cells are needed to cover the viewport.
 */
function getViewportCellCounts(size, cellSize) {
  return {
    columns: Math.ceil(size.width / cellSize) + 1,
    rows: Math.ceil(size.height / cellSize) + 1,
  };
}

/**
 * Calculates the maximum horizontal scroll offset for the project width.
 */
function getMaxScrollX(viewportWidth, cellSize, maxColumn) {
  const contentWidth = (maxColumn - MIN_COLUMN + 1) * cellSize;
  return Math.max(0, contentWidth - viewportWidth);
}

/**
 * Calculates the maximum vertical scroll offset for the fixed pitch range.
 */
function getMaxScrollY(viewportHeight, cellSize) {
  const contentHeight = (MAX_ROW - MIN_BOTTOM_ROW + 1) * cellSize;
  return Math.max(0, contentHeight - viewportHeight);
}

/**
 * Builds the pitch-class set for the current key and mode.
 */
function getKeyPitchClasses(key, mode) {
  const root = KEY_ROOTS[key] ?? KEY_ROOTS.C;
  const intervals = MODE_INTERVALS[mode] ?? MODE_INTERVALS["Ionian (maj.)"];
  return new Set(intervals.map((interval) => (root + interval) % 12));
}

/**
 * Extends the grid width to include the latest note plus end padding.
 */
function getProjectMaxColumn(noteMap) {
  if (!noteMap || typeof noteMap !== "object")
    return DEFAULT_PROJECT_MAX_COLUMN;

  let latestNoteEnd = 0;
  Object.values(noteMap).forEach((notes) => {
    if (!Array.isArray(notes)) return;

    notes.forEach((note) => {
      const time = Number(note?.time);
      const duration = Number(note?.duration);
      if (!Number.isFinite(time) || !Number.isFinite(duration) || duration <= 0)
        return;

      latestNoteEnd = Math.max(latestNoteEnd, time + duration);
    });
  });

  return Math.max(
    DEFAULT_PROJECT_MAX_COLUMN,
    latestNoteEnd + PROJECT_END_PADDING_COLUMNS,
  );
}

/**
 * Reads a root theme color with a safe fallback for non-browser contexts.
 */
function readRootThemeColor(variableName, fallback) {
  if (typeof document === "undefined") return fallback;

  return (
    getComputedStyle(document.documentElement)
      .getPropertyValue(variableName)
      .trim() || fallback
  );
}

/**
 * Reads a numeric css variable from an element.
 */
function readCssNumber(element, variableName, fallback) {
  if (!element) return fallback;

  const value = Number(
    getComputedStyle(element).getPropertyValue(variableName).trim(),
  );
  return Number.isFinite(value) ? value : fallback;
}

/**
 * Detects editable targets so global shortcuts do not steal text input.
 */
function isTextEditingTarget(target) {
  if (!target) return false;
  const tagName = target.tagName?.toLowerCase();
  return (
    tagName === "input" ||
    tagName === "textarea" ||
    tagName === "select" ||
    target.isContentEditable
  );
}

/**
 * Parses supported css color strings into rgb channels.
 */
function parseCssColor(value) {
  const trimmed = value.trim();
  const hex = trimmed.match(/^#([0-9a-f]{3,8})$/i)?.[1];

  if (hex) {
    const expanded =
      hex.length === 3 || hex.length === 4
        ? hex
            .slice(0, 3)
            .split("")
            .map((part) => part + part)
            .join("")
        : hex.slice(0, 6);

    return {
      r: Number.parseInt(expanded.slice(0, 2), 16),
      g: Number.parseInt(expanded.slice(2, 4), 16),
      b: Number.parseInt(expanded.slice(4, 6), 16),
    };
  }

  const channels = trimmed.match(/^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
  if (!channels) return null;

  return {
    r: Number(channels[1]),
    g: Number(channels[2]),
    b: Number(channels[3]),
  };
}

/**
 * Formats rgb channels as a hex color.
 */
function formatHexColor({ r, g, b }) {
  return `#${[r, g, b]
    .map((channel) => Math.round(channel).toString(16).padStart(2, "0"))
    .join("")}`;
}

/**
 * Converts a color to its neutral grayscale channel.
 */
function getNeutralChannel(color) {
  const parsed = parseCssColor(color);
  if (!parsed) return null;

  return Math.round((parsed.r + parsed.g + parsed.b) / 3);
}

/**
 * Formats a grayscale channel as a hex color.
 */
function formatNeutralShade(channel) {
  const safeChannel = Math.min(255, Math.max(0, Math.round(channel)));
  return formatHexColor({ r: safeChannel, g: safeChannel, b: safeChannel });
}

/**
 * Offsets a theme color while preserving neutral shading.
 */
function offsetThemeGray(baseColor, offset) {
  const channel = getNeutralChannel(baseColor);
  if (channel === null) return baseColor;

  return formatNeutralShade(channel + offset);
}

/**
 * Derives the full grid cell palette from theme variables.
 */
function getGridCellPalette(sourceElement) {
  const background = readRootThemeColor(
    "--background",
    ROOT_THEME_COLORS.background,
  );
  /**
   * Reads one palette offset from the grid surface.
   */
  const getOffset = (name, fallback) =>
    readCssNumber(sourceElement, name, fallback);

  return {
    base: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-base-offset",
        GRID_CELL_OFFSET_FALLBACKS.base,
      ),
    ),
    inKey: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-in-key-offset",
        GRID_CELL_OFFSET_FALLBACKS.inKey,
      ),
    ),
    beat: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-beat-offset",
        GRID_CELL_OFFSET_FALLBACKS.beat,
      ),
    ),
    beatInKey: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-beat-in-key-offset",
        GRID_CELL_OFFSET_FALLBACKS.beatInKey,
      ),
    ),
    downBeat: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-downbeat-offset",
        GRID_CELL_OFFSET_FALLBACKS.downBeat,
      ),
    ),
    downBeatInKey: offsetThemeGray(
      background,
      getOffset(
        "--note-grid-cell-downbeat-in-key-offset",
        GRID_CELL_OFFSET_FALLBACKS.downBeatInKey,
      ),
    ),
  };
}

/**
 * Chooses a cell fill from beat, downbeat, and in-key state.
 */
function getCellFill({
  column,
  row,
  keyPitchClasses,
  beatLength,
  beatsPerMeasure,
  cellPalette,
}) {
  const beatSize = Math.max(1, Number(beatLength) || 1);
  const measureSize = beatSize * Math.max(1, Number(beatsPerMeasure) || 1); // beats to measure cells
  const isBeatStart = positiveModulo(column, beatSize) === 0;
  const isDownBeat = positiveModulo(column, measureSize) === 0;
  const isInKey = keyPitchClasses.has(positiveModulo(row, 12));

  if (isDownBeat && isInKey) return cellPalette.downBeatInKey;
  if (isDownBeat) return cellPalette.downBeat;
  if (isBeatStart && isInKey) return cellPalette.beatInKey;
  if (isBeatStart) return cellPalette.beat;
  if (isInKey) return cellPalette.inKey;
  return cellPalette.base;
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

    /**
     * Samples frame timings and publishes aggregated stats twice per second.
     */
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
function recordTimedStat(
  stats,
  countKey,
  totalKey,
  averageKey,
  worstKey,
  duration,
) {
  stats[totalKey] += duration;
  stats[averageKey] = stats[totalKey] / Math.max(1, stats[countKey]);
  stats[worstKey] = Math.max(stats[worstKey], duration);
}

/**
 * Converts an in-flight gesture into overlay ghost notes.
 */
function buildGhostNotes(gesture) {
  if (!gesture) return null;

  if (gesture.kind === "move-drag") {
    return gesture.proposed.map((note) => ({
      color: gesture.targetColor,
      pitch: note.pitch,
      time: note.time,
      duration: note.duration,
      variant: gesture.duplicate ? "ghost" : "preview",
    }));
  }
  if (gesture.kind === "resize-drag") {
    return gesture.proposed.map((note) => ({
      color: gesture.targetColor,
      pitch: note.pitch,
      time: note.time,
      duration: note.duration,
      variant: "preview",
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
 * Builds keys for original notes hidden while drag previews are visible.
 */
function buildHiddenKeys(gesture) {
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

/**
 * Builds a position signature for commit-visual reconciliation.
 */
function notePositionSignature(color, note) {
  return `${color}:${note.time}:${note.pitch}:${note.duration}`;
}

/**
 * Renders the interactive piano-roll note grid and gesture layer.
 */
export default function NoteGridSurface({
  beatLength = 4,
  beatsPerMeasure = 4,
  brush = null,
  keySignature = "C",
  mode = "Ionian (maj.)",
  noteMap = null,
  currentColorIdx = 0,
  isPlaying = false,
  playheadHomeTime = 0,
  playbackClock = null,
  tempo = 360,
  playheadArmed = false,
  onConsumePlayheadArm = null,
  debugUiEnabled = false,
  showDebugByDefault = false,
}) {
  const surfaceRef = useRef(null);
  const viewportRef = useRef(null);
  const customCursorRef = useRef(null);
  const tickerLayerRef = useRef(null);
  const pitchLayerRef = useRef(null);
  const tickerApiRef = useRef(null);
  const pitchApiRef = useRef(null);
  const notesApiRef = useRef(null);
  const overlayApiRef = useRef(null);
  const playheadApiRef = useRef(null);
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
  const scrollPositionRef = useRef({
    x: DEFAULT_COLUMN * ZOOM_LEVELS[DEFAULT_ZOOM_INDEX],
    y: 0,
  });
  const originRef = useRef({ row: DEFAULT_TOP_ROW, column: DEFAULT_COLUMN });
  const visualDirtyRef = useRef(true);
  const visualLoopRef = useRef(0);
  const previousCellSizeRef = useRef(ZOOM_LEVELS[DEFAULT_ZOOM_INDEX]);
  const interactionCountersRef = useRef(createInteractionStats());

  const gestureRef = useRef(null);
  const ghostNotesRef = useRef(null);
  const selectionRectRef = useRef(null);
  const selectionOverrideRef = useRef(null);
  const hiddenKeysRef = useRef(null);
  const pendingCommitVisualRef = useRef(null);
  const commitVisualIdRef = useRef(0);
  const pointerHoverRef = useRef(null);
  const altDownRef = useRef(false);
  const activePointerIdRef = useRef(null);
  const boxSelectRecaptureRef = useRef(null);
  const previousDebugUiEnabledRef = useRef(debugUiEnabled);

  const [zoomIndex, setZoomIndex] = useState(DEFAULT_ZOOM_INDEX);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [showDebugStats, setShowDebugStats] = useState(
    () => debugUiEnabled && showDebugByDefault,
  );
  const [interactionStats, setInteractionStats] = useState(
    createInteractionStats,
  );
  const [cursorOverride, setCursorOverride] = useState(null);

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
  const cellRadius = Math.min(
    CELL_RADIUS,
    Math.max(2, Math.round(cellSize * 0.08)),
  );
  /**
   * Computes the project width needed for the current notes.
   */
  const projectMaxColumn = useMemo(
    () => getProjectMaxColumn(noteMap),
    [noteMap],
  );
  /**
   * Computes visible cell counts for canvas and diagnostics.
   */
  const cellCounts = useMemo(
    () => getViewportCellCounts(viewportSize, cellSize),
    [cellSize, viewportSize],
  );
  /**
   * Computes the current horizontal scroll limit.
   */
  const maxScrollX = useMemo(
    () => getMaxScrollX(viewportSize.width, cellSize, projectMaxColumn),
    [cellSize, projectMaxColumn, viewportSize.width],
  );
  /**
   * Computes the current vertical scroll limit.
   */
  const maxScrollY = useMemo(
    () => getMaxScrollY(viewportSize.height, cellSize),
    [cellSize, viewportSize.height],
  );
  /**
   * Memoizes pitch classes highlighted by key and mode.
   */
  const keyPitchClasses = useMemo(
    () => getKeyPitchClasses(keySignature, mode),
    [keySignature, mode],
  );
  /**
   * Provides the latest theme-derived grid palette to the canvas layer.
   */
  const getCellPalette = useCallback(
    () => getGridCellPalette(surfaceRef.current),
    [],
  );
  /**
   * Normalizes backend note state into flat frontend note records.
   */
  const normalizedNotes = useMemo(() => normalizeNoteMap(noteMap), [noteMap]);
  const activeChannel = getActiveChannelName(currentColorIdx);
  const isAllChannel = currentColorIdx === ALL_CHANNEL_INDEX;
  const interactionBlocked = isAllChannel;
  /**
   * Defines immutable world bounds for the current grid width.
   */
  const gridBounds = useMemo(
    () => ({
      minColumn: MIN_COLUMN,
      maxColumn: projectMaxColumn,
      maxRow: MAX_ROW,
    }),
    [projectMaxColumn],
  );

  const objectCount = 1 + cellCounts.columns + cellCounts.rows;
  const visibleCellCount = cellCounts.columns * cellCounts.rows;
  /**
   * Packages sampled grid diagnostics for the navigator.
   */
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
      const trackWidth = Math.max(
        0,
        viewportSize.width - OVERLAY_SCROLLBAR_TRACK_INSET * 2,
      );
      const contentWidth = viewportSize.width + maxScrollX;
      const thumbWidth =
        trackWidth <= 0 || maxScrollX <= 0
          ? trackWidth
          : clamp(
              (viewportSize.width / contentWidth) * trackWidth,
              MIN_SCROLLBAR_THUMB_WIDTH,
              trackWidth,
            );
      const thumbLeft =
        maxScrollX <= 0 || trackWidth <= thumbWidth
          ? 0
          : (scrollX / maxScrollX) * (trackWidth - thumbWidth);

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
   * Clears a retained commit preview when the backend state catches up.
   */
  const clearPendingCommitVisual = useCallback(
    (commitId = null) => {
      const pending = pendingCommitVisualRef.current;
      if (!pending || (commitId !== null && pending.id !== commitId)) return;

      pendingCommitVisualRef.current = null;
      ghostNotesRef.current = null;
      hiddenKeysRef.current = null;
      overlayApiRef.current?.invalidate();
      notesApiRef.current?.invalidate();
      scheduleVisualUpdate();
    },
    [scheduleVisualUpdate],
  );

  /**
   * Keeps drag or resize previews visible while the async commit resolves.
   */
  const retainCommitVisual = useCallback(
    ({ gesture, targetColor, proposed }) => {
      const hiddenKeys = buildHiddenKeys(gesture);
      const commitId = commitVisualIdRef.current + 1;
      commitVisualIdRef.current = commitId;

      pendingCommitVisualRef.current = {
        id: commitId,
        proposedSignatures: new Set(
          proposed.map((note) => notePositionSignature(targetColor, note)), // proposed backend positions
        ),
        hiddenOriginalSignatures: hiddenKeys
          ? new Set(
              gesture.originals.map((note) =>
                notePositionSignature(gesture.originalColor, note), // originals hidden until replaced
              ),
            )
          : null,
      };
      ghostNotesRef.current = buildGhostNotes(gesture);
      hiddenKeysRef.current = hiddenKeys;
      overlayApiRef.current?.invalidate();
      notesApiRef.current?.invalidate();
      scheduleVisualUpdate();

      return commitId;
    },
    [scheduleVisualUpdate],
  );

  useLayoutEffect(() => {
    const pending = pendingCommitVisualRef.current;
    if (!pending) return;

    const visibleSignatures = new Set(
      normalizedNotes.map((note) => notePositionSignature(note.color, note)),
    );
    const proposedReady = [...pending.proposedSignatures].every((signature) =>
      visibleSignatures.has(signature),
    );
    const originalsReplaced =
      !pending.hiddenOriginalSignatures ||
      [...pending.hiddenOriginalSignatures].every(
        (signature) =>
          !visibleSignatures.has(signature) ||
          pending.proposedSignatures.has(signature),
      );

    if (proposedReady && originalsReplaced) {
      clearPendingCommitVisual(pending.id);
    }
  }, [clearPendingCommitVisual, normalizedNotes]);

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
        column: MIN_COLUMN + Math.floor(clampedX / cellSize), // scroll px to world column
        row: MAX_ROW - Math.floor(clampedY / cellSize), // scroll px to world row
      };

      const previousScrollPosition = scrollPositionRef.current;
      if (
        previousScrollPosition.x !== clampedX ||
        previousScrollPosition.y !== clampedY
      ) {
        scrollPositionRef.current = { x: clampedX, y: clampedY };
      }
      const originChanged =
        nextOrigin.row !== originRef.current.row ||
        nextOrigin.column !== originRef.current.column;

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

    syncScrollPosition(
      scrollPositionRef.current.x,
      scrollPositionRef.current.y,
    );
  }, [cellSize, syncScrollPosition, viewportSize.height, viewportSize.width]);

  useLayoutEffect(() => {
    scheduleVisualUpdate();
  }, [scheduleVisualUpdate]);

  useEffect(() => {
    if (typeof MutationObserver === "undefined") return undefined;

    const observer = new MutationObserver(() => {
      scheduleVisualUpdate();
    });

    observer.observe(document.head, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true,
    });

    return () => observer.disconnect();
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
        // Box-select capture is sticky and depends on the current scroll, so
        // re-evaluate it whenever we redraw so wheel-scroll captures notes
        // that pass through the rectangle in addition to pointermove.
        const gesture = gestureRef.current;
        if (gesture?.kind === "box-select" && boxSelectRecaptureRef.current) {
          boxSelectRecaptureRef.current(
            gesture.endViewportX,
            gesture.endViewportY,
          );
        }
        notesApiRef.current?.update({ x, y });
        overlayApiRef.current?.update({ x, y });
        playheadApiRef.current?.update({ x, y });
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
  const handleWheel = useCallback(
    (event) => {
      const start = performance.now();
      event.preventDefault();
      interactionCountersRef.current.wheelEvents += 1;
      syncScrollPosition(
        scrollPositionRef.current.x + event.deltaX,
        scrollPositionRef.current.y + event.deltaY,
      );
      recordTimedStat(
        interactionCountersRef.current,
        "wheelEvents",
        "wheelTotalMs",
        "averageWheelMs",
        "worstWheelMs",
        performance.now() - start,
      );
    },
    [syncScrollPosition],
  );

  /**
   * Reads viewport-relative pointer coordinates so gestures can translate them
   * to world (column, row) space without each handler recomputing the bounds.
   */
  const getPointerViewportPosition = useCallback((event) => {
    const viewport = viewportRef.current;
    if (!viewport) return null;
    const bounds = viewport.getBoundingClientRect();
    return {
      viewportX: event.clientX - bounds.left,
      viewportY: event.clientY - bounds.top,
    };
  }, []);

  /**
   * Convenience helper: viewport pointer position -> world coords. Used by
   * every gesture (draw, erase, select, drag, resize) so the math lives in
   * exactly one place.
   */
  const getPointerWorldPosition = useCallback(
    (event) => {
      const viewportPos = getPointerViewportPosition(event);
      if (!viewportPos) return null;
      const point = viewportToWorldPoint({
        viewportX: viewportPos.viewportX,
        viewportY: viewportPos.viewportY,
        scrollPosition: scrollPositionRef.current,
        cellSize,
        bounds: gridBounds,
      });
      return { ...viewportPos, ...point };
    },
    [cellSize, getPointerViewportPosition, gridBounds],
  );

  /**
   * Plays a short note preview for hover and draw feedback.
   */
  const previewPitch = useCallback((pitch, color = null) => {
    editorAPI
      .playNotePreview(pitch, color, NOTE_PREVIEW_SECONDS)
      .catch(() => {});
  }, []);

  /**
   * Recomputes the cursor variant from gesture + hover state. Called from
   * pointer move and gesture transitions; React bails on the set if the value
   * has not changed so the cost of polling is bounded.
   */
  const refreshCursor = useCallback(() => {
    if (playheadArmed) {
      setCursorOverride("playhead");
      return;
    }

    if (interactionBlocked) {
      setCursorOverride("disabled");
      return;
    }

    const gesture = gestureRef.current;
    if (gesture?.kind === "resize-drag") {
      setCursorOverride("resize");
      return;
    }
    if (gesture) {
      setCursorOverride(null);
      return;
    }

    if (brush?.id === "select") {
      const hover = pointerHoverRef.current;
      if (hover) {
        const nearTail = normalizedNotes.some(
          (note) =>
            note.selected &&
            note.color === activeChannel &&
            isPointNearNoteTail({
              note,
              exactColumn: hover.exactColumn,
              exactRow: hover.exactRow,
            }),
        );
        if (nearTail) {
          setCursorOverride("resize");
          return;
        }
      }
    }

    setCursorOverride(null);
  }, [
    activeChannel,
    brush?.id,
    interactionBlocked,
    normalizedNotes,
    playheadArmed,
  ]);

  /**
   * Pushes the latest gesture-derived overlays (selection rectangle and ghost
   * notes) into refs and schedules a redraw so the overlay layer can pick
   * them up on the next animation frame.
   */
  const refreshOverlayState = useCallback(() => {
    const gesture = gestureRef.current;
    ghostNotesRef.current = buildGhostNotes(gesture);
    // Hide originals for in-place moves/resizes so the preview reads as the
    // note being carried, while duplicate-drag keeps originals visible.
    hiddenKeysRef.current = buildHiddenKeys(gesture);
    overlayApiRef.current?.invalidate();
    notesApiRef.current?.invalidate();
    scheduleVisualUpdate();
  }, [scheduleVisualUpdate]);

  /**
   * Resets all transient gesture state and cancels backend temp notes.
   */
  const cancelGesture = useCallback(() => {
    gestureRef.current = null;
    ghostNotesRef.current = null;
    selectionRectRef.current = null;
    selectionOverrideRef.current = null;
    hiddenKeysRef.current = null;
    activePointerIdRef.current = null;
    editorAPI.cancelTempNotes().catch(() => {});
    refreshOverlayState();
    refreshCursor();
  }, [refreshCursor, refreshOverlayState]);

  /**
   * Recomputes proposed positions / durations for the in-flight drag/resize
   * from the latest pointer position and modifier state.
   */
  const updateDragProposal = useCallback(() => {
    const gesture = gestureRef.current;
    const hover = pointerHoverRef.current;
    if (!gesture || !hover) return;

    if (gesture.kind === "move-drag") {
      const deltaColumn = snapDelta(
        hover.exactColumn - gesture.startExactColumn,
      );
      const deltaRow = snapDelta(hover.exactRow - gesture.startExactRow);
      gesture.deltaColumn = deltaColumn;
      gesture.deltaRow = deltaRow;
      gesture.duplicate = altDownRef.current;
      const { proposed } = buildMoveProposal({
        originals: gesture.originals,
        deltaColumn,
        deltaRow,
      });
      gesture.proposed = proposed;
    } else if (gesture.kind === "resize-drag") {
      const deltaDuration = snapDelta(
        hover.exactColumn - gesture.startExactColumn,
      );
      gesture.deltaDuration = deltaDuration;
      const { proposed } = buildResizeProposal({
        originals: gesture.originals,
        deltaDuration,
      });
      gesture.proposed = proposed;
    }

    refreshOverlayState();
  }, [refreshOverlayState]);

  /**
   * Updates the box-select rectangle and unions any newly-captured notes into
   * the visual draft set. The rect is anchored to the viewport so scrolling
   * moves world coordinates underneath it; we also publish this through
   * `boxSelectRecaptureRef` so the rAF tick can pick up notes that scroll
   * into the rectangle without the user moving the mouse.
   */
  const updateBoxSelect = useCallback(
    (viewportX, viewportY) => {
      const gesture = gestureRef.current;
      if (gesture?.kind !== "box-select") return;
      gesture.endViewportX = viewportX;
      gesture.endViewportY = viewportY;
      selectionRectRef.current = {
        startViewportX: gesture.startViewportX,
        startViewportY: gesture.startViewportY,
        endViewportX: viewportX,
        endViewportY: viewportY,
      };
      const rect = selectionRectToWorldRect({
        startViewportX: gesture.startViewportX,
        startViewportY: gesture.startViewportY,
        endViewportX: viewportX,
        endViewportY: viewportY,
        currentScroll: scrollPositionRef.current,
        cellSize,
        bounds: gridBounds,
      });
      const captured = findNotesInWorldRect({
        notes: normalizedNotes,
        rect,
        activeChannel,
      });
      const draft = gesture.capturedKeys;
      for (const note of captured) {
        draft.add(note.key);
      }
      // Box-select also keeps the existing selection visible while drawing so
      // the user can see what was selected before the gesture began.
      const union = new Set(draft);
      for (const key of gesture.preservedKeys) union.add(key);
      selectionOverrideRef.current = union;
      refreshOverlayState();
    },
    [activeChannel, cellSize, gridBounds, normalizedNotes, refreshOverlayState],
  );

  useEffect(() => {
    boxSelectRecaptureRef.current = updateBoxSelect;
  }, [updateBoxSelect]);

  /**
   * Commits or discards the in-flight gesture on pointer up. Each branch
   * sends its intent through the editor bridge so the backend records the
   * transaction; the React surface never mutates the document directly.
   */
  const commitGesture = useCallback(() => {
    const gesture = gestureRef.current;
    if (!gesture) return;
    let retainedCommitVisual = false;

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
      const selectedNotes = normalizedNotes.filter((note) =>
        draftKeys.has(note.key),
      );
      selectionOverrideRef.current = draftKeys;
      editorAPI
        .setSelection(serializeSelectionEntries(selectedNotes))
        .catch(() => {})
        .finally(() => {
          selectionOverrideRef.current = null;
          notesApiRef.current?.invalidate();
          scheduleVisualUpdate();
        });
    } else if (gesture.kind === "move-drag") {
      const action = gesture.duplicate ? "duplicate" : "move";
      const sourceColor = gesture.originalColor;
      const targetColor = gesture.targetColor;
      const { originals, proposed } = buildMoveProposal({
        originals: gesture.originals,
        deltaColumn: gesture.deltaColumn,
        deltaRow: gesture.deltaRow,
      });
      if (
        gesture.deltaColumn !== 0 ||
        gesture.deltaRow !== 0 ||
        gesture.duplicate ||
        targetColor !== sourceColor
      ) {
        const commitVisualId = retainCommitVisual({
          gesture,
          targetColor,
          proposed,
        });
        retainedCommitVisual = true;
        editorAPI
          .beginTempNotes(action, sourceColor, originals, targetColor)
          .then(() => editorAPI.setTempNotes(proposed))
          .then(() => editorAPI.commitTempNotes())
          .catch(() => {
            editorAPI.cancelTempNotes().catch(() => {});
            clearPendingCommitVisual(commitVisualId);
          });
      } else {
        editorAPI.cancelTempNotes().catch(() => {});
      }
    } else if (gesture.kind === "resize-drag") {
      const sourceColor = gesture.originalColor;
      const { originals, proposed } = buildResizeProposal({
        originals: gesture.originals,
        deltaDuration: gesture.deltaDuration,
      });
      if (gesture.deltaDuration !== 0) {
        const commitVisualId = retainCommitVisual({
          gesture,
          targetColor: sourceColor,
          proposed,
        });
        retainedCommitVisual = true;
        editorAPI
          .beginTempNotes("move", sourceColor, originals, sourceColor)
          .then(() => editorAPI.setTempNotes(proposed))
          .then(() => editorAPI.commitTempNotes())
          .catch(() => {
            editorAPI.cancelTempNotes().catch(() => {});
            clearPendingCommitVisual(commitVisualId);
          });
      } else {
        editorAPI.cancelTempNotes().catch(() => {});
      }
    }

    gestureRef.current = null;
    selectionRectRef.current = null;
    activePointerIdRef.current = null;
    if (!retainedCommitVisual) {
      ghostNotesRef.current = null;
      hiddenKeysRef.current = null;
      refreshOverlayState();
    } else {
      overlayApiRef.current?.invalidate();
      notesApiRef.current?.invalidate();
      scheduleVisualUpdate();
    }
    refreshCursor();
  }, [
    clearPendingCommitVisual,
    normalizedNotes,
    refreshCursor,
    refreshOverlayState,
    retainCommitVisual,
    scheduleVisualUpdate,
  ]);

  /**
   * Routes pointer down to draw/erase/select/playhead based on the current
   * brush and channel; per-branch logic is intentionally inlined here so the
   * gesture state machine stays in one readable place.
   */
  const handlePointerDown = useCallback(
    (event) => {
      if (event.button !== 0) return;
      const world = getPointerWorldPosition(event);
      if (!world) return;

      const viewport = viewportRef.current;
      viewport?.setPointerCapture?.(event.pointerId);
      activePointerIdRef.current = event.pointerId;

      if (playheadArmed) {
        const time = Math.max(0, Math.round(world.exactColumn));
        playheadApiRef.current?.setHome(time);
        editorAPI.setPlayheadHome(time).catch(() => {});
        onConsumePlayheadArm?.();
        return;
      }

      if (interactionBlocked) {
        return;
      }

      const hit = findNoteAtPoint({
        notes: normalizedNotes,
        exactColumn: world.exactColumn,
        exactRow: world.exactRow,
        activeChannel,
      });

      if (brush?.id === "pencil") {
        if (!activeChannel) return;
        if (hit && hit.color === activeChannel) return;
        const time = Math.max(0, world.column);
        const pitch = world.row - NOTE_PITCH_TO_GRID_ROW_OFFSET;
        // Draw is a single-note stroke: pointer-down spawns a 1-cell ghost,
        // pointer-move extends its duration rightward, pointer-up commits.
        gestureRef.current = {
          kind: "draw",
          color: activeChannel,
          pitch,
          time,
          startExactColumn: world.exactColumn,
          duration: 1,
        };
        refreshOverlayState();
        return;
      }

      if (brush?.id === "eraser") {
        const erasedKeys = new Set();
        if (hit) {
          erasedKeys.add(hit.key);
          editorAPI.eraseNoteAt(hit.color, hit.time, hit.pitch).catch(() => {});
        }
        gestureRef.current = { kind: "erase", erasedKeys };
        return;
      }

      if (brush?.id === "select") {
        const currentSelection = normalizedNotes.filter(
          (note) => note.selected,
        );

        if (
          hit &&
          hit.selected &&
          hit.color === activeChannel &&
          !event.shiftKey
        ) {
          if (
            isPointNearNoteTail({
              note: hit,
              exactColumn: world.exactColumn,
              exactRow: world.exactRow,
            })
          ) {
            gestureRef.current = {
              kind: "resize-drag",
              originalColor: activeChannel,
              targetColor: activeChannel,
              originals: currentSelection.filter(
                (note) => note.color === activeChannel,
              ),
              proposed: [],
              startExactColumn: world.exactColumn,
              deltaDuration: 0,
            };
            refreshCursor();
            return;
          }
          gestureRef.current = {
            kind: "move-drag",
            originalColor: activeChannel,
            targetColor: activeChannel,
            originals: currentSelection.filter(
              (note) => note.color === activeChannel,
            ),
            proposed: [],
            startExactColumn: world.exactColumn,
            startExactRow: world.exactRow,
            deltaColumn: 0,
            deltaRow: 0,
            duplicate: event.altKey,
          };
          altDownRef.current = event.altKey;
          refreshCursor();
          return;
        }

        if (hit) {
          const nextSelection = mergeClickSelection({
            currentSelection,
            target: hit,
            additive: event.shiftKey,
          });
          previewPitch(hit.pitch, hit.color);
          editorAPI
            .setSelection(serializeSelectionEntries(nextSelection))
            .catch(() => {});
          return;
        }

        if (!event.shiftKey && currentSelection.length > 0) {
          editorAPI.clearSelection().catch(() => {});
        }
        const preservedKeys = event.shiftKey
          ? new Set(currentSelection.map((note) => note.key))
          : new Set();
        gestureRef.current = {
          kind: "box-select",
          startViewportX: world.viewportX,
          startViewportY: world.viewportY,
          endViewportX: world.viewportX,
          endViewportY: world.viewportY,
          capturedKeys: new Set(),
          preservedKeys,
        };
        selectionRectRef.current = {
          startViewportX: world.viewportX,
          startViewportY: world.viewportY,
          endViewportX: world.viewportX,
          endViewportY: world.viewportY,
        };
        selectionOverrideRef.current = preservedKeys;
        refreshOverlayState();
      }
    },
    [
      activeChannel,
      brush?.id,
      getPointerWorldPosition,
      interactionBlocked,
      normalizedNotes,
      onConsumePlayheadArm,
      playheadArmed,
      previewPitch,
      refreshCursor,
      refreshOverlayState,
    ],
  );

  /**
   * Updates hover state, cursor position, and the active gesture while moving.
   */
  const handlePointerMove = useCallback(
    (event) => {
      const world = getPointerWorldPosition(event);
      const customCursor = customCursorRef.current;
      const viewport = viewportRef.current;
      if (!world || !viewport) return;

      const overScrollbar =
        event.target.closest(".note-grid-overlay-scrollbar") !== null;
      if (customCursor) {
        if (overScrollbar) {
          customCursor.dataset.visible = "false";
        } else {
          customCursor.style.transform = `translate3d(${world.viewportX}px, ${world.viewportY}px, 0)`;
          customCursor.dataset.visible = "true";
        }
      }

      pointerHoverRef.current = {
        exactColumn: world.exactColumn,
        exactRow: world.exactRow,
        column: world.column,
        row: world.row,
      };
      altDownRef.current = event.altKey;
      refreshCursor();

      const gesture = gestureRef.current;
      if (!gesture) return;

      if (gesture.kind === "draw") {
        const extension = Math.max(
          0,
          snapDelta(world.exactColumn - gesture.startExactColumn), // drag cells from note start
        );
        const nextDuration = Math.max(1, extension + 1);
        if (nextDuration !== gesture.duration) {
          gesture.duration = nextDuration;
          refreshOverlayState();
        }
        return;
      }

      if (gesture.kind === "erase") {
        const hit = findNoteAtPoint({
          notes: normalizedNotes,
          exactColumn: world.exactColumn,
          exactRow: world.exactRow,
          activeChannel,
        });
        if (hit && !gesture.erasedKeys.has(hit.key)) {
          gesture.erasedKeys.add(hit.key);
          editorAPI.eraseNoteAt(hit.color, hit.time, hit.pitch).catch(() => {});
        }
        return;
      }

      if (gesture.kind === "box-select") {
      const dx = Math.abs(world.viewportX - gesture.startViewportX); // viewport drag threshold
      const dy = Math.abs(world.viewportY - gesture.startViewportY); // viewport drag threshold
        if (dx < SELECT_RECT_MIN_DRAG_PX && dy < SELECT_RECT_MIN_DRAG_PX)
          return;
        updateBoxSelect(world.viewportX, world.viewportY);
        return;
      }

      if (gesture.kind === "move-drag" || gesture.kind === "resize-drag") {
        updateDragProposal();
      }
    },
    [
      activeChannel,
      getPointerWorldPosition,
      normalizedNotes,
      refreshCursor,
      updateBoxSelect,
      updateDragProposal,
    ],
  );

  /**
   * Finalizes the active gesture and releases pointer capture.
   */
  const handlePointerUp = useCallback(
    (event) => {
      if (
        activePointerIdRef.current !== null &&
        event.pointerId !== activePointerIdRef.current
      )
        return;
      const world = getPointerWorldPosition(event);
      if (world) {
        pointerHoverRef.current = {
          exactColumn: world.exactColumn,
          exactRow: world.exactRow,
          column: world.column,
          row: world.row,
        };
        const gesture = gestureRef.current;
        if (gesture?.kind === "move-drag" || gesture?.kind === "resize-drag") {
          updateDragProposal();
        } else if (gesture?.kind === "draw") {
          const extension = Math.max(
            0,
            snapDelta(world.exactColumn - gesture.startExactColumn), // drag cells from note start
          );
          gesture.duration = Math.max(1, extension + 1);
        }
      }
      const viewport = viewportRef.current;
      viewport?.releasePointerCapture?.(event.pointerId);
      commitGesture();
    },
    [commitGesture, getPointerWorldPosition, updateDragProposal],
  );

  /**
   * Cancels the active gesture when pointer capture is lost.
   */
  const handlePointerCancel = useCallback(
    (event) => {
      if (
        activePointerIdRef.current !== null &&
        event.pointerId !== activePointerIdRef.current
      )
        return;
      cancelGesture();
    },
    [cancelGesture],
  );

  /**
   * Hides the custom cursor when the pointer leaves the viewport.
   */
  const handlePointerLeave = useCallback(() => {
    if (customCursorRef.current) {
      customCursorRef.current.dataset.visible = "false";
    }
    pointerHoverRef.current = null;
  }, []);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  useEffect(() => {
    if (
      typeof PerformanceObserver === "undefined" ||
      !PerformanceObserver.supportedEntryTypes?.includes("longtask")
    ) {
      return undefined;
    }

    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        const counters = interactionCountersRef.current;
        counters.longTasks += 1;
        counters.longTaskTotalMs += entry.duration;
        counters.averageLongTaskMs =
          counters.longTaskTotalMs / Math.max(1, counters.longTasks);
        counters.worstLongTaskMs = Math.max(
          counters.worstLongTaskMs,
          entry.duration,
        );
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
        averageCommitMs:
          counters.averageCommitMs / Math.max(1, counters.commits),
      });
      interactionCountersRef.current = createInteractionStats();
    }, 500);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!debugUiEnabled) {
      setShowDebugStats(false);
    } else if (!previousDebugUiEnabledRef.current) {
      setShowDebugStats(Boolean(showDebugByDefault));
    }
    previousDebugUiEnabledRef.current = debugUiEnabled;
  }, [debugUiEnabled, showDebugByDefault]);

  useEffect(() => {
    /**
     * Handles zoom and debug shortcuts before global editor shortcuts run.
     */
    const handleZoomShortcut = (event) => {
      if (isTextEditingTarget(event.target)) return;

      if (
        debugUiEnabled &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        event.key.toLowerCase() === "i"
      ) {
        event.preventDefault();
        setShowDebugStats((current) => !current);
        return;
      }

      if (!event.ctrlKey || event.altKey) return;

      const isZoomIn = event.key === "+" || event.key === "=";
      const isZoomOut = event.key === "-" || event.key === "_";

      if (!isZoomIn && !isZoomOut) return;

      event.preventDefault();
      event.stopPropagation();
      setZoomIndex((currentZoomIndex) =>
        clamp(
          currentZoomIndex + (isZoomIn ? 1 : -1),
          0,
          ZOOM_LEVELS.length - 1,
        ),
      );
    };

    window.addEventListener("keydown", handleZoomShortcut, { capture: true });
    return () =>
      window.removeEventListener("keydown", handleZoomShortcut, {
        capture: true,
      });
  }, [debugUiEnabled]);

  /**
   * Captures number keys 1-6 in capture phase during an active move/duplicate
   * drag so the gesture can retarget its destination channel without the
   * global handler (which switches the active channel) firing.
   */
  useEffect(() => {
    /**
     * Captures modifier and channel hotkeys while a gesture is active.
     */
    const handleHotkey = (event) => {
      if (isTextEditingTarget(event.target)) return;

      const gesture = gestureRef.current;

      if (event.key === "Alt" || event.key === "AltGraph") {
        altDownRef.current = true;
        if (gesture?.kind === "move-drag") {
          gesture.duplicate = true;
          updateDragProposal();
        }
        return;
      }

      if (gesture?.kind === "move-drag") {
        const channel = getChannelNameFromHotkey(event.key);
        if (channel) {
          event.preventDefault();
          event.stopPropagation();
          gesture.targetColor = channel;
          refreshOverlayState();
          return;
        }
        if (event.key === "7") {
          // Channel 7 is the "all" channel; ignore it as a drag target so a
          // mistyped hotkey does not yank the active channel mid-drag.
          event.preventDefault();
          event.stopPropagation();
          return;
        }
      }

      if (event.key === "Escape" && gesture) {
        event.preventDefault();
        cancelGesture();
      }
    };

    /**
     * Clears transient duplicate-drag state when Alt is released.
     */
    const handleKeyUp = (event) => {
      if (event.key === "Alt" || event.key === "AltGraph") {
        altDownRef.current = false;
        const gesture = gestureRef.current;
        if (gesture?.kind === "move-drag") {
          gesture.duplicate = false;
          updateDragProposal();
        }
      }
    };

    window.addEventListener("keydown", handleHotkey, { capture: true });
    window.addEventListener("keyup", handleKeyUp, { capture: true });
    return () => {
      window.removeEventListener("keydown", handleHotkey, { capture: true });
      window.removeEventListener("keyup", handleKeyUp, { capture: true });
    };
  }, [cancelGesture, refreshOverlayState, updateDragProposal]);

  // Keep cursor + overlay state fresh when the brush, active channel, or
  // selection set changes, e.g. when the user switches to select mode while
  // hovering near a selected note tail.
  useEffect(() => {
    refreshCursor();
    notesApiRef.current?.invalidate();
    scheduleVisualUpdate();
  }, [
    brush?.id,
    activeChannel,
    interactionBlocked,
    playheadArmed,
    refreshCursor,
    scheduleVisualUpdate,
  ]);

  // Resolve the cursor icon and CSS variant for the custom cursor div. We
  // override the brush icon for resize/playhead states; disabled uses the
  // native cursor instead.
  const BrushCursorIcon = brush?.Icon;
  /**
   * Chooses the cursor icon for the current brush override state.
   */
  const cursorIcon = (() => {
    if (cursorOverride === "disabled") return null;
    if (cursorOverride === "resize") return MoveHorizontal;
    if (cursorOverride === "playhead") return ArrowRightFromLine;
    return BrushCursorIcon;
  })();
  /**
   * Chooses the cursor style variant for the current brush override state.
   */
  const cursorVariant = (() => {
    if (cursorOverride === "resize") return "resize";
    if (cursorOverride === "playhead") return "playhead";
    return brush?.id ?? null;
  })();

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
        onPreviewPitch={(pitch) => previewPitch(pitch)}
      />
      <div
        ref={viewportRef}
        className="note-grid-viewport"
        data-cursor-disabled={interactionBlocked ? "true" : undefined}
        data-row={originRef.current.row}
        data-column={originRef.current.column}
        onPointerMove={handlePointerMove}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onPointerLeave={handlePointerLeave}
      >
        <NoteGridCanvas
          viewportSize={viewportSize}
          cellSize={cellSize}
          tileSize={tileSize}
          cellRadius={cellRadius}
          keyPitchClasses={keyPitchClasses}
          beatLength={beatLength}
          beatsPerMeasure={beatsPerMeasure}
          getCellPalette={getCellPalette}
          getCellFill={getCellFill}
          onRenderStats={updateCanvasStats}
          layerRef={canvasLayerRef}
          canvasApiRef={canvasApiRef}
          initialScrollPosition={scrollPositionRef.current}
          bounds={gridBounds}
        />
        <Notes
          notes={normalizedNotes}
          viewportSize={viewportSize}
          cellSize={cellSize}
          tileSize={tileSize}
          cellRadius={cellRadius}
          bounds={gridBounds}
          initialScrollPosition={scrollPositionRef.current}
          notesApiRef={notesApiRef}
          activeChannel={activeChannel}
          selectionOverrideRef={selectionOverrideRef}
          hiddenKeysRef={hiddenKeysRef}
          selectMode={brush?.id === "select"}
        />
        <Overlay
          viewportSize={viewportSize}
          cellSize={cellSize}
          tileSize={tileSize}
          cellRadius={cellRadius}
          bounds={gridBounds}
          initialScrollPosition={scrollPositionRef.current}
          overlayApiRef={overlayApiRef}
          ghostNotesRef={ghostNotesRef}
          selectionRectRef={selectionRectRef}
        />
        <Playhead
          viewportSize={viewportSize}
          cellSize={cellSize}
          bounds={gridBounds}
          initialScrollPosition={scrollPositionRef.current}
          playheadApiRef={playheadApiRef}
          playheadHomeTime={playheadHomeTime}
          isPlaying={isPlaying}
          playbackClock={playbackClock}
          tempo={tempo}
        />
        {cursorIcon ? (
          <div
            ref={customCursorRef}
            className={`note-grid-custom-cursor note-grid-custom-cursor-${cursorVariant}`}
            data-visible="false"
            aria-hidden="true"
          >
            {(() => {
              const Icon = cursorIcon;
              return (
                <>
                  <Icon className="note-grid-custom-cursor-outline" />
                  <Icon className="note-grid-custom-cursor-fill" />
                </>
              );
            })()}
          </div>
        ) : null}
        <OverlayScrollbar
          viewportWidth={viewportSize.width}
          scrollX={scrollPositionRef.current.x}
          maxScrollX={maxScrollX}
          onScrollXChange={(nextScrollX) =>
            syncScrollPosition(nextScrollX, scrollPositionRef.current.y)
          }
          thumbRef={scrollbarThumbRef}
        />
      </div>
      <Navigator
        zoomIndex={zoomIndex}
        zoomLevels={ZOOM_LEVELS}
        onZoomChange={setZoomIndex}
        debugStats={debugStats}
        showDebugStats={debugUiEnabled && showDebugStats}
      />
    </div>
  );
}

export { DEFAULT_PROJECT_MAX_COLUMN as MAX_COLUMN, ZOOM_LEVELS };
