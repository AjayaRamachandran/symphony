import React, { useState, useEffect } from 'react';
import { Square, Copy } from 'lucide-react';
import Icon from '@/assets/icon-dark.svg';

function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    // Listen for maximize/unmaximize from backend
    window.electronAPI.onWindowStateChange(setIsMaximized);
  }, []);

  return (
    <>
      <div className="titlebar">
        <div style={{display: 'flex', flexDirection: 'row', alignItems:'center', gap:'7px'}}>
          <img src={Icon} width='16px'></img>
          <div>Project Manager - Symphony v1.0 Beta</div>
        </div>
        <div className="window-controls">
          <button className="bi bi-dash-lg" topbar-buttons='true'
            onClick={() => window.electronAPI.minimize()}>
          </button>
          <button topbar-buttons='true'
            onClick={() => window.electronAPI.maximize()}>
          {
            isMaximized ?
            <Copy size={12} style={{ transform: 'rotate(90deg)' }}/>
            : <Square size={11} />
          }
          </button>
          <button className="bi bi-x-lg x-button" topbar-buttons='true'
            onClick={() => window.electronAPI.close()}>
          </button>
        </div>
      </div>
    </>
  );
}

export default TitleBar;
