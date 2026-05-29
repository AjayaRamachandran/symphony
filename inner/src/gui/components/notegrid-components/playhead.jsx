import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

/**
 * Renders and animates the playhead independently from grid re-renders.
 */
export function Playhead({
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

  /**
   * Places the playhead for a world time against the current scroll offset.
   */
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
        const {
          isPlaying: playing,
          playbackClock: clock,
          tempo: currentTempo,
        } = playbackRef.current;
        if (!playing || !clock) {
          placePlayhead(homeTimeRef.current);
          return;
        }

        const elapsedSeconds = Math.max(
          0,
          (performance.now() - clock.startedAtMs) / 1000, // perf clock to seconds
        );
        placePlayhead(
          clock.fromTime +
            elapsedSeconds * (Math.max(1, Number(currentTempo) || 1) / 60), // seconds to tiles
        );
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
    /**
     * Advances the playhead every animation frame during playback.
     */
    const tick = () => {
      const elapsedSeconds = Math.max(
        0,
        (performance.now() - playbackClock.startedAtMs) / 1000, // perf clock to seconds
      );
      placePlayhead(
        playbackClock.fromTime +
          elapsedSeconds * (Math.max(1, Number(tempo) || 1) / 60), // seconds to tiles
      );
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
