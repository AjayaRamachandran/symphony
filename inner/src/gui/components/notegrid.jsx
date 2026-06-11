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
import { Navigator } from "./notegrid-components/navigator.jsx";
import { PitchList } from "./notegrid-components/pitch-list.jsx";
import { Playhead } from "./notegrid-components/playhead.jsx";
import {
  MIN_SCROLLBAR_THUMB_WIDTH,
  OVERLAY_SCROLLBAR_TRACK_INSET,
  OverlayScrollbar,
} from "./notegrid-components/scrollbar.jsx";
import { Ticker } from "./notegrid-components/ticker.jsx";
import {
  DEFAULT_ZOOM_INDEX,
  MAX_ROW,
  MIN_COLUMN,
  ZOOM_LEVELS,
  convertWorldToGrid,
  getMaxScrollX,
  getScrollPosition,
  tile,
  view,
  viewBounds,
} from "./notegrid-utils/camera.js";
import { buildCellPalette } from "./notegrid-utils/cell-palette.js";
import { drawFrame, invalidateGridBlock } from "./notegrid-utils/draw.js";
import {
  cancelGesture,
  getGestureKind,
  handleClick,
  handleDrag,
  handleHotkeyDown,
  handleHotkeyUp,
  handleUnClick,
  recaptureBoxSelect,
  reconcileCommitVisual,
} from "./notegrid-utils/gestures.js";
import {
  ALL_CHANNEL_INDEX,
  getActiveChannelName,
  isPointNearNoteTail,
  normalizeNoteMap,
} from "./notegrid-utils/note-grid-ops.js";
import "../universal-styling/note-grid.css";

// ---- CONSTANTS ----

const DEFAULT_PROJECT_MAX_COLUMN = 128;
const PROJECT_END_PADDING_COLUMNS = 10;
const NOTE_PREVIEW_SECONDS = 0.3;

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

// ---- PURE UTILITIES ----

/**
 * Bounds a number between a minimum and maximum value.
 */
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
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
 * Extends the grid width to include the latest note end plus end padding.
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
 * Returns true if the event target is a text input so global shortcuts can
 * skip processing and let the browser handle the keystroke normally.
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

// ---- COMPONENT ----

