import "./editor-bridge.js";
import React from "react";
import ReactDOM from "react-dom/client";
import EditorApp from "./components/app.jsx";
import "@/universal-styling/index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <EditorApp />
  </React.StrictMode>,
);
