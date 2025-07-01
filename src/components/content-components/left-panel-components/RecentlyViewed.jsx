import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt } from 'lucide-react';
import Tooltip from '@/components/Tooltip';
import './recently-viewed.css';
import { useDirectory } from '@/contexts/DirectoryContext';

function RecentlyViewed() {
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const { setGlobalDirectory, setSelectedFile, globalUpdateTimestamp } = useDirectory();
  const fileTypes = {
    'symphony': ChartNoAxesGantt,
    'mp3': Music,
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

  const handleDoubleClick = (item) => {
    window.electronAPI.runPythonScript([item.type, item.name, item.fileLocation]);
  };

  return (
    <div className="recently-viewed">
      {recentlyViewed.length > 0 && recentlyViewed.map((item, recentIndex) => {
        const Icon = fileTypes[item.type];
        return (
          <button
            className="recently-viewed-medium tooltip"
            key={recentIndex}
            onClick={() => handleClick(item)}
            onDoubleClick={() => handleDoubleClick(item)}
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
      })}
    </div>
  );
}

export default RecentlyViewed;