import React, { createContext, useContext, useState } from "react";

const DirectoryContext = createContext();

export function DirectoryProvider({ children }) {
  const [globalDirectory, setGlobalDirectory] = useState(null);
  const [globalUpdateTimestamp, setGlobalUpdateTimestamp] = useState(Date.now());
  const [selectedFile, setSelectedFile] = useState(null);
  const [viewType, setViewType] = useState('grid');
  const [clipboardFile, setClipboardFile] = useState(null);
  const [clipboardCut, setClipboardCut] = useState(false);
  const [isFieldSelected, setIsFieldSelected] = useState(false); // Add field selection state
  const [tempFileName, setTempFileName] = useState(""); // Add temp file name for editing
  const [globalStars, setGlobalStars] = useState([]);
  const [showSplashScreen, setShowSplashScreen] = useState(true);

  return (
    <DirectoryContext.Provider value={{
      globalDirectory,
      setGlobalDirectory,
      globalUpdateTimestamp,
      setGlobalUpdateTimestamp,
      selectedFile,
      setSelectedFile,
      viewType,
      setViewType,
      clipboardFile,
      setClipboardFile,
      clipboardCut,
      setClipboardCut,
      isFieldSelected,
      setIsFieldSelected,
      tempFileName,
      setTempFileName,
      globalStars,
      setGlobalStars,
      showSplashScreen,
      setShowSplashScreen
    }}>
      {children}
    </DirectoryContext.Provider>
  );
}

export function useDirectory() {
  return useContext(DirectoryContext);
}