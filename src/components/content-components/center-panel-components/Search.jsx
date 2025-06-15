import React, { useState, useEffect } from 'react';

import Field from '.././right-panel-components/Field'

import "./search.css";

function Search() {

  return (
    <>
      <Field defaultText='Search All Files' className='search-field' height="31px" fontSize='1.1em' lightDark={[]}/>
    </>
  );
}

export default Search;