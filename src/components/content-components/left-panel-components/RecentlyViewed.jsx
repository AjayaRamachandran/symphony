import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt } from 'lucide-react';

import Tooltip from '@/components/Tooltip';
import './recently-viewed.css';
import { useDirectory } from '@/contexts/DirectoryContext';
import FileNotExist from '@/modals/FileNotExist';
import GenericModal from '@/modals/GenericModal';

function RecentlyViewed() {
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [showFileNotExist, setShowFileNotExist] = useState(false);
  const [launchItemName, setLaunchItemName] = useState(null);
  const { setGlobalDirectory, setSelectedFile, globalUpdateTimestamp, setGlobalUpdateTimestamp } = useDirectory();
  const fileTypes = {
    'symphony': ChartNoAxesGantt,
    'mp3': Music,
  };

  const getItemName = () => {
    return launchItemName;
  };

  useEffect(() => {
    window.electronAPI.getRecentlyViewed().then((items) => {
      setRecentlyViewed(Array.isArray(items) ? items : []);
    }).catch(() => setRecentlyViewed([]));
  }, [globalUpdateTimestamp]);

  // Handle single and double click
  const handleClick = (item) => {
    if (item.fileLocation) {
      setGlobalDirectory(item.fileLocation);
      setSelectedFile(item.name);
    }
  };

  const handleDoubleClick = async (item) => {
    setLaunchItemName(item.name);
    try {
      setGlobalUpdateTimestamp(Date.now());
        const result = await window.electronAPI.runPythonScript([
          'open',
          item.name,
          item.fileLocation
        ]);
        console.log("Python script succeeded:", result.output);
      } catch (err) {
        console.error("Python script failed:", err.error || err);
        setShowFileNotExist(true);
        recentlyViewedDelete(item);
      }
  };

  const recentlyViewedDelete = (item) => {
    window.electronAPI.recentlyViewedDelete(item.name);
    setGlobalUpdateTimestamp(Date.now());
  }

  return (
    <>
      <div className="recently-viewed scrollable med-bg">
        {recentlyViewed.length > 0 && recentlyViewed.map((item, recentIndex) => {
          if (recentIndex < 12) {
            const Icon = fileTypes[item.type];
            return (
              <button
                className="recently-viewed-medium tooltip"
                key={recentIndex}
                onClick={() => handleClick(item)}
                onDoubleClick={async () => { await handleDoubleClick(item); }}
              >
                {Icon && (
                  <Icon style={{ flexShrink: 0 }} size={16} strokeWidth={1.5}
                    color-type={item.type === 'mp3' ? 'accent-color' : 'icon-color'} />
                )}
                <div className="truncated-text" style={{ marginLeft: '6px' }}>
                  {item.name}
                </div>
                <Tooltip text={item.name} />
              </button>
            );
          }
        })}
      </div>
      <GenericModal isOpen={showFileNotExist} onClose={() => { setShowFileNotExist(false) }} showXButton={false}>
        <FileNotExist onComplete={() => { setShowFileNotExist(false); }} fileName={getItemName} />
      </GenericModal>
    </>
  );
}

export default RecentlyViewed;