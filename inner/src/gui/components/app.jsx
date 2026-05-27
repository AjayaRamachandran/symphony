import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import TitleBar from "@/ui/title-bar";
import appIcon from "@/assets/icon-light.svg";
import ApiInspector from "./api-inspector.jsx";
import editorAPI from "../editor-bridge.js";
import {
  BRUSHES,
  CHANNELS,
  DRAW_BRUSH_INDEX,
  ERASER_BRUSH_INDEX,
  SELECT_BRUSH_INDEX,
} from "./toolbar-options.jsx";
import EditorSurface from "./content.jsx";
import "./components-styling/index.css";

// Temporary API inspection surface. This is not the real editor UI; it only
// confirms that the inner pywebview window mounted React and can reach the
// backend handler surface registered on ``window.pywebview.api``. Press
// Alt/Option + I to toggle between this inspector and the placeholder editor.
const SHOW_API_INSPECTOR_BY_DEFAULT = true;

function isTextEditingTarget(target) {
  if (!target) return false;
  const tagName = target.tagName?.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select" || target.isContentEditable;
}

function getPlaybackEndTime(noteMap, currentColorIdx) {
  if (!noteMap || typeof noteMap !== "object") return 0;

  const channelName = CHANNELS[currentColorIdx]?.name;
  const noteLists = channelName && channelName !== "all" ? [noteMap[channelName]] : Object.values(noteMap);
  let latestEnd = 0;

  for (const notes of noteLists) {
    if (!Array.isArray(notes)) continue;
    for (const note of notes) {
      const time = Number(note?.time);
      const duration = Number(note?.duration);
      if (!Number.isFinite(time) || !Number.isFinite(duration) || duration <= 0) continue;
      latestEnd = Math.max(latestEnd, time + duration);
    }
  }

  return latestEnd;
}

