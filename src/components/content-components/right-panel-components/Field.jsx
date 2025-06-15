import React, { useEffect, useRef, useState } from 'react';

import './field.css'

const Field = ({ initialValue = '',
                  height = '33px',
                  fontSize = '1.3em' ,
                  whiteSpace = 'auto',
                  defaultText = '',
                  className = 'field',
                  lightDark = ['#606060', '#c2c2c2']}) => {

  const [value, setValue] = useState(initialValue);
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      setEditing(false);
    }
    if (e.key === 'Tab') {
      e.preventDefault(); // prevent default tab
      nextRef.current?.focus(); // manually focus next element
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
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => {setTimeout(() => setEditing(false), 300);}}

      onKeyDown={handleKeyDown}
      className={className}
      style={{ height: height, fontSize: fontSize, whiteSpace: whiteSpace, color: value == '' ? lightDark[0] : lightDark[1] }}
    />
  ) : (
    <span
      onClick={() => setEditing(true)}
      className={className}
      style={{ height: height, fontSize: fontSize, whiteSpace: whiteSpace, color: value == '' ? lightDark[0] : lightDark[1] }}
    >
      {value || defaultText}
    </span>
  );
};

export default Field;
