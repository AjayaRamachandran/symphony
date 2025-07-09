import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

import Field from '../right-panel-components/Field'
import SearchResults from './SearchResults';

import "./search-bar.css";

function SearchBar() {
  const [ searchContent, setSearchContent ] = useState('');
  const [ focused, setFocused ] = useState(false);
  const [ searchResults, setSearchResults ] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    // window.electronAPI.searchAllFiles(searchTerm);
  }, [focused])

  const getSearchTerm = () => {
    return searchContent;
  }

  const getFocused = () => {
    return focused;
  }

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && focused) {
        setFocused(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [focused]);

  return (
    <>
      <Field
        value={searchContent || ''}
        className='search-field'
        defaultText='Search All Files'
        height='31px'
        fontSize='1.1em'
        lightDark={[]}
        searchField={true}
        onChange={e => setSearchContent(e.target.value)}
        onFocus={() => setFocused(true)}
        singleLine={true}
        //onBlur={() => setFocused(false)}
      />
      <SearchResults searchResults={searchResults} getSearchTerm={getSearchTerm} getFocused={getFocused} onClose={() => setFocused(false)}/>
    </>
  );
}

export default SearchBar;