import React, { createContext, useContext, useState } from "react";

const DirectoryContext = createContext();

export function DirectoryProvider({ children }) {
  const [globalDirectory, setGlobalDirectory] = useState(null);

  return (
    <DirectoryContext.Provider value={{ globalDirectory, setGlobalDirectory }}>
      {children}
    </DirectoryContext.Provider>
  );
}

export function useDirectory() {
  return useContext(DirectoryContext);
}