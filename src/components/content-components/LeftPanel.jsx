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
  const {setSelectedFile, selectedFile} = useDirectory();
  const [userFirstName, setUserFirstName] = useState('');

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setUserFirstName(result['user_name'] || null)
    })
  }, [showUserSettings]);

  return (
    <>
      <div className="content-panel-container" style={{paddingTop: '15px'}}>
        <div className='section-title' style={{fontSize:'15px', margin: '3px 3px 3px 5px', height: '15px', letterSpacing: '0.5px'}}>{userFirstName ? userFirstName.split(' ')[0].slice(0, 15) + "'s" : ''}</div>
        <div className='title-row'>
          <div className={'big-title'} text-style='display'>
            Home
          </div>
          <button className='settings-button tooltip rotate' onClick={() => {setShowUserSettings(true); setSelectedFile(null)}}><Tooltip text="User Settings"/><Settings className='rotated'/></button>
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
        <UserSettings onComplete={() => { setShowUserSettings(false); }} />
      </GenericModal>
    </>
  );
}

export default LeftPanel;