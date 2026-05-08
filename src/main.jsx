import React from "react";
import ReactDOM from "react-dom/client";
import * as Neutralino from "@neutralinojs/lib";
import "./universal-styling/index.css";
import { symphonyAPI, initSymphonyApi } from "@/lib/symphonyApi";

// Attach the Neutralino-backed shim *before* the rest of the app's
// module graph evaluates. A handful of legacy modules historically
// called `window.electronAPI` at top-level — that worked in Electron
// because preload.js ran synchronously, but with our ESM bootstrap the
// assignment must happen before App's tree is imported.
window.electronAPI = symphonyAPI;

async function bootstrap() {
  try {
    Neutralino.init();
  } catch (err) {
    console.error("Neutralino.init failed:", err);
  }

  Neutralino.events.on("ready", () => {
    initSymphonyApi().catch((err) => {
      console.error("Failed to initialise Symphony API:", err);
    });
  });

  const [{ default: App }, { DirectoryProvider }] = await Promise.all([
    import("./App"),
    import("./contexts/DirectoryContext"),
  ]);

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(
    <React.StrictMode>
      <DirectoryProvider>
        <App />
      </DirectoryProvider>
    </React.StrictMode>,
  );
}

bootstrap().catch((err) => {
  console.error("Bootstrap failed:", err);
});
