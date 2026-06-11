/**
 * Derives grid cell background colors from the active CSS theme and renders
 * each cell based on its beat, downbeat, and in-key position.
 */

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

/**
 * Reads a CSS custom property from the document root with a safe fallback.
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
 * Reads a numeric CSS custom property from an element, returning a fallback
 * if the element is missing or the value is not a finite number.
 */
function readCssNumber(element, variableName, fallback) {
  if (!element) return fallback;
  const value = Number(
    getComputedStyle(element).getPropertyValue(variableName).trim(),
  );
  return Number.isFinite(value) ? value : fallback;
}

/**
 * Parses a hex or rgb/rgba CSS color string into separate r, g, b channels.
 * Returns null for unrecognized formats.
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
 * Formats an rgb channel object as a lowercase hex color string.
 */
function formatHexColor({ r, g, b }) {
  return `#${[r, g, b]
    .map((channel) => Math.round(channel).toString(16).padStart(2, "0"))
    .join("")}`;
}

/**
 * Averages r, g, b into a single neutral grayscale channel value.
 * Returns null if the color cannot be parsed.
 */
function getNeutralChannel(color) {
  const parsed = parseCssColor(color);
  if (!parsed) return null;
  return Math.round((parsed.r + parsed.g + parsed.b) / 3);
}

/**
 * Converts a grayscale channel value to a hex color, clamped to [0, 255].
 */
function formatNeutralShade(channel) {
  const safeChannel = Math.min(255, Math.max(0, Math.round(channel)));
  return formatHexColor({ r: safeChannel, g: safeChannel, b: safeChannel });
}

/**
 * Shifts a theme color lighter or darker by an offset while keeping it neutral.
 * Falls back to the original color if parsing fails.
 */
function offsetThemeGray(baseColor, offset) {
  const channel = getNeutralChannel(baseColor);
  if (channel === null) return baseColor;
  return formatNeutralShade(channel + offset);
}

/**
 * Reads the current theme background and CSS offset variables from the given
 * element, then returns a full palette of per-cell-type fill colors.
 */
export function buildCellPalette(sourceElement) {
  const background = readRootThemeColor(
    "--background",
    ROOT_THEME_COLORS.background,
  );

  /**
   * Reads one named offset variable from the grid surface element.
   */
  const getOffset = (name, fallback) =>
    readCssNumber(sourceElement, name, fallback);

  return {
    base: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-base-offset", GRID_CELL_OFFSET_FALLBACKS.base),
    ),
    inKey: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-in-key-offset", GRID_CELL_OFFSET_FALLBACKS.inKey),
    ),
    beat: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-beat-offset", GRID_CELL_OFFSET_FALLBACKS.beat),
    ),
    beatInKey: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-beat-in-key-offset", GRID_CELL_OFFSET_FALLBACKS.beatInKey),
    ),
    downBeat: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-downbeat-offset", GRID_CELL_OFFSET_FALLBACKS.downBeat),
    ),
    downBeatInKey: offsetThemeGray(
      background,
      getOffset("--note-grid-cell-downbeat-in-key-offset", GRID_CELL_OFFSET_FALLBACKS.downBeatInKey),
    ),
  };
}

/**
 * Chooses a fill color for one grid cell based on beat position and key membership.
 * Downbeats outrank beats; in-key status is a secondary modifier for both.
 */
export function getCellFill({
  column,
  row,
  keyPitchClasses,
  beatLength,
  beatsPerMeasure,
  cellPalette,
}) {
  const beatSize = Math.max(1, Number(beatLength) || 1);
  const measureSize = beatSize * Math.max(1, Number(beatsPerMeasure) || 1); // beats to measure cells
  const isBeatStart = ((column % beatSize) + beatSize) % beatSize === 0;
  const isDownBeat = ((column % measureSize) + measureSize) % measureSize === 0;
  const isInKey = keyPitchClasses.has(((row % 12) + 12) % 12);

  if (isDownBeat && isInKey) return cellPalette.downBeatInKey;
  if (isDownBeat) return cellPalette.downBeat;
  if (isBeatStart && isInKey) return cellPalette.beatInKey;
  if (isBeatStart) return cellPalette.beat;
  if (isInKey) return cellPalette.inKey;
  return cellPalette.base;
}
