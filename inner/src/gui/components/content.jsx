import { HelpCircle, Milestone, Pause, Play } from "lucide-react";
import editorAPI from "../editor-bridge.js";
import { IconButton } from "./toolbar-components/icon-button.jsx";
import { StepperField } from "./toolbar-components/stepper-field.jsx";
import { SvgAssetIcon } from "./toolbar-components/svg-asset-icon.jsx";
import { ToolbarDropdown } from "./toolbar-components/toolbar-dropdown.jsx";
import {
  BRUSHES,
  CHANNELS,
  HELP_URL,
  INSTRUMENT_OPTIONS,
  KEY_OPTIONS,
  MODE_OPTIONS,
  flatIcon,
  sharpIcon,
} from "./toolbar-options.jsx";
import NoteGrid from "./notegrid.jsx";

/**
 * Composes the editor toolbar, active controls, and note grid surface.
 */
export default function EditorSurface({
  docState,
  isPlaying,
  playbackClock,
  playheadArmed,
  brush,
  tempo,
  beatLength,
  beatsPerMeasure,
  onTogglePlayback,
  onToggleAccidentals,
  onTogglePlayhead,
  onCycleBrush,
  onSetTempo,
  onSetBeatLength,
  onSetBeatsPerMeasure,
  onCycleColor,
  onSetInstrument,
  onSetKey,
  onSetMode,
  onConsumePlayheadArm,
  debugUiEnabled = false,
  showDebugByDefault = false,
}) {
  const colorIndex = Math.max(
    0,
    Math.min(6, Number(docState?.currentColorIdx ?? 0)),
  );
  const activeChannel = CHANNELS[colorIndex];
  const activeColorName = activeChannel.name;
  const currentInstrumentValue =
    docState?.instrumentMap?.[activeColorName] ?? 0;
  const instrumentValue =
    INSTRUMENT_OPTIONS.find(
      (option) => option.value === currentInstrumentValue,
    ) ?? INSTRUMENT_OPTIONS[0];
  const keyValue =
    KEY_OPTIONS.find((option) => option.value === docState?.key) ??
    KEY_OPTIONS[0];
  const modeValue =
    MODE_OPTIONS.find((option) => option.value === docState?.mode) ??
    MODE_OPTIONS[1];
  const BrushIcon = brush.Icon;

  return (
    <div
      className="editor-content-shell"
      style={{ "--brush-accent": brush.color }}
    >
      <div className="editor-border-top" />
      <div className="editor-toolbar">
        <div className="editor-toolbar-side">
          <div className="editor-fused-icon-group" aria-label="Editor tools">
            <IconButton
              label={isPlaying ? "Pause playback" : "Play audio"}
              shortcut="Space"
              color={isPlaying ? "var(--inactive-bad)" : "var(--active-good)"}
              className="editor-square-button"
              onClick={onTogglePlayback}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            </IconButton>

            <IconButton
              label={`Toggle accidentals (${docState?.accidentals === "flats" ? "flats" : "sharps"})`}
              className="editor-square-button editor-cycle-button"
              sizingContent={[flatIcon, sharpIcon].map((icon) => (
                <span key={icon} className="editor-cycle-button-sizer-item">
                  <SvgAssetIcon source={icon} size={15} />
                </span>
              ))}
              onClick={onToggleAccidentals}
            >
              <SvgAssetIcon
                source={
                  docState?.accidentals === "flats" ? flatIcon : sharpIcon
                }
                size={15}
              />
            </IconButton>

            <IconButton
              label="Set playhead"
              isActive={playheadArmed}
              color="var(--primary)"
              className="editor-square-button"
              onClick={onTogglePlayhead}
            >
              <Milestone size={15} />
            </IconButton>

            <IconButton
              label={brush.label}
              color={brush.color}
              className="editor-square-button editor-cycle-button"
              sizingContent={BRUSHES.map(({ id, Icon }) => (
                <span key={id} className="editor-cycle-button-sizer-item">
                  <Icon size={15} />
                </span>
              ))}
              onClick={onCycleBrush}
            >
              <BrushIcon size={15} />
            </IconButton>
          </div>

          <span className="editor-toolbar-separator" />

          <StepperField
            label="Beat length (in tiles)"
            suffix="tiles"
            value={beatLength}
            min={1}
            onCommit={onSetBeatLength}
          />
          <StepperField
            label="Beats per measure"
            suffix="beats"
            value={beatsPerMeasure}
            min={1}
            onCommit={onSetBeatsPerMeasure}
          />
        </div>

        <div className="editor-toolbar-side right">
          <StepperField
            label="Tempo"
            suffix="tpm"
            value={tempo}
            min={1}
            onCommit={onSetTempo}
          />
          <div
            className="editor-fused-channel-instrument-group"
            aria-label="Channel and instrument"
          >
            <IconButton
              label={`Color channel: ${activeChannel.label}`}
              shortcut="Numkeys 1-7"
              className="editor-square-button editor-channel-button"
              style={{ "--channel-color": activeChannel.color }}
              onClick={onCycleColor}
            >
              {colorIndex + 1}
            </IconButton>

            <ToolbarDropdown
              label="Instrument"
              options={INSTRUMENT_OPTIONS}
              value={instrumentValue}
              onSelect={(option) =>
                onSetInstrument(activeColorName, option.value)
              }
            />
          </div>
          <div
            className="editor-fused-dropdown-group"
            aria-label="Key and mode"
          >
            <ToolbarDropdown
              label="Key"
              options={KEY_OPTIONS}
              value={keyValue}
              onSelect={(option) => onSetKey(option.value)}
            />
            <ToolbarDropdown
              label="Mode"
              options={MODE_OPTIONS}
              value={modeValue}
              onSelect={(option) => onSetMode(option.value)}
            />
          </div>

          <IconButton
            label="Open Symphony help"
            className="editor-square-button"
            onClick={() =>
              editorAPI
                .openExternalUrl(HELP_URL)
                .catch(() =>
                  window.open(HELP_URL, "_blank", "noopener,noreferrer"),
                )
            }
          >
            <HelpCircle size={15} />
          </IconButton>
        </div>
      </div>
      <div className="editor-brush-line" />
      <NoteGrid
        beatLength={beatLength}
        beatsPerMeasure={beatsPerMeasure}
        brush={brush}
        keySignature={docState?.key}
        mode={docState?.mode}
        noteMap={docState?.noteMap}
        currentColorIdx={colorIndex}
        isPlaying={isPlaying}
        playheadHomeTime={docState?.playheadHomeTime}
        playbackClock={playbackClock}
        tempo={tempo}
        playheadArmed={playheadArmed}
        onConsumePlayheadArm={onConsumePlayheadArm}
        debugUiEnabled={debugUiEnabled}
        showDebugByDefault={showDebugByDefault}
      />
    </div>
  );
}
