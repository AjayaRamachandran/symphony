import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

import Field from '../right-panel-components/Field'

import "./search-bar.css";

function SearchBar() {

  return (
    <>
      <Field defaultText='Search All Files' className='search-field' height="31px" fontSize='1.1em' lightDark={[]} searchField={true} />
    </>
  );
}

export default SearchBar;