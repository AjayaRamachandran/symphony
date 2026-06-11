import { ZoomIn, ZoomOut } from "lucide-react";

/**
 * Formats optional diagnostic numbers without leaking NaN into the debug strip.
 */
function formatNumber(value, digits = 0) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

/**
 * Renders zoom controls and an optional draw-performance readout.
 */
export function Navigator({ zoomIndex, zoomLevels, onZoomChange, debugStats = null }) {
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
      {debugStats ? (
        <div className="note-grid-debug" aria-label="Grid debug information">
          <span>{formatNumber(debugStats.fps)} fps</span>
          <span>{formatNumber(debugStats.drawMs, 2)} ms draw</span>
          <span>{debugStats.visibleNotes} notes drawn</span>
        </div>
      ) : null}
    </div>
  );
}
