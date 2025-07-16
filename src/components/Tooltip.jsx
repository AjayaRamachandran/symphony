import React, { useState, useEffect } from 'react';

function Tooltip({text = "", altText="", positionOverride=null}) {

  return (
    <>
      <span className="tooltip-text" style={positionOverride? {transform: 'translate('+positionOverride[0] +', '+ positionOverride[1]+')'} : {}}>
        <span className="tooltip-inner-1">{text}</span>
        {altText && (<span className="tooltip-inner-alt">{altText}</span>)}
      </span>
    </>
  );
}

export default Tooltip;
