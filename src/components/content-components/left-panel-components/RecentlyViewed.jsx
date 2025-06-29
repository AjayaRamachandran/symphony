import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt } from 'lucide-react';
import recentlyViewed from '@/assets/recently-viewed.json';

import './recently-viewed.css'
import Tooltip from '@/components/Tooltip';

function RecentlyViewed() {
  const fileTypes = {
    'symphony' : ChartNoAxesGantt,
    'mp3' : Music,
  };

  return (
    <div className="recently-viewed">
      {recentlyViewed.map((recent, recentIndex) => {
        const item = recentlyViewed[recentIndex];
        const Icon = fileTypes[item.type];

        return (
          <button className="recently-viewed-medium tooltip" key={recentIndex}>
            {Icon && (
              <Icon style={{ flexShrink: 0 }} size={16} strokeWidth={1.5}
              color-type ={item.type == 'mp3' ? "accent-color" : "icon-color"}/>
            )}
            <div className="truncated-text" style={{ marginLeft: '6px' }}>
              {item.name}
            </div>
            <Tooltip text={item.name} />
          </button>
        );
      })}
    </div>
  )};

export default RecentlyViewed;