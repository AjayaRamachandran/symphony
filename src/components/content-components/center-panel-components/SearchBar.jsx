import React, { useState, useEffect, useRef } from "react";
import { Search } from "lucide-react";
import path from "path-browserify";

import Field from "../right-panel-components/Field";
import SearchResults from "./SearchResults";

import "./search-bar.css";

function SearchBar() {
  const [searchContent, setSearchContent] = useState("");
  const [lastSearchContent, setLastSearchContent] = useState("");
  const [focused, setFocused] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    // window.electronAPI.searchAllFiles(searchTerm);
  }, [focused]);

  const doSearch = async () => {
    setLastSearchContent(searchContent);
    if (searchContent === "") {
      setSearchResults([]);
      return;
    }
    const directories = ["Projects", "Exports", "Symphony Auto-Save"];

    const directoryMap = await window.electronAPI.getDirectory();
    //console.log(directoryMap);

    const results = [];
    console.log(searchContent);

    for (const dirName of directories) {
      const dirEntries = directoryMap[dirName];
      for (const nameDirPair of dirEntries) {
        const dir = Object.entries(nameDirPair)[0][1];
        const listOfFiles = await window.electronAPI.getSymphonyFiles(dir);
        listOfFiles.forEach((el) => {
          if (
            el.toLowerCase().includes(searchContent.toLowerCase()) &&
            results.length < 5
          ) {
            results.push({ el, fullPath: path.join(dir, el) });
            console.log({ el, fullPath: path.join(dir, el) });
          }
        });
      }
    }
    setSearchResults(results);
  };

  const getSearchResults = () => {
    return searchResults;
  };

  const getSearchTerm = () => {
    return lastSearchContent;
  };

  const getFocused = () => {
    return focused;
  };

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchContent !== lastSearchContent) {
        doSearch();
      }
    }, 300);

    return () => {
      clearTimeout(debounceTimer);
    };
  }, [searchContent]);

  return (
    <>
      <Field
        value={searchContent || ""}
        className="search-field"
        defaultText="Search All Files"
        height="31px"
        fontSize="1.1em"
        lightDark={[]}
        searchField={true}
        onChange={(e) => {
          setSearchContent(e.target.value);
          console.log(e.target.value);
        }}
        onFocus={() => setFocused(true)}
        singleLine={true}
        isControlled={true}
        width={"100%"}
        //onBlur={() => setFocused(false)}
      />
      <SearchResults
        getSearchResults={getSearchResults}
        getSearchTerm={getSearchTerm}
        getFocused={getFocused}
        onClose={() => setFocused(false)}
      />
    </>
  );
}

export default SearchBar;
