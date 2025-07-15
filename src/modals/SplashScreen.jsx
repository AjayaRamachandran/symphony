import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt, FolderClosed } from 'lucide-react';
import Tooltip from '@/components/Tooltip';
import '@/components/content-components/left-panel-components/recently-viewed.css'

import banner from '@/assets/banner.svg'
import { useDirectory } from '@/contexts/DirectoryContext';

function SplashScreen({onComplete}) {
  const [userName, setUserName] = useState('');
  const [page, setPage] = useState(0);
  const [userFirstName, setUserFirstName] = useState('');
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const {globalUpdateTimestamp} = useDirectory();

  const fileTypes = {
    'symphony': ChartNoAxesGantt,
    'mp3': Music,
    'wav': Music,
    '' : FolderClosed,
  };

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setUserFirstName(result['user_name'] || null)
    })
  }, []);

  useEffect(() => {
    window.electronAPI.getRecentlyViewed().then((items) => {
      setRecentlyViewed(Array.isArray(items) ? items : []);
    }).catch(() => setRecentlyViewed([]));
  }, [globalUpdateTimestamp]);


  return (
    <>
      <div className='banner'><img src={banner}></img></div>
      <div style={{padding: '40px'}}>
        <div className='modal-big-title' text-style='display' style={{margin : '0px 0px', width: '500px', fontSize: '32px'}}>Hi {userFirstName.split(' ')[0]}!</div>
        <div className='modal-big-body' text-style='display' style={{fontSize: '18px', marginBottom: '8px', marginTop: '15px'}}>Jump back in</div>
        <div className="recently-viewed scrollable med-bg">
          {recentlyViewed.length > 0 && recentlyViewed.map((item, recentIndex) => {
            if (recentIndex < 3) {
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
                      color-type={item.type === 'mp3' || item.type === 'wav' ? 'accent-color' : item.type === 'symphony' ? 'accent-color-2' : 'icon-color'} />
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
        <div className='modal-body' text-style='display' style={{fontSize: '16px', marginBottom: '8px', marginTop: '15px'}}>View the latest <u>Release Notes</u></div>
      </div>
    </>
  );
}

export default SplashScreen;