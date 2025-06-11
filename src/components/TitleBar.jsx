import React, { useState, useEffect } from 'react';
import { Square, Copy } from 'lucide-react';

function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    // Listen for maximize/unmaximize from backend
    window.electronAPI.onWindowStateChange(setIsMaximized);
  }, []);

  return (
    <>
      <div className="titlebar">
        <div>Project Manager - Symphony v1.0 Beta</div>
        <div className="window-controls">
          <button className="bi bi-dash-lg" topBarButtons='true'
            onClick={() => window.electronAPI.minimize()}>
          </button>
          <button topBarButtons='true'
            onClick={() => window.electronAPI.maximize()}>
          {
            isMaximized ?
            <Copy size={12} style={{ transform: 'rotate(90deg)' }}/>
            : <Square size={11} />
          }
          </button>
          <button className="bi bi-x-lg x-button" topBarButtons='true'
            onClick={() => window.electronAPI.close()}>
          </button>
        </div>
      </div>
    </>
  );
}

export default TitleBar;
