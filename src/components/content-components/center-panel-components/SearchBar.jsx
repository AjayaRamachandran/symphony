import React, { useState, useEffect, useRef } from "react";
import { Search } from "lucide-react";
import path from "path-browserify";

import Field from "../../../ui/Field";
import SearchResults from "./SearchResults";

import "./search-bar.css";

function SearchBar() {
  const [searchContent, setSearchContent] = useState("");
  const [lastSearchContent, setLastSearchContent] = useState("");
  const [focused, setFocused] = useState(false);
  const [searchResults, setSearchResults] = useState([]);

  // Wrapper ref for BOTH input and results
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setFocused(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const doSearch = async () => {
    setLastSearchContent(searchContent);

    if (searchContent === "") {
      setSearchResults([]);
      return;
    }

    const directories = ["Projects", "Exports", "Symphony Auto-Save"];
    const directoryMap = await window.electronAPI.getDirectory();

    const results = [];

    for (const dirName of directories) {
      const dirEntries = directoryMap[dirName] || [];

      for (const nameDirPair of dirEntries) {
        const dir = Object.values(nameDirPair)[0];
        const listOfFiles = await window.electronAPI.getSymphonyFiles(dir);

        listOfFiles.forEach((el) => {
          if (
            el.toLowerCase().includes(searchContent.toLowerCase()) &&
            results.length < 5
          ) {
            results.push({
              el,
              fullPath: path.join(dir, el),
            });
          }
        });
      }
    }

    setSearchResults(results);
  };

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchContent !== lastSearchContent) {
        doSearch();
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchContent]);

  useEffect(() => {
    const handleFocusSearch = () => {
      setFocused(true);
      const input = wrapperRef.current?.querySelector("input");
      input?.focus();
    };

    window.addEventListener("symphony:focus-search", handleFocusSearch);
    return () => {
      window.removeEventListener("symphony:focus-search", handleFocusSearch);
    };
  }, []);

  const getSearchResults = () => searchResults;
  const getSearchTerm = () => lastSearchContent;
  const getFocused = () => focused;

  return (
    <div ref={wrapperRef}>
      <div style={{ display: "flex", position: "relative" }}>
        <Field
          value={searchContent}
          className="search-field"
          placeholder={<span style={{ display: "flex", flexDirection: "row", alignItems: "center" }}>
            Search All Files <div style={{ fontSize: "10px", color: "#888", backgroundColor: "#fff1", padding: "2px 4px", borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", marginLeft: "7px" }}>
              {navigator.platform && navigator.platform.startsWith("Mac") ? (
                "⌘ + K"
              ) : (
                "Ctrl + K"
              )}
            </div>
          </span>}
          style={{ height: "31px", fontSize: "1.1em", width: "100%", paddingLeft: "32px", boxShadow: "none !important" }}
          onChange={(e) => setSearchContent(e.target.value)}
          onFocus={() => setFocused(true)}
          singleLine={true}
        />
        <Search className="field-search-icon" size={15} />
      </div>

      <div className={`search-results-container ${focused ? "focused" : ""}`}>
        <SearchResults
          getSearchResults={getSearchResults}
          getSearchTerm={getSearchTerm}
          getFocused={getFocused}
          onClose={() => setFocused(false)}
        />
      </div>
    </div>
  );
}

export default SearchBar;
