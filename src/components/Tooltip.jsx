import React, { useState, useEffect } from 'react';

function Tooltip({text = ""}) {

  return (
    <>
      <span className="tooltip-text">{text}</span>
    </>
  );
}

export default Tooltip;
