import React, { createContext, useContext, useState } from "react";

const DirectoryContext = createContext();

export function DirectoryProvider({ children }) {
  const [globalDirectory, setGlobalDirectory] = useState(null);
  const [globalUpdateTimestamp, setGlobalUpdateTimestamp] = useState(Date.now());
  const [selectedFile, setSelectedFile] = useState(null);
  const [viewType, setViewType] = useState('grid');

  return (
    <DirectoryContext.Provider value={{
      globalDirectory,
      setGlobalDirectory,
      globalUpdateTimestamp,
      setGlobalUpdateTimestamp,
      selectedFile,
      setSelectedFile,
      viewType,
      setViewType
    }}>
      {children}
    </DirectoryContext.Provider>
  );
}

export function useDirectory() {
  return useContext(DirectoryContext);
}