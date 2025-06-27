import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

import "./files.css";
import NewFile from './files-components/NewFile';

function Files() {

  return (
    <>
      <div className='files'>
        <NewFile />
      </div>
    </>
  );
}

export default Files;