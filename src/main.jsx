import "./electron-api-shim";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./app";
import "@/universal-styling/index.css";
import { DirectoryProvider } from "@/contexts/directory-context";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <DirectoryProvider>
      <App />
    </DirectoryProvider>
  </React.StrictMode>,
);
