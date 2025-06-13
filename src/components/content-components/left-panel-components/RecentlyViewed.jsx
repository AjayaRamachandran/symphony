import React, { useState, useEffect } from 'react';
import { Music, ChartNoAxesGantt } from 'lucide-react';
import recentlyViewed from '@/assets/recentlyViewed.json';

import './recently-viewed.css'

function RecentlyViewed() {
  const fileTypes = {
    'mgrid' : ChartNoAxesGantt,
    'mp3' : Music,
  };

  return (
    <div className="recently-viewed">
      {recentlyViewed.map((recent, recentIndex) => {
        const item = recentlyViewed[recentIndex];
        const Icon = fileTypes[item.type];

        return (
          <div className="recently-viewed-medium" key={recentIndex}>
            {Icon && (
              <Icon style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} color="#606060" />
            )}
            <div className="truncated-text" style={{ marginLeft: '6px' }}>
              {item.name}
            </div>
          </div>
        );
      })}
    </div>
  )};

export default RecentlyViewed;