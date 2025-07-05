import React, { useState, useEffect } from 'react';

function Tooltip({text = "", positionOverride=null}) {

  return (
    <>
      <span className="tooltip-text" style={positionOverride? {transform: 'translate('+positionOverride[0] +', '+ positionOverride[1]+')'} : {}}>{text}</span>
    </>
  );
}

export default Tooltip;
