import React, { useState, useRef, useEffect } from "react";

import { ChevronDown, ChevronUp } from "lucide-react";
import "./dropdown.css/";

const Dropdown = ({
  options,
  onSelect,
  value,
  placeholder = "Select an option",
}) => {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const dropdownRef = useRef(null);

  // Sync selected with value prop
  useEffect(() => {
    if (value) {
      setSelected(value);
    } else {
      setSelected(null);
    }
  }, [value]);

  const handleOnSelect = (option) => {
    setSelected(option);
    setOpen(false);
    onSelect && onSelect(option);
  };

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="dropdown" ref={dropdownRef}>
      <button className="dropdown-toggle" onClick={() => setOpen(!open)}>
        <span className="truncate">
          {selected ? selected.label : placeholder}
        </span>
        <span className="chevron">
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>
      {open && (
        <ul className="dropdown-menu">
          {options.map((opt, i) => (
            <li
              key={i}
              className="dropdown-item"
              onClick={() => handleOnSelect(opt)}
            >
              {opt.icon && (
                <span className="icon">{<opt.icon size={16} />}</span>
              )}
              <span className="truncate">{opt.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Dropdown;