export default function EditorApp() {
  const [showApiInspector, setShowApiInspector] = useState(SHOW_API_INSPECTOR_BY_DEFAULT);
  const [bridgeReady, setBridgeReady] = useState(false);
  const [docState, setDocState] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackClock, setPlaybackClock] = useState(null);
  const [playheadArmed, setPlayheadArmed] = useState(false);
  const [brushIndex, setBrushIndex] = useState(0);
  const [tempo, setTempo] = useState(360);
  const [beatLength, setBeatLength] = useState(4);
  const [beatsPerMeasure, setBeatsPerMeasure] = useState(4);
  const playbackRequestIdRef = useRef(0);
  const playbackEndTimerRef = useRef(0);

  const brush = BRUSHES[brushIndex];
  const editorTitle = useMemo(() => {
    const title = docState?.title || "Symphony Editor";
    return `${title} - Symphony`;
  }, [docState?.title]);

  const updateDocState = (patch) => {
    setDocState((current) => (current ? { ...current, ...patch } : current));
  };

  useEffect(() => {
    let cancelled = false;
    editorAPI
      .getDocumentState()
      .then((state) => {
        if (cancelled) return;
        setBridgeReady(true);
        setDocState(state);
        setTempo(Number(state?.tempo ?? 360));
        setBeatLength(Number(state?.beatLength ?? 4));
        setBeatsPerMeasure(Number(state?.beatsPerMeasure ?? 4));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
      });

    const off = editorAPI.onEditorStateChange((state) => {
      if (!cancelled) {
        setDocState(state);
        setTempo(Number(state?.tempo ?? 360));
        setBeatLength(Number(state?.beatLength ?? 4));
        setBeatsPerMeasure(Number(state?.beatsPerMeasure ?? 4));
      }
    });

    return () => {
      cancelled = true;
      off?.();
    };
  }, []);

  const handleTogglePlayback = useCallback(() => {
    if (isPlaying) {
      playbackRequestIdRef.current += 1;
      window.clearTimeout(playbackEndTimerRef.current);
      setIsPlaying(false);
      setPlaybackClock(null);
      editorAPI.stopPlayback().catch((err) => setError(String(err)));
      return;
    }

    const requestId = playbackRequestIdRef.current + 1;
    playbackRequestIdRef.current = requestId;
    window.clearTimeout(playbackEndTimerRef.current);
    setIsPlaying(true);
    const fromTime = Number(docState?.playheadHomeTime ?? 0);
    const endTime = getPlaybackEndTime(docState?.noteMap, Number(docState?.currentColorIdx ?? 0));
    editorAPI
      .playFull({ fromTime })
      .then((result) => {
        if (playbackRequestIdRef.current !== requestId) return;
        if (result?.ok === false) throw new Error(result.error || "Playback failed");
        const startedAtMs = performance.now();
        setPlaybackClock({
          fromTime,
          startedAtMs,
        });
        const remainingMs = Math.max(0, ((endTime - fromTime) * 60_000) / Math.max(1, Number(tempo) || 1));
        playbackEndTimerRef.current = window.setTimeout(() => {
          if (playbackRequestIdRef.current !== requestId) return;
          setIsPlaying(false);
          setPlaybackClock(null);
        }, Math.max(80, remainingMs));
      })
      .catch((err) => {
        if (playbackRequestIdRef.current !== requestId) return;
        setIsPlaying(false);
        setPlaybackClock(null);
        setError(String(err));
      });
  }, [docState?.currentColorIdx, docState?.noteMap, docState?.playheadHomeTime, isPlaying, tempo]);

  useEffect(() => () => window.clearTimeout(playbackEndTimerRef.current), []);

  const handleSelectActiveChannelNotes = useCallback(() => {
    const activeChannel = CHANNELS[docState?.currentColorIdx ?? 0]?.name;
    const entries = Object.entries(docState?.noteMap ?? {}).flatMap(([color, notes]) => {
      if (activeChannel && activeChannel !== "all" && color !== activeChannel) return [];
      if (!Array.isArray(notes)) return [];
      return notes.map((note) => ({
        color,
        time: note.time,
        pitch: note.pitch,
      }));
    });

    editorAPI.setSelection(entries).catch((err) => setError(String(err)));
  }, [docState?.currentColorIdx, docState?.noteMap]);

  const commitDocumentNumber = (key, value, setter, apiCall) => {
    setter(value);
    updateDocState({ [key]: value });
    apiCall(value).catch((err) => setError(String(err)));
  };

  const handleToggleAccidentals = () => {
    const next = docState?.accidentals === "flats" ? "sharps" : "flats";
    updateDocState({ accidentals: next });
    editorAPI.setAccidentals(next).catch((err) => setError(String(err)));
  };

  const handleCycleBrush = () => {
    setBrushIndex((current) => (current + 1) % BRUSHES.length);
  };

  // Leaving select mode clears any active selection so the user does not
  // carry an invisible-but-still-recorded selection into draw/erase mode.
  const previousBrushIndexRef = useRef(brushIndex);
  useEffect(() => {
    if (
      previousBrushIndexRef.current === SELECT_BRUSH_INDEX &&
      brushIndex !== SELECT_BRUSH_INDEX
    ) {
      editorAPI.clearSelection().catch((err) => setError(String(err)));
    }
    previousBrushIndexRef.current = brushIndex;
  }, [brushIndex]);

  const handleSetActiveColor = (index) => {
    updateDocState({ currentColorIdx: index });
    editorAPI.setActiveColor(index).catch((err) => setError(String(err)));
  };

  const handleCycleColor = () => {
    const nextIndex = ((docState?.currentColorIdx ?? 0) + 1) % CHANNELS.length;
    handleSetActiveColor(nextIndex);
  };

  const handleSetInstrument = (colorName, value) => {
    const instrumentMap = { ...(docState?.instrumentMap ?? {}), [colorName]: value };
    updateDocState({ instrumentMap });
    editorAPI.setWaveType(colorName, value).catch((err) => setError(String(err)));
  };

  const handleSetKey = (key) => {
    updateDocState({ key });
    editorAPI.setKey(key).catch((err) => setError(String(err)));
  };

  const handleSetMode = (mode) => {
    updateDocState({ mode });
    editorAPI.setMode(mode).catch((err) => setError(String(err)));
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      const isInspectorShortcut =
        event.altKey && !event.repeat && (event.code === "KeyI" || event.key.toLowerCase() === "i");
      if (isInspectorShortcut) {
        event.preventDefault();
        setShowApiInspector((current) => !current);
        return;
      }

      if (isTextEditingTarget(event.target)) return;

      if (event.key === "Shift") {
        setBrushIndex(SELECT_BRUSH_INDEX);
        return;
      }

      if (event.key === "Control") {
        setBrushIndex(ERASER_BRUSH_INDEX);
        return;
      }

      if (!event.repeat && event.code === "Space") {
        event.preventDefault();
        handleTogglePlayback();
        return;
      }

      if (!event.ctrlKey && !event.metaKey && !event.altKey && event.key.toLowerCase() === "a") {
        event.preventDefault();
        handleSelectActiveChannelNotes();
        return;
      }

      if (event.key === "Backspace" || event.key === "Delete") {
        event.preventDefault();
        editorAPI.deleteSelectedNotes().catch((err) => setError(String(err)));
        return;
      }

      if (/^[1-7]$/.test(event.key)) {
        event.preventDefault();
        handleSetActiveColor(Number(event.key) - 1);
      }
    };

    const handleKeyUp = (event) => {
      if (isTextEditingTarget(event.target)) return;

      if (event.key === "Control") {
        setBrushIndex(DRAW_BRUSH_INDEX);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [handleSelectActiveChannelNotes, handleSetActiveColor, handleTogglePlayback]);

  return (
    <>
      <TitleBar title={editorTitle} icon={appIcon} api={editorAPI} />
      {showApiInspector ? (
        <ApiInspector bridgeReady={bridgeReady} docState={docState} error={error} />
      ) : (
        <EditorSurface
          docState={docState}
          isPlaying={isPlaying}
          playbackClock={playbackClock}
          playheadArmed={playheadArmed}
          brush={brush}
          tempo={tempo}
          beatLength={beatLength}
          beatsPerMeasure={beatsPerMeasure}
          onTogglePlayback={handleTogglePlayback}
          onToggleAccidentals={handleToggleAccidentals}
          onTogglePlayhead={() => setPlayheadArmed((current) => !current)}
          onCycleBrush={handleCycleBrush}
          onSetTempo={(value) => commitDocumentNumber("tempo", value, setTempo, editorAPI.setTempo)}
          onSetBeatLength={(value) => commitDocumentNumber("beatLength", value, setBeatLength, editorAPI.setBeatLength)}
          onSetBeatsPerMeasure={(value) =>
            commitDocumentNumber("beatsPerMeasure", value, setBeatsPerMeasure, editorAPI.setBeatsPerMeasure)
          }
          onCycleColor={handleCycleColor}
          onSetInstrument={handleSetInstrument}
          onSetKey={handleSetKey}
          onSetMode={handleSetMode}
          onConsumePlayheadArm={() => setPlayheadArmed(false)}
        />
      )}
    </>
  );
}
