import { useEffect, useMemo, useState } from "react";
import TitleBar from "@/ui/title-bar";
import appIcon from "@/assets/icon-light.svg";
import ApiInspector from "./api-inspector.jsx";
import editorAPI from "./editor-bridge.js";
import {
  BRUSHES,
  CHANNELS,
  DRAW_BRUSH_INDEX,
  ERASER_BRUSH_INDEX,
  SELECT_BRUSH_INDEX,
} from "./editor-options.jsx";
import EditorSurface from "./editor-surface.jsx";
import "./editor-app.css";

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

export default function EditorApp() {
  const [showApiInspector, setShowApiInspector] = useState(SHOW_API_INSPECTOR_BY_DEFAULT);
  const [bridgeReady, setBridgeReady] = useState(false);
  const [docState, setDocState] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playheadArmed, setPlayheadArmed] = useState(false);
  const [brushIndex, setBrushIndex] = useState(0);
  const [tempo, setTempo] = useState(360);
  const [beatLength, setBeatLength] = useState(4);
  const [beatsPerMeasure, setBeatsPerMeasure] = useState(4);

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

  const handleTogglePlayback = () => {
    if (isPlaying) {
      setIsPlaying(false);
      editorAPI.stopPlayback().catch((err) => setError(String(err)));
      return;
    }

    setIsPlaying(true);
    editorAPI.playFull({}).catch((err) => {
      setIsPlaying(false);
      setError(String(err));
    });
  };

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
  });

  return (
    <>
      <TitleBar title={editorTitle} icon={appIcon} api={editorAPI} />
      {showApiInspector ? (
        <ApiInspector bridgeReady={bridgeReady} docState={docState} error={error} />
      ) : (
        <EditorSurface
          docState={docState}
          isPlaying={isPlaying}
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
        />
      )}
    </>
  );
}
