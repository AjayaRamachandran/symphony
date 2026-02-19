import React, { useState, useEffect } from "react";

import { FolderClosed, KeyboardMusic, FileMusic } from "lucide-react";
import path from "path-browserify";

import Dropdown from "@/ui/Dropdown";
import Field from "@/ui/Field";
import { useDirectory } from "@/contexts/DirectoryContext";
import InitExportFolder from "@/modals/InitExportFolder";
import GenericModal from "@/modals/GenericModal";
import "./convert-modal.css";

const formats = [
  { label: "MIDI", icon: KeyboardMusic },
  { label: "MusicXML", icon: FileMusic },
];

const conversionMethods = [
  { label: "Automatic (from Symphony project)", value: "automatic" },
  { label: "Custom", value: "custom" },
];

const dynamicsOptions = [{ label: "None", value: "none" }];
const keyOptions = [
  "C",
  "Db",
  "D",
  "Eb",
  "E",
  "F",
  "Gb",
  "G",
  "Ab",
  "A",
  "Bb",
  "B",
].map((key) => ({ label: key, value: key }));
const modeOptions = [
  "Lydian",
  "Ionian (maj.)",
  "Mixolydian",
  "Dorian",
  "Aeolian (min.)",
  "Phrygian",
  "Locrian",
].map((mode) => ({ label: mode, value: mode }));

const builtinPresets = [
  { name: "Vocals:  6-part choir (SMATBB)", value: "builtin:vocals-6" },
  { name: "Vocals:  All-Treble choir (SSMMAA)", value: "builtin:treble-6" },
  { name: "Vocals:  All-Bass choir (TTBBBB)", value: "builtin:bass-6" },
];

const builtinPresetColorClefMaps = {
  "vocals-6": {
    orange: "Treble (8va)",
    lime: "Treble",
    purple: "Treble",
    cyan: "Treble",
    pink: "Treble (8vb)",
    blue: "Bass",
  },
  "treble-6": {
    orange: "Treble (8va)",
    lime: "Treble (8va)",
    purple: "Treble",
    cyan: "Treble",
    pink: "Treble",
    blue: "Treble",
  },
  "bass-6": {
    orange: "Treble (8vb)",
    lime: "Treble (8vb)",
    purple: "Bass",
    cyan: "Bass",
    pink: "Bass (8vb)",
    blue: "Bass (8vb)",
  },
};

const presetCreatorOption = {
  label: "Make Preset...",
  value: "__create_preset__",
};

const colorKeys = ["orange", "purple", "cyan", "lime", "blue", "pink"];

const clefOptions = [
  "Treble",
  "Treble (8va)",
  "Treble (8vb)",
  "Soprano",
  "Mezzo-soprano",
  "Alto",
  "Tenor",
  "Bass",
  "Bass (8vb)",
].map((clef) => ({ label: clef, value: clef }));

const coerceNumberOrAuto = (value) => {
  const trimmed = String(value ?? "").trim();
  if (trimmed === "") return "auto";
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isNaN(parsed) ? "auto" : parsed;
};

