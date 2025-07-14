import React, { useState, useEffect } from 'react';
import { Settings } from 'lucide-react';
import Directory from './left-panel-components/Directory';
import RecentlyViewed from './left-panel-components/RecentlyViewed';

import GenericModal from '@/modals/GenericModal';
import UserSettings from '@/modals/UserSettings';

import "./left-panel.css";
import Tooltip from '@/components/Tooltip';
import { useDirectory } from '@/contexts/DirectoryContext';

function LeftPanel() {
  const [showUserSettings, setShowUserSettings] = useState(false);
  const {setSelectedFile} = useDirectory();

  return (
    <>
      <div className="content-panel-container">
        <div className='title-row'>
          <div className='big-title' text-style='display'>
            Home
          </div>
          <button className='settings-button tooltip' onClick={() => {setShowUserSettings(true); setSelectedFile(null)}}><Tooltip text="User Settings"/><Settings /></button>
        </div>
        <div className='section-title'>
          DIRECTORY
        </div>
        <Directory />
        <div className='section-title'>
          RECENTLY LAUNCHED
        </div>
        <RecentlyViewed />
      </div>
      <GenericModal isOpen={showUserSettings} onClose={() => { setShowUserSettings(false) }} showXButton={false}>
        <UserSettings onComplete={() => { setShowUserSettings(false); }} fileName={undefined} />
      </GenericModal>
    </>
  );
}

export default LeftPanel;