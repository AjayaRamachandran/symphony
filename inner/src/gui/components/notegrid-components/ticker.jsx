import { useLayoutEffect, useRef } from "react";

function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor;
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
