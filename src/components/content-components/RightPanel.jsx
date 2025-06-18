import React, { useState, useEffect } from 'react';
import { PencilRuler, ArrowRight } from 'lucide-react';

import Field from "./right-panel-components/Field";

import "./right-panel.css";

function RightPanel() {
  const [hovered, setHovered] = useState(false);

  return (
    <>
      <div className="content-panel-container">
        <div>
          <div className='med-title' text-style='display'>
            Details
          </div>
          <div className='field-label'>Title</div>
          <Field initialValue="" height = '33px' />

          <div className='field-label'>Description</div>
          <Field initialValue="" height='120px' fontSize='1.2em'/>

          <div className='field-label'>Composer / Arr.</div>
          <Field initialValue="" height='70px' fontSize='1.2em'/>

          <div className='field-label'>Collaborators</div>
          <Field initialValue="" height='70px' fontSize='1.2em'/>

          <div className='field-label'>File Location</div>
          <Field initialValue="" height = '32px' fontSize='1.2em' whiteSpace='nowrap'/>
        </div>
      
        <button
          className='call-to-action'
          text-style='display'
          style={{transition: 'filter 0.2s'}}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}>
          <div>Open in Editor</div>
          <PencilRuler size={16} strokeWidth={2.5} />
        </button>
      </div>
    </>
  );
}

export default RightPanel;