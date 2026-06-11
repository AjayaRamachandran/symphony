import { useLayoutEffect, useRef } from "react";
import flatIcon from "@/assets/editor-icons/flat.svg?raw";
import { NOTE_PITCH_TO_GRID_ROW_OFFSET } from "../notegrid-utils/note-grid-ops.js";

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

/**
 * Formats a grid row as a pitch label and octave.
 */
function getPitchLabel(row) {
  const pitchClass = PITCH_CLASS_LABELS[positiveModulo(row, 12)];
  const octave = Math.floor(row / 12) - 1;
  return { ...pitchClass, octave };
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
 * Renders fixed pitch labels that update as the grid scrolls vertically.
 */
export function PitchList({
  slotCount,
  cellSize,
  bounds,
  initialScrollPosition,
  layerRef,
  pitchApiRef,
  onPreviewPitch,
}) {
  const slotsRef = useRef([]);

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
    <div className="note-grid-pitch-list" aria-label="Pitches">
      <div ref={layerRef} className="note-grid-pitch-list-layer">
        {Array.from({ length: slotCount }, (_, index) => (
          <div
            key={index}
            ref={(node) => {
              slotsRef.current[index] = node;
            }}
            className="note-grid-pitch-row"
            onMouseDown={(e) => {
              const pitch = Number(e.currentTarget.dataset.pitch);
              if (Number.isFinite(pitch)) onPreviewPitch?.(pitch);
            }}
          >
            <span className="note-grid-pitch-label" style={{fontSize:Math.min(cellSize * 0.7, 14)}}>
              <span data-pitch-note />
              <span
                className="note-grid-pitch-flat"
                data-pitch-flat
                dangerouslySetInnerHTML={{ __html: flatIcon }}
                style={{fontSize:Math.min(cellSize * 0.7, 14)}}
              />
            </span>
            <span className="note-grid-pitch-octave" data-pitch-octave style={{fontSize:Math.min(cellSize * 0.7, 14)}} />
          </div>
        ))}
      </div>
    </div>
  );
}
