import React, { useState, useEffect } from "react";

import LeftPanel from "@/components/content-components/left-panel";
import CenterPanel from "@/components/content-components/center-panel";
import RightPanel from "@/components/content-components/right-panel";

import GenericModal from "@/modals/generic-modal";
import OnboardingModal from "@/modals/onboarding-modal";
import { useDirectory } from "@/contexts/directory-context";

import "@/universal-styling/content.css";

function Content() {
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const { selectedFile, globalDirectory } = useDirectory();
  const rightPanelKey = `${globalDirectory || ""}::${selectedFile || ""}`;
  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setNeedsOnboarding(result["needs_onboarding"]);
      setShowOnboardingModal(result["needs_onboarding"]);
    });
  }, []);

  return (
    <>
      {showOnboardingModal ? (
        <></>
      ) : (
        <>
          <div className="content">
            <LeftPanel />
            <CenterPanel />
            <RightPanel key={rightPanelKey} />
          </div>
        </>
      )}
      <GenericModal
        isOpen={showOnboardingModal}
        onClose={() => {
          setShowOnboardingModal(false);
        }}
        showXButton={false}
        custom={"onboarding"}
      >
        <OnboardingModal
          onComplete={() => {
            setShowOnboardingModal(false);
          }}
        />
      </GenericModal>
    </>
  );
}

export default Content;