/**
 * Renders the interactive piano-roll note grid. The React component is a
 * thin shell: it owns the chrome (ticker, pitch list, navigator, scrollbar)
 * and routes pointer/keyboard events into the imperative camera, gesture,
 * and draw modules, which repaint a single canvas through a dirty-flag
 * animation loop — the same mainloop shape as the old pygame editor.
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
  // ---- REFS & STATE ----

  const surfaceRef = useRef(null);
  const viewportRef = useRef(null);
  const canvasRef = useRef(null);
  const customCursorRef = useRef(null);
  const tickerLayerRef = useRef(null);
  const pitchLayerRef = useRef(null);
  const tickerApiRef = useRef(null);
  const pitchApiRef = useRef(null);
  const playheadApiRef = useRef(null);
  const scrollbarThumbRef = useRef(null);

  const gridRef = useRef(null); // current props + callbacks for the imperative modules
  const dirtyRef = useRef(true); // repaint requested for the next animation frame
  const paletteRef = useRef(null);
  const selectionStrokeRef = useRef("#ffffff");
  const hoverRef = useRef(null); // last pointer grid position, for cursor shape
  const activePointerIdRef = useRef(null);
  const drawStatsRef = useRef({ drawMs: 0, visibleNotes: 0 });
  const frameCountRef = useRef(0);

  const [zoomIndex, setZoomIndex] = useState(DEFAULT_ZOOM_INDEX);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [cursorOverride, setCursorOverride] = useState(null);
  const [showDebugStats, setShowDebugStats] = useState(
    () => debugUiEnabled && showDebugByDefault,
  );
  const [debugStats, setDebugStats] = useState(null);

  // ---- DERIVED VALUES ----

  const cellSize = ZOOM_LEVELS[zoomIndex];
  tile.size = cellSize; // sync the camera before children compute scroll positions

  const activeChannel = getActiveChannelName(currentColorIdx);
  const interactionBlocked = currentColorIdx === ALL_CHANNEL_INDEX; // all-channel view blocks editing

  const normalizedNotes = useMemo(() => normalizeNoteMap(noteMap), [noteMap]);
  const projectMaxColumn = useMemo(() => getProjectMaxColumn(noteMap), [noteMap]);
  const keyPitchClasses = useMemo(
    () => getKeyPitchClasses(keySignature, mode),
    [keySignature, mode],
  );

  const gridBounds = useMemo(
    () => ({ minColumn: MIN_COLUMN, maxColumn: projectMaxColumn, maxRow: MAX_ROW }),
    [projectMaxColumn],
  );
  const maxScrollX = useMemo(
    () => getMaxScrollX(viewportSize.width, projectMaxColumn),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cellSize, projectMaxColumn, viewportSize.width],
  );
  const slotCounts = {
    columns: Math.ceil(viewportSize.width / cellSize) + 1,
    rows: Math.ceil(viewportSize.height / cellSize) + 1,
  };

  // ---- IMPERATIVE PLUMBING ----

  /**
   * Requests a repaint on the next animation frame. Multiple calls within a
   * frame coalesce into one draw.
   */
  const markDirty = useCallback(() => {
    dirtyRef.current = true;
  }, []);

  /**
   * Plays a short note preview through the backend for hover/draw feedback.
   */
  const previewPitch = useCallback((pitch, color = null) => {
    editorAPI.playNotePreview(pitch, color, NOTE_PREVIEW_SECONDS).catch(() => {});
  }, []);

  /**
   * Derives the cursor variant from gesture and hover state. React bails on
   * unchanged values, so calling this every pointermove is cheap.
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

    const gestureKind = getGestureKind();
    if (gestureKind === "resize-drag") {
      setCursorOverride("resize");
      return;
    }
    if (gestureKind) {
      setCursorOverride(null);
      return;
    }

    if (brush?.id === "select" && hoverRef.current) {
      const { exactCol, exactRow } = hoverRef.current;
      const nearTail = normalizedNotes.some(
        (note) =>
          note.selected &&
          note.color === activeChannel &&
          isPointNearNoteTail({ note, exactColumn: exactCol, exactRow }),
      );
      if (nearTail) {
        setCursorOverride("resize");
        return;
      }
    }

    setCursorOverride(null);
  }, [activeChannel, brush?.id, interactionBlocked, normalizedNotes, playheadArmed]);

  // rebuild the grid context every render so the imperative modules always
  // see the latest props; palette/stroke are patched in from refs at draw time
  gridRef.current = {
    notes: normalizedNotes,
    activeChannel,
    brushId: brush?.id ?? null,
    selectMode: brush?.id === "select",
    interactionBlocked,
    beatLength,
    beatsPerMeasure,
    keyPitchClasses,
    maxColumn: projectMaxColumn,
    viewport: viewportSize,
    palette: paletteRef.current,
    selectionStroke: selectionStrokeRef.current,
    markDirty,
    refreshCursor,
    previewPitch,
  };

  // ---- POINTER HANDLERS ----

  /**
   * Converts a pointer event into viewport pixels plus grid coordinates.
   */
  const getPoint = useCallback((event) => {
    const viewport = viewportRef.current;
    if (!viewport) return null;
    const bounds = viewport.getBoundingClientRect();
    const x = event.clientX - bounds.left;
    const y = event.clientY - bounds.top;
    return { x, y, ...convertWorldToGrid(x, y) };
  }, []);

  /**
   * Routes pointer-down to the playhead arm or the gesture module.
   */
  const handlePointerDown = useCallback(
    (event) => {
      if (event.button !== 0) return; // only the primary button
      const point = getPoint(event);
      if (!point) return;

      viewportRef.current?.setPointerCapture?.(event.pointerId);
      activePointerIdRef.current = event.pointerId;

      if (playheadArmed) {
        // playhead arm mode: click sets a new playhead home position
        const time = Math.max(0, Math.round(point.exactCol));
        playheadApiRef.current?.setHome(time);
        editorAPI.setPlayheadHome(time).catch(() => {});
        onConsumePlayheadArm?.();
        return;
      }

      handleClick(gridRef.current, point, event);
    },
    [getPoint, onConsumePlayheadArm, playheadArmed],
  );

  /**
   * Tracks hover, moves the custom cursor, and advances the active gesture.
   */
  const handlePointerMove = useCallback(
    (event) => {
      const point = getPoint(event);
      if (!point) return;

      const customCursor = customCursorRef.current;
      if (customCursor) {
        const overScrollbar =
          event.target.closest(".note-grid-overlay-scrollbar") !== null;
        if (overScrollbar) {
          customCursor.dataset.visible = "false";
        } else {
          customCursor.style.transform = `translate3d(${point.x}px, ${point.y}px, 0)`;
          customCursor.dataset.visible = "true";
        }
      }

      hoverRef.current = point;
      refreshCursor();
      handleDrag(gridRef.current, point, event);
    },
    [getPoint, refreshCursor],
  );

  /**
   * Commits the active gesture on pointer-up.
   */
  const handlePointerUp = useCallback(
    (event) => {
      if (
        activePointerIdRef.current !== null &&
        event.pointerId !== activePointerIdRef.current
      )
        return;
      activePointerIdRef.current = null;
      viewportRef.current?.releasePointerCapture?.(event.pointerId);
      handleUnClick(gridRef.current, getPoint(event));
    },
    [getPoint],
  );

  /**
   * Cancels the active gesture when pointer capture is lost unexpectedly.
   */
  const handlePointerCancel = useCallback((event) => {
    if (
      activePointerIdRef.current !== null &&
      event.pointerId !== activePointerIdRef.current
    )
      return;
    activePointerIdRef.current = null;
    cancelGesture(gridRef.current);
  }, []);

  /**
   * Hides the custom cursor when the pointer leaves the viewport.
   */
  const handlePointerLeave = useCallback(() => {
    if (customCursorRef.current) {
      customCursorRef.current.dataset.visible = "false";
    }
    hoverRef.current = null;
  }, []);

  // ---- SCROLLBAR ----

  /**
   * Moves the overlay scrollbar thumb by direct DOM mutation so scrolling
   * never triggers a React commit.
   */
  const applyScrollbarOffset = useCallback(
    (scrollX) => {
      const thumb = scrollbarThumbRef.current;
      if (!thumb) return;

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
          : (scrollX / maxScrollX) * (trackWidth - thumbWidth); // proportional position

      thumb.style.transform = `translateX(${thumbLeft}px)`;
    },
    [maxScrollX, viewportSize.width],
  );

  /**
   * Applies scrollbar thumb drags back to the camera.
   */
  const handleScrollXChange = useCallback(
    (nextScrollX) => {
      const grid = gridRef.current;
      view.col = MIN_COLUMN + nextScrollX / tile.size;
      viewBounds(grid.viewport.width, grid.viewport.height, grid.maxColumn);
      markDirty();
    },
    [markDirty],
  );

  // ---- EFFECTS ----

  // every committed render means some prop changed; repaint on the next frame
  useLayoutEffect(() => {
    markDirty();
  });

  // read the theme palette once the surface is mounted
  useLayoutEffect(() => {
    paletteRef.current = buildCellPalette(surfaceRef.current);
    selectionStrokeRef.current =
      getComputedStyle(surfaceRef.current)
        .getPropertyValue("--tinted-foreground")
        .trim() || "#ffffff";
    markDirty();
  }, [markDirty]);

  // watch the viewport element for size changes
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;

    const resizeObserver = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setViewportSize((current) =>
        current.width === width && current.height === height
          ? current
          : { width, height },
      );
    });

    resizeObserver.observe(viewport);
    return () => resizeObserver.disconnect();
  }, []);

  // re-clamp the camera whenever zoom, viewport, or project width changes
  useLayoutEffect(() => {
    viewBounds(viewportSize.width, viewportSize.height, projectMaxColumn);
    markDirty();
  }, [cellSize, markDirty, projectMaxColumn, viewportSize]);

  // the frame loop: drain the dirty flag with at most one repaint per frame,
  // then bring the scroll-following chrome along with the same camera
  useEffect(() => {
    let frameHandle = 0;

    const tick = () => {
      frameCountRef.current += 1;
      if (dirtyRef.current) {
        dirtyRef.current = false;
        const grid = gridRef.current;
        grid.palette = paletteRef.current;
        grid.selectionStroke = selectionStrokeRef.current;

        // viewport-anchored box selects capture notes that scroll through them
        recaptureBoxSelect(grid);

        drawStatsRef.current = drawFrame(grid, canvasRef.current);
        const scroll = getScrollPosition();
        applyScrollbarOffset(scroll.x);
        tickerApiRef.current?.update(scroll);
        pitchApiRef.current?.update(scroll);
        playheadApiRef.current?.update(scroll);
      }
      frameHandle = requestAnimationFrame(tick);
    };

    frameHandle = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameHandle);
  }, [applyScrollbarOffset]);

  // scroll on wheel input; non-passive so preventDefault works
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;

    /**
     * Pans the camera by the wheel delta and clamps it to the project.
     */
    const handleWheel = (event) => {
      event.preventDefault();
      const grid = gridRef.current;
      view.col += event.deltaX / tile.size;
      view.row -= event.deltaY / tile.size; // wheel down moves the view down the pitch range
      viewBounds(grid.viewport.width, grid.viewport.height, grid.maxColumn);
      markDirty();
    };

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [markDirty]);

  // observe document.head mutations so theme changes re-derive the palette
  useEffect(() => {
    if (typeof MutationObserver === "undefined") return undefined;

    const observer = new MutationObserver(() => {
      paletteRef.current = buildCellPalette(surfaceRef.current);
      selectionStrokeRef.current =
        getComputedStyle(surfaceRef.current)
          .getPropertyValue("--tinted-foreground")
          .trim() || "#ffffff";
      invalidateGridBlock();
      markDirty();
    });

    observer.observe(document.head, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true,
    });
    return () => observer.disconnect();
  }, [markDirty]);

  // clear retained drag previews once the backend echoes the committed notes
  useLayoutEffect(() => {
    reconcileCommitVisual(gridRef.current);
  }, [normalizedNotes]);

  // refresh the cursor when the tool, channel, or arm state changes
  useEffect(() => {
    refreshCursor();
  }, [refreshCursor]);

  // keyboard shortcuts for zoom (ctrl +/-) and the debug readout (i)
  useEffect(() => {
    /**
     * Handles zoom and debug-toggle shortcuts before the global editor layer.
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
      setZoomIndex((current) =>
        clamp(current + (isZoomIn ? 1 : -1), 0, ZOOM_LEVELS.length - 1),
      );
    };

    window.addEventListener("keydown", handleZoomShortcut, { capture: true });
    return () =>
      window.removeEventListener("keydown", handleZoomShortcut, {
        capture: true,
      });
  }, [debugUiEnabled]);

  // gesture modifier keys: alt duplicate, 1-6 channel retarget, escape cancel
  useEffect(() => {
    /**
     * Forwards modifier keys to the gesture module while a drag is active.
     */
    const handleKeyDown = (event) => {
      if (isTextEditingTarget(event.target)) return;
      if (handleHotkeyDown(gridRef.current, event)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    /**
     * Forwards modifier key releases to the gesture module.
     */
    const handleKeyUp = (event) => {
      handleHotkeyUp(gridRef.current, event);
    };

    window.addEventListener("keydown", handleKeyDown, { capture: true });
    window.addEventListener("keyup", handleKeyUp, { capture: true });
    return () => {
      window.removeEventListener("keydown", handleKeyDown, { capture: true });
      window.removeEventListener("keyup", handleKeyUp, { capture: true });
    };
  }, []);

  // hide the debug readout when the debug UI is disabled externally
  useEffect(() => {
    if (!debugUiEnabled) setShowDebugStats(false);
  }, [debugUiEnabled]);

  // sample draw timings into React state at 2Hz while the readout is open
  useEffect(() => {
    if (!showDebugStats) {
      setDebugStats(null);
      return undefined;
    }

    frameCountRef.current = 0;
    const interval = window.setInterval(() => {
      setDebugStats({
        fps: frameCountRef.current * 2, // frames per 500ms window to per-second
        drawMs: drawStatsRef.current.drawMs,
        visibleNotes: drawStatsRef.current.visibleNotes,
      });
      frameCountRef.current = 0;
    }, 500);
    return () => window.clearInterval(interval);
  }, [showDebugStats]);

  // ---- CURSOR DERIVATION ----

  const BrushCursorIcon = brush?.Icon;

  /**
   * Selects the icon for the custom cursor, overriding the brush icon for
   * resize and playhead states.
   */
  const cursorIcon = (() => {
    if (cursorOverride === "disabled") return null;
    if (cursorOverride === "resize") return MoveHorizontal;
    if (cursorOverride === "playhead") return ArrowRightFromLine;
    return BrushCursorIcon;
  })();

  /**
   * Selects the CSS variant name for the custom cursor element.
   */
  const cursorVariant = (() => {
    if (cursorOverride === "resize") return "resize";
    if (cursorOverride === "playhead") return "playhead";
    return brush?.id ?? null;
  })();

  // ---- RENDER ----

  const initialScrollPosition = getScrollPosition();

  return (
    <div
      ref={surfaceRef}
      className="note-grid-surface"
      style={{ "--note-grid-cell-size": `${cellSize}px` }}
    >
      <div className="note-grid-corner" />
      <Ticker
        slotCount={slotCounts.columns}
        cellSize={cellSize}
        beatLength={beatLength}
        beatsPerMeasure={beatsPerMeasure}
        bounds={gridBounds}
        initialScrollPosition={initialScrollPosition}
        layerRef={tickerLayerRef}
        tickerApiRef={tickerApiRef}
      />
      <PitchList
        slotCount={slotCounts.rows}
        cellSize={cellSize}
        bounds={gridBounds}
        initialScrollPosition={initialScrollPosition}
        layerRef={pitchLayerRef}
        pitchApiRef={pitchApiRef}
        onPreviewPitch={(pitch) => previewPitch(pitch)}
      />
      <div
        ref={viewportRef}
        className="note-grid-viewport"
        data-cursor-disabled={interactionBlocked ? "true" : undefined}
        onPointerMove={handlePointerMove}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onPointerLeave={handlePointerLeave}
      >
        <canvas
          ref={canvasRef}
          className="note-grid-canvas"
          style={{ width: viewportSize.width, height: viewportSize.height }}
          aria-hidden="true"
        />
        <Playhead
          viewportSize={viewportSize}
          cellSize={cellSize}
          bounds={gridBounds}
          initialScrollPosition={initialScrollPosition}
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
          scrollX={initialScrollPosition.x}
          maxScrollX={maxScrollX}
          onScrollXChange={handleScrollXChange}
          thumbRef={scrollbarThumbRef}
        />
      </div>
      <Navigator
        zoomIndex={zoomIndex}
        zoomLevels={ZOOM_LEVELS}
        onZoomChange={setZoomIndex}
        debugStats={debugUiEnabled && showDebugStats ? debugStats : null}
      />
    </div>
  );
}

export { ZOOM_LEVELS };
