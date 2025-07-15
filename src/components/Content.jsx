import React, { useState, useEffect } from 'react';

import LeftPanel from "./content-components/LeftPanel";
import CenterPanel from "./content-components/CenterPanel";
import RightPanel from "./content-components/RightPanel";

import GenericModal from '@/modals/GenericModal';
import OnboardingModal from '@/modals/OnboardingModal';

import "./content.css"

function Content() {
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  useState(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setNeedsOnboarding(result['needs_onboarding']);
      setShowOnboardingModal(result['needs_onboarding'])
    })
  }, [])

  return (
    <>
      {showOnboardingModal ? (<></>) : (<>
        <div className='content'>
          <LeftPanel />
          <CenterPanel />
          <RightPanel />
        </div>
      </>)}
      <GenericModal isOpen={showOnboardingModal} onClose={() => { setShowOnboardingModal(false) }} showXButton={false} custom={'onboarding'}>
        <OnboardingModal onComplete={() => { setShowOnboardingModal(false); }} />
      </GenericModal>
    </>
  );
}

export default Content;
