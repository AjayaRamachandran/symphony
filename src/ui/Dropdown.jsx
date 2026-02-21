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

  const isPlainOptionObject = (option) =>
    option && typeof option === "object" && !React.isValidElement(option);
  const getMenuOptionContent = (option) => {
    if (isPlainOptionObject(option)) return option?.node ?? option?.label;
    return option;
  };
  const getSelectedContent = (option) =>
    isPlainOptionObject(option)
      ? option?.selectedNode ?? option?.selectedLabel ?? option?.label
      : option;

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
        {typeof (selected ? getSelectedContent(selected) : placeholder) === "string" ? (
          <span className="truncate">
            {selected ? getSelectedContent(selected) : placeholder}
          </span>
        ) : (
          selected ? getSelectedContent(selected) : placeholder
        )}
        <span className="chevron">
          <ChevronUp size={16} className="chevron-arrow" style={!open ? { rotate: "-180deg" } : {}} />
        </span>
      </button>
      <ul className={`dropdown-menu ${open ? "open" : ""}`}>
          {options.map((opt, i) => (
            <li
              key={i}
              className="dropdown-item"
              onClick={() => handleOnSelect(opt)}
            >
              {opt.icon && (
                <span className="icon">{<opt.icon size={16} />}</span>
              )}
              {typeof getMenuOptionContent(opt) === "string" ? (
                <span className="truncate">{getMenuOptionContent(opt)}</span>
              ) : (
                getMenuOptionContent(opt)
              )}
            </li>
          ))}
        </ul>
    </div>
  );
};

export default Dropdown;
