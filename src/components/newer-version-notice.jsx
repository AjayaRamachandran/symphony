import React, { useEffect, useState } from "react";

import GenericModal from "@/modals/generic-modal";
import NewerVersionFile from "@/modals/newer-version-file";
import ProgramData from "@/assets/program-data.json";
import { NEWER_VERSION_EVENT } from "@/utils/open-in-editor";

// App-wide notice shown when a file opened from the Project Manager was made
// in a newer version of Symphony. Triggered by openInEditor().
function NewerVersionNotice() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handler = () => setIsOpen(true);
    window.addEventListener(NEWER_VERSION_EVENT, handler);
    return () => window.removeEventListener(NEWER_VERSION_EVENT, handler);
  }, []);

  return (
    <GenericModal
      isOpen={isOpen}
      onClose={() => setIsOpen(false)}
      showXButton={false}
    >
      <NewerVersionFile
        onComplete={() => {
          setIsOpen(false);
          window.electronAPI.openExternal(`${ProgramData.website}/download`);
        }}
        onClose={() => setIsOpen(false)}
      />
    </GenericModal>
  );
}

export default NewerVersionNotice;
