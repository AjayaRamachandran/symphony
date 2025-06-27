import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./universal-styling/index.css";
import { DirectoryProvider } from "./contexts/DirectoryContext";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <DirectoryProvider>
      <App />
    </DirectoryProvider>
  </React.StrictMode>
);