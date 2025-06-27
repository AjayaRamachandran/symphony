import React, { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';

import './field.css'

const Field = ({
  value: controlledValue,
  onChange,
  initialValue = '',
  height = '33px',
  fontSize = '1.3em' ,
  whiteSpace = 'auto',
  defaultText = '',
  className = 'field',
  lightDark = ['#606060', '#c2c2c2'],
  width = '100%',
  searchField = false}) => {
  
  const isControlled = controlledValue !== undefined && onChange !== undefined;
  const [uncontrolledValue, setUncontrolledValue] = useState(initialValue);
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef(null);

  const value = isControlled ? controlledValue : uncontrolledValue;
  const handleChange = (e) => {
    if (isControlled) {
      onChange(e);
    } else {
      setUncontrolledValue(e.target.value);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      setEditing(false);
    }
    if (e.key === 'Tab') {
      e.preventDefault(); // prevent default tab
      // nextRef.current?.focus(); // manually focus next element (not defined)
    }
  };

  useEffect(() => {
    if (editing && textareaRef.current) {
      // Move cursor to end
      const el = textareaRef.current;
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length);
    }
  }, [editing]);

  return editing ? (
    <textarea
      ref={textareaRef}
      type="text"
      value={value}
      autoFocus
      onChange={handleChange}
      onBlur={() => {setTimeout(() => setEditing(false), 300);}}

      onKeyDown={handleKeyDown}
      className={className}
      style={{ height: height, fontSize: fontSize, whiteSpace: whiteSpace, paddingTop: '7px', width: width, color: value == '' ? lightDark[0] : lightDark[1] }}
    />
  ) : (
    <div
      onClick={() => setEditing(true)}
      className={className}
      style={{ height: height, fontSize: fontSize, whiteSpace: whiteSpace, width: width, color: value == '' ? lightDark[0] : lightDark[1] }}
    >
      {searchField ? (<Search size={15} style={{marginRight: '5px', flexShrink: 0}} />) : ''}
      {searchField ? (value || defaultText) : (value || defaultText)}
      
    </div>
  );
};

export default Field;