function ConvertModal({ onClose, onComplete }) {
  const [destination, setDestination] = useState(null);
  const [format, setFormat] = useState(null);
  const [folders, setFolders] = useState([]);
  const [showInitExportFolder, setShowInitExportFolder] = useState(false);
  const [flowStep, setFlowStep] = useState("select");
  const [conversionMethod, setConversionMethod] = useState("automatic");
  const [tempoBpm, setTempoBpm] = useState("144");
  const [keySignatureKey, setKeySignatureKey] = useState("Eb");
  const [keySignatureMode, setKeySignatureMode] = useState("Lydian");
  const [dynamics, setDynamics] = useState("none");
  const [timeSigNumerator, setTimeSigNumerator] = useState("4");
  const [timeSigDenominator, setTimeSigDenominator] = useState("4");
  const [instrumentPreset, setInstrumentPreset] = useState("builtin:vocals-6");
  const [userClefPresets, setUserClefPresets] = useState({});
  const [newPresetName, setNewPresetName] = useState("");
  const [newPresetMap, setNewPresetMap] = useState({
    orange: "Treble",
    purple: "Treble",
    cyan: "Treble",
    lime: "Treble",
    blue: "Treble",
    pink: "Treble",
  });
  const [presetError, setPresetError] = useState("");
  const [showPresetModal, setShowPresetModal] = useState(false);

  const { globalDirectory, setGlobalDirectory, selectedFile, setSelectedFile } =
    useDirectory();

  useEffect(() => {
    window.electronAPI.getDirectory().then((result) => {
      const rawExports = result["Exports"];
      const formatted = rawExports.map((obj) => {
        const [label, value] = Object.entries(obj)[0];
        return {
          label: `${label}`,
          value,
          icon: FolderClosed,
        };
      });
      setFolders(formatted);
      console.log(formatted);
      if (formatted.length === 0) {
        setShowInitExportFolder(true);
      }
    });

    window.electronAPI.getUserSettings().then((settings) => {
      const loadedPresets = settings?.clef_presets ?? {};
      if (
        loadedPresets &&
        typeof loadedPresets === "object" &&
        !Array.isArray(loadedPresets)
      ) {
        setUserClefPresets(loadedPresets);
      }
    });
  }, []);

  const customPresetOptions = Object.entries(userClefPresets).map(
    ([presetId, preset]) => ({
      label: preset?.name || "Unnamed preset",
      value: `custom:${presetId}`,
    }),
  );
  const presetOptions = [
    ...builtinPresets.map((preset) => ({
      label: preset.name,
      value: preset.value,
    })),
    ...customPresetOptions,
    presetCreatorOption,
  ];

  const selectedFormat = formats.find((opt) => opt.label === format) || null;
  const selectedFolder =
    folders.find((opt) => opt.label === destination) || null;
  const selectedMethod =
    conversionMethods.find((opt) => opt.value === conversionMethod) ||
    conversionMethods[0];
  const selectedDynamics =
    dynamicsOptions.find((opt) => opt.value === dynamics) || dynamicsOptions[0];
  const selectedKey =
    keyOptions.find((opt) => opt.value === keySignatureKey) || keyOptions[0];
  const selectedMode =
    modeOptions.find((opt) => opt.value === keySignatureMode) || modeOptions[0];
  const selectedPreset =
    presetOptions.find((opt) => opt.value === instrumentPreset) || presetOptions[0];

  const isMusicXmlFlow = format === "MusicXML";
  const isCustomMusicXml = conversionMethod === "custom";
  const canSubmit = Boolean(selectedFile && selectedFolder && selectedFormat);

  useEffect(() => {
    if (
      flowStep !== "musicxml" ||
      !isMusicXmlFlow ||
      !selectedFile ||
      !globalDirectory
    ) {
      return;
    }

    let cancelled = false;
    const hydrateFromFileDetails = async () => {
      try {
        const result = await window.electronAPI.doProcessCommand(
          path.join(globalDirectory, path.basename(selectedFile)),
          "retrieve",
        );
        const fileInfo = result?.payload?.fileInfo;
        if (!fileInfo || cancelled) return;

        const tempoTpm = Number(fileInfo["Tempo (tpm)"]);
        const beatsPerMeasure = Number(fileInfo["Beats Per Measure"]);
        if (
          Number.isFinite(tempoTpm) &&
          Number.isFinite(beatsPerMeasure) &&
          beatsPerMeasure > 0
        ) {
          setTempoBpm(String(Math.round(tempoTpm / beatsPerMeasure)));
        }

        const directKey = String(fileInfo["Key"] ?? "").trim();
        const directMode = String(fileInfo["Mode"] ?? "").trim();
        const keySignatureString = String(fileInfo["Key Signature"] ?? "").trim();

        let hydratedKey = directKey;
        let hydratedMode = directMode;
        if ((!hydratedKey || !hydratedMode) && keySignatureString) {
          const split = keySignatureString.split(" ");
          hydratedKey = split[0] ?? hydratedKey;
          hydratedMode = split.slice(1).join(" ") || hydratedMode;
        }

        if (keyOptions.some((opt) => opt.value === hydratedKey)) {
          setKeySignatureKey(hydratedKey);
        }
        if (modeOptions.some((opt) => opt.value === hydratedMode)) {
          setKeySignatureMode(hydratedMode);
        }

        if (Number.isFinite(beatsPerMeasure) && beatsPerMeasure > 0) {
          setTimeSigNumerator(String(Math.round(beatsPerMeasure)));
        }
        setTimeSigDenominator("4");
        setInstrumentPreset("builtin:vocals-6");
      } catch (_error) {
        // Keep existing defaults if retrieval fails.
      }
    };

    hydrateFromFileDetails();
    return () => {
      cancelled = true;
    };
  }, [flowStep, isMusicXmlFlow, selectedFile, globalDirectory]);

  const handleSelect = (selected, setAttr) => {
    setAttr(selected.label);
  };

  const getSelectedPresetMap = () => {
    if (instrumentPreset.startsWith("builtin:")) {
      const builtinId = instrumentPreset.replace("builtin:", "");
      return builtinPresetColorClefMaps[builtinId] ?? {};
    }
    if (instrumentPreset.startsWith("custom:")) {
      const customId = instrumentPreset.replace("custom:", "");
      return userClefPresets[customId]?.color_clef_map ?? {};
    }
    return {};
  };

  const buildMusicXmlArgs = () => {
    if (!isCustomMusicXml) {
      return {
        time_sig_numerator: "auto",
        time_sig_denominator: "auto",
        tempo_bpm: "auto",
        key_signature: "auto",
        color_clef_map: {},
      };
    }

    return {
      time_sig_numerator: coerceNumberOrAuto(timeSigNumerator),
      time_sig_denominator: coerceNumberOrAuto(timeSigDenominator),
      tempo_bpm: coerceNumberOrAuto(tempoBpm),
      key_signature: `${keySignatureKey} ${keySignatureMode}`,
      color_clef_map: getSelectedPresetMap(),
    };
  };

  const saveNewPreset = async () => {
    const trimmedName = newPresetName.trim();
    if (!trimmedName) {
      setPresetError("Preset name is required.");
      return false;
    }
    const normalizedName = trimmedName.toLowerCase();
    const alreadyExists = Object.values(userClefPresets).some(
      (preset) => (preset?.name || "").trim().toLowerCase() === normalizedName,
    );
    if (alreadyExists) {
      setPresetError("A preset with this name already exists.");
      return false;
    }

    const newPresetId = `preset_${Date.now()}`;
    const updatedPresets = {
      ...userClefPresets,
      [newPresetId]: {
        name: trimmedName,
        color_clef_map: { ...newPresetMap },
      },
    };

    setUserClefPresets(updatedPresets);
    await window.electronAPI.updateUserSettings("clef_presets", updatedPresets);
    setInstrumentPreset(`custom:${newPresetId}`);
    setPresetError("");
    setShowPresetModal(false);
    return true;
  };

  const finish = async () => {
    document.body.style.cursor = "wait";
    try {
      const args = {
        dest_folder_path: selectedFolder.value,
        file_type: format.toLowerCase(),
      };

      if (isMusicXmlFlow) {
        Object.assign(args, buildMusicXmlArgs());
      }

      await window.electronAPI.doProcessCommand(
        path.join(globalDirectory, path.basename(selectedFile)),
        "convert",
        args,
      );
    } finally {
      document.body.style.cursor = "default";
    }
  };

  return (
    <>
      {showInitExportFolder ? (
        <>
          <InitExportFolder
            onComplete={() => {
              setShowInitExportFolder(false);
              onClose();
            }}
          />
        </>
      ) : (
        <>
          {flowStep === "select" ? (
            <>
              <div
                className="modal-title"

                style={{ marginBottom: "25px" }}
              >
                Convert to...
              </div>
              <div className="modal-body">Symphony Name</div>
              <div>
                <div
                  className="modal-file-explorer-button"
                  style={{ cursor: "not-allowed" }}
                >
                  <span
                    style={{
                      overflow: "hidden",
                      whiteSpace: "nowrap",
                      textOverflow: "ellipsis",
                      display: "inline-block",
                      flexGrow: 1,
                      minWidth: 0,
                    }}
                  >
                    {selectedFile?.slice(0, -9)}
                  </span>
                </div>
              </div>
              <div className="modal-body" style={{ marginTop: "2em" }}>
                Destination
              </div>
              <Dropdown
                options={folders}
                onSelect={(e) => handleSelect(e, setDestination)}
                value={selectedFolder}
              />
              <div className="modal-body" style={{ marginTop: "2em" }}>
                Format
              </div>
              <Dropdown
                options={formats}
                onSelect={(e) => {
                  handleSelect(e, setFormat);
                  if (e.label !== "MusicXML") {
                    setFlowStep("select");
                  }
                }}
                value={selectedFormat}
              />
            </>
          ) : (
            <div style={{ width: "470px" }}>
              <div
                className="modal-title"

                style={{ marginBottom: "8px" }}
              >
                Convert to MusicXML
              </div>
              <div className="modal-subtext" style={{ marginBottom: "22px", width: "auto" }}>
                Specify how your Symphony file gets converted to MusicXML.
              </div>

              <div className="modal-body">Conversion Method</div>
              <Dropdown
                options={conversionMethods}
                onSelect={(selected) => setConversionMethod(selected.value)}
                value={selectedMethod}
              />

              <div className="musicxml-config-panel">
                <div className="musicxml-grid">
                  <div>
                    <div className="modal-body">Tempo (BPM)</div>
                    <Field
                      value={tempoBpm}
                      onChange={(e) => setTempoBpm(e.target.value || "")}
                      singleLine={true}
                      width="100%"
                    />
                  </div>
                  <div>
                    <div className="modal-body">Key Signature</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", width: "250px", gap: "8px" }}>
                      <Dropdown
                        options={keyOptions}
                        onSelect={(selected) => setKeySignatureKey(selected.value)}
                        value={selectedKey}
                        style={{ display: "flex", width: "100%" }}
                      />
                      <Dropdown
                        options={modeOptions}
                        onSelect={(selected) => setKeySignatureMode(selected.value)}
                        value={selectedMode}
                        style={{ display: "flex", width: "100%" }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="modal-body">Dynamics</div>
                    <Dropdown
                      options={dynamicsOptions}
                      onSelect={(selected) => setDynamics(selected.value)}
                      value={selectedDynamics}
                    />
                  </div>
                  <div>
                    <div className="modal-body">Time Signature</div>
                    <div className="musicxml-timesig-row">
                      <div className="musicxml-timesig-stack">
                        <Field
                          value={timeSigNumerator}
                          onChange={(e) => setTimeSigNumerator(e.target.value || "")}
                          singleLine={true}
                          width="72px"
                          height="40px"
                          fontSize="28px"
                          className="musicxml-time-sig-field field"
                        />
                        <Field
                          value={timeSigDenominator}
                          onChange={(e) => setTimeSigDenominator(e.target.value || "")}
                          singleLine={true}
                          width="72px"
                          height="40px"
                          fontSize="28px"
                          className="musicxml-time-sig-field field"
                        />
                      </div>
                      <div className="musicxml-staff-lines">
                        <div />
                        <div />
                        <div />
                        <div />
                        <div />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="modal-body" style={{ marginTop: "18px" }}>
                  Instrument / Vocal Parts
                </div>
                <Dropdown
                  options={presetOptions}
                  onSelect={(selected) => {
                    if (selected.value === presetCreatorOption.value) {
                      setPresetError("");
                      setNewPresetName("");
                      setNewPresetMap({
                        orange: "Treble",
                        purple: "Treble",
                        cyan: "Treble",
                        lime: "Treble",
                        blue: "Treble",
                        pink: "Treble",
                      });
                      setShowPresetModal(true);
                      return;
                    }
                    setInstrumentPreset(selected.value);
                  }}
                  value={selectedPreset}
                />

                {!isCustomMusicXml ? (
                  <div className="musicxml-custom-overlay" aria-hidden="true" />
                ) : null}
              </div>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "22px" }}>
            <button
              className={canSubmit ? "call-to-action-2" : "call-to-action-2 locked"}

              onClick={
                !canSubmit
                  ? null
                  : async () => {
                    if (flowStep === "select" && isMusicXmlFlow) {
                      setFlowStep("musicxml");
                      return;
                    }

                    await finish();
                    setGlobalDirectory(selectedFolder.value);
                    setSelectedFile(null);
                    if (onComplete) onComplete();
                    onClose();
                  }
              }
            >
              {flowStep === "select" && isMusicXmlFlow
                ? "Next"
                : "Convert"}
            </button>
          </div>

          <GenericModal
            isOpen={showPresetModal}
            onClose={() => {
              setShowPresetModal(false);
              setPresetError("");
            }}
          >
            <div style={{ width: "470px" }}>
              <div
                className="modal-title"
                text-style="display"
                style={{ marginBottom: "8px" }}
              >
                Create New Instrument Preset
              </div>
              <div
                className="modal-subtext"
                style={{ marginBottom: "14px", width: "auto" }}
              >
                Specify how your Symphony file gets converted to MusicXML.
              </div>

              <div className="modal-body" style={{ marginTop: "20px" }}>
                Preset Name
              </div>
              <Field
                value={newPresetName}
                onChange={(e) => {
                  setNewPresetName(e.target.value || "");
                  if (presetError) setPresetError("");
                }}
                singleLine={true}
                width="100%"
                fontSize="13px"
                height="34px"
              />
              {presetError ? (
                <div
                  className="modal-subtext red"
                  style={{ marginTop: "6px", marginBottom: "6px", width: "auto" }}
                >
                  {presetError}
                </div>
              ) : null}

              <div className="musicxml-preset-scroll">
                {colorKeys.map((color) => {
                  const label = `Color Channel: ${color[0].toUpperCase()}${color.slice(1)}`;
                  const selectedClef =
                    clefOptions.find((opt) => opt.value === newPresetMap[color]) ||
                    clefOptions[0];
                  return (
                    <div key={color} style={{ marginBottom: "12px" }}>
                      <div className="modal-body" style={{ marginBottom: "5px" }}>
                        {label}
                      </div>
                      <Dropdown
                        options={clefOptions}
                        onSelect={(selected) =>
                          setNewPresetMap((prev) => ({
                            ...prev,
                            [color]: selected.value,
                          }))
                        }
                        value={selectedClef}
                      />
                    </div>
                  );
                })}
              </div>

              <div
                style={{ display: "flex", justifyContent: "flex-end", marginTop: "14px" }}
              >
                <button
                  className="call-to-action-2"
                  onClick={async () => {
                    await saveNewPreset();
                  }}
                >
                  Create Preset
                </button>
              </div>
            </div>
          </GenericModal>
        </>
      )}
    </>
  );
}

export default ConvertModal;
