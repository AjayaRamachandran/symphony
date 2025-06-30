import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt } from 'lucide-react';
import Tooltip from '@/components/Tooltip';
import './recently-viewed.css';

function RecentlyViewed() {
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const fileTypes = {
    'symphony': ChartNoAxesGantt,
    'mp3': Music,
  };

  useEffect(() => {
    // Use Electron preload API to get or create the file
    if (window.electronAPI && window.electronAPI.getRecentlyViewed) {
      window.electronAPI.getRecentlyViewed().then((items) => {
        setRecentlyViewed(Array.isArray(items) ? items : []);
      }).catch(() => setRecentlyViewed([]));
    } else {
      setRecentlyViewed([]); // fallback for non-Electron
    }
  }, []);

  return (
    <div className="recently-viewed">
      {recentlyViewed.length > 0 && recentlyViewed.map((item, recentIndex) => {
        const Icon = fileTypes[item.type];
        return (
          <button className="recently-viewed-medium tooltip" key={recentIndex}>
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