const HANDLER_GROUPS = [
  {
    title: "Window",
    handlers: ["getPlatform", "minimize", "maximize", "close", "toggleDevTools", "openExternalUrl"],
  },
  {
    title: "Document",
    handlers: ["getDocumentState", "saveNow"],
  },
  {
    title: "Note edits",
    handlers: [
      "drawNote",
      "eraseNoteAt",
      "setSelection",
      "clearSelection",
      "deleteSelectedNotes",
    ],
  },
  {
    title: "Metadata / settings",
    handlers: [
      "setAccidentals",
      "setBeatLength",
      "setBeatsPerMeasure",
      "setTempo",
      "setKey",
      "setMode",
      "setActiveColor",
      "setWaveType",
      "updateProjectMetadata",
    ],
  },
  {
    title: "Audio",
    handlers: ["playNotePreview", "playPitch", "playFull", "stopPlayback", "setPlayheadHome"],
  },
  {
    title: "Transactions",
    handlers: ["undo", "redo"],
  },
  {
    title: "Temp drag list",
    handlers: [
      "beginTempNotes",
      "appendTempNotes",
      "setTempNotes",
      "commitTempNotes",
      "cancelTempNotes",
    ],
  },
];

export default function ApiInspector({ bridgeReady, docState, error }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        padding: 24,
        color: "var(--foreground)",
        fontFamily: "Inter, sans-serif",
        overflow: "auto",
      }}
    >
      <h1
        className="display"
        style={{
          fontFamily: "Instrument Sans, sans-serif",
          fontSize: 28,
          margin: 0,
        }}
      >
        Editor API Inspector
      </h1>
      <div
        style={{
          alignSelf: "flex-start",
          border: "1px solid var(--border-color)",
          borderRadius: 999,
          color: "var(--tinted-foreground)",
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          padding: "4px 8px",
          textTransform: "uppercase",
        }}
      >
        Temporary test view
      </div>
      <p style={{ color: "var(--muted-foreground)", margin: 0 }}>
        This page is only a test surface for peering into the editor API. Press
        <code style={{ margin: "0 4px" }}>Alt/Option + I</code>
        to toggle between this inspector and the placeholder editor content.
      </p>

      <section>
        <h2 style={{ fontSize: 14, margin: "0 0 8px 0" }}>Bridge status</h2>
        <div style={{ fontSize: 12 }}>
          {error ? (
            <span style={{ color: "var(--inactive-bad)" }}>{error}</span>
          ) : bridgeReady ? (
            <span style={{ color: "var(--active-good)" }}>connected</span>
          ) : (
            <span style={{ color: "var(--muted-foreground)" }}>connecting...</span>
          )}
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: 14, margin: "0 0 8px 0" }}>Document snapshot</h2>
        <pre
          style={{
            margin: 0,
            padding: 12,
            background: "var(--alternate-background)",
            border: "1px solid var(--border-color)",
            borderRadius: 6,
            maxHeight: 220,
            overflow: "auto",
            fontSize: 11,
          }}
        >
          {docState ? JSON.stringify(docState, null, 2) : "(no state)"}
        </pre>
      </section>

      <section>
        <h2 style={{ fontSize: 14, margin: "0 0 8px 0" }}>Available handlers</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {HANDLER_GROUPS.map((group) => (
            <div
              key={group.title}
              style={{
                border: "1px solid var(--border-color)",
                borderRadius: 6,
                padding: 12,
                background: "var(--alternate-background)",
              }}
            >
              <div
                style={{
                  fontFamily: "Instrument Sans, sans-serif",
                  fontSize: 12,
                  marginBottom: 6,
                  color: "var(--tinted-foreground)",
                }}
              >
                {group.title}
              </div>
              <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11 }}>
                {group.handlers.map((name) => (
                  <li key={name}>
                    <code>editorAPI.{name}</code>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
