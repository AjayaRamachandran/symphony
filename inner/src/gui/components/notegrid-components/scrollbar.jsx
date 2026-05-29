import { Hand, HandGrab } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";

export const OVERLAY_SCROLLBAR_TRACK_INSET = 6;
export const MIN_SCROLLBAR_THUMB_WIDTH = 44;

/**
 * Bounds a number between a minimum and maximum value.
 */
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Renders the horizontal overlay scrollbar with a custom hover cursor.
 */
export function OverlayScrollbar({
  viewportWidth,
  scrollX,
  maxScrollX,
  onScrollXChange,
  thumbRef,
}) {
  const trackRef = useRef(null);
  const dragOffsetRef = useRef(0);
  const [cursorState, setCursorState] = useState({
    visible: false,
    grabbing: false,
    x: 0,
    y: 0,
  });
  const trackWidth = Math.max(
    0,
    viewportWidth - OVERLAY_SCROLLBAR_TRACK_INSET * 2,
  );

  /**
   * Derives thumb width from visible viewport and total scrollable content.
   */
  const thumbWidth = useMemo(() => {
    if (trackWidth <= 0 || maxScrollX <= 0) return trackWidth;
    const contentWidth = viewportWidth + maxScrollX;
    return clamp(
      (viewportWidth / contentWidth) * trackWidth,
      MIN_SCROLLBAR_THUMB_WIDTH,
      trackWidth,
    );
  }, [maxScrollX, trackWidth, viewportWidth]);

  /**
   * Derives thumb x position from the current scroll offset.
   */
  const thumbLeft = useMemo(() => {
    if (maxScrollX <= 0 || trackWidth <= thumbWidth) return 0;
    return (scrollX / maxScrollX) * (trackWidth - thumbWidth);
  }, [maxScrollX, scrollX, thumbWidth, trackWidth]);

  /**
   * Converts thumb dragging into horizontal grid scroll.
   */
  const syncPointer = useCallback(
    (clientX) => {
      const track = trackRef.current;
      if (!track || maxScrollX <= 0) return;

      const rect = track.getBoundingClientRect();
      const maxThumbLeft = Math.max(0, rect.width - thumbWidth);
      const nextLeft = clamp(
        clientX - rect.left - dragOffsetRef.current,
        0,
        maxThumbLeft,
      );
      const nextScrollX = (nextLeft / Math.max(1, maxThumbLeft)) * maxScrollX; // thumb px to scroll px
      onScrollXChange(nextScrollX);
    },
    [maxScrollX, onScrollXChange, thumbWidth],
  );

  /**
   * Tracks pointer position for the custom scrollbar cursor.
   */
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

  /**
   * Ends dragging and hides the custom cursor when the pointer leaves the track.
   */
  const releaseCursor = useCallback((event) => {
    const track = trackRef.current;
    if (!track) {
      setCursorState((current) => ({
        ...current,
        visible: false,
        grabbing: false,
      }));
      return;
    }

    const rect = track.getBoundingClientRect();
    const pointerInside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;

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
        setCursorState((current) =>
          current.grabbing ? current : { ...current, visible: false },
        );
      }}
    >
      <div
        ref={thumbRef}
        className="note-grid-overlay-scrollbar-thumb"
        onPointerDown={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          if (!rect) return;

          event.currentTarget.setPointerCapture(event.pointerId);
          dragOffsetRef.current = clamp(
            event.clientX - rect.left,
            0,
            thumbWidth,
          );
          syncCursor(event, { grabbing: true });
        }}
        onPointerMove={(event) => {
          if (event.buttons !== 1) return;
          syncPointer(event.clientX);
          syncCursor(event, { grabbing: true });
        }}
        onPointerUp={releaseCursor}
        onPointerCancel={() => {
          setCursorState((current) => ({
            ...current,
            visible: false,
            grabbing: false,
          }));
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
        <ScrollbarCursorIcon
          className="note-grid-overlay-scrollbar-cursor-outline"
          aria-hidden="true"
        />
        <ScrollbarCursorIcon
          className="note-grid-overlay-scrollbar-cursor-fill"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
