import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt, FolderClosed, BookMarked, GitBranch, Play } from 'lucide-react';
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
      <div className='banner'><img src={banner} style={{ width: '500px', display: 'block' }}></img></div>
      <div style={{padding: '30px', borderTop: '1px solid #3c3c3c'}}>
        <div className='modal-big-title' text-style='display' style={{margin : '0px 0px', fontSize: '28px'}}>Hi {userFirstName.split(' ')[0]}!</div>
        <div className='modal-paragraph' text-style='display' style={{fontSize: '14px', marginBottom: '8px', marginTop: '8px'}}>Let's create something amazing.</div>
        {recentlyViewed.length > 0 && <>
          <div className="quick-launch scrollable med-bg">
            {recentlyViewed.map((item, recentIndex) => {
              if (recentIndex < 3) {
                const Icon = fileTypes[item.type];
                return (
                  <button
                    className="quick-launch-medium tooltip"
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
        </>}
        <div className='modal-body' text-style='display' style={{fontSize: '18px', marginBottom: '8px', marginTop: '15px'}}>Resources</div>
        <div className="quick-launch scrollable med-bg">
          <button className="quick-launch-medium tooltip" onClick={() => handleClick(item)}>
            <BookMarked style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: '6px' }}>
              Learn how to use Symphony <span style={{opacity: '0.5', fontStyle: 'italic'}}>(recommended)</span>
            </div>
          </button>
          <button className="quick-launch-medium tooltip" onClick={() => handleClick(item)}>
            <GitBranch style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: '6px' }}>
              See the latest Release Notes
            </div>
          </button>
          <button className="quick-launch-medium tooltip" onClick={() => handleClick(item)}>
            <Play style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: '6px' }}>
              Watch the launch video
            </div>
          </button>
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between', height: 'min-content', alignItems: 'flex-end'}}>
          <button style={{opacity: '0.7'}}><i>Don't show this screen on startup</i></button>
          <button className='call-to-action-2' text-style='display' onClick={() => onComplete()}>Close</button>
        </div>
        
      </div>
    </>
  );
}

export default SplashScreen;