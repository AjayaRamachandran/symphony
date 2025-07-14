import React, { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { useDirectory } from '@/contexts/DirectoryContext';

import './field.css';

const Field = ({
  value: controlledValue,
  onChange,
  onFocus = () => {}, // default to no-op
  //onBlur, // if you want to accept onBlur prop, uncomment this
  initialValue = '',
  height = '33px',
  fontSize = '1.3em',
  whiteSpace = 'auto',
  defaultText = '',
  className = 'field',
  lightDark = ['#606060', '#c2c2c2'],
  width = '200px',
  searchField = false,
  singleLine = false // new prop
}) => {
  const isControlled = controlledValue !== undefined && onChange !== undefined;
  const [uncontrolledValue, setUncontrolledValue] = useState(initialValue);
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef(null);
  const inputRef = useRef(null);
  const { setIsFieldSelected } = useDirectory();

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
      // Optionally call onBlur if you have one
      // if (onBlur) onBlur(e);

      setEditing(false);
      e.target.blur(); // unfocus input or textarea on Enter
    }
    if (e.key === 'Tab') {
      e.preventDefault(); // prevent default tab behavior if needed
      // implement custom tab navigation if needed
    }
  };

  useEffect(() => {
    if (editing) {
      if (singleLine && inputRef.current) {
        const el = inputRef.current;
        el.focus();
        el.setSelectionRange(el.value.length, el.value.length);
      } else if (!singleLine && textareaRef.current) {
        const el = textareaRef.current;
        el.focus();
        el.setSelectionRange(el.value.length, el.value.length);
      }
    }
  }, [editing, singleLine]);

  if (editing) {
    if (singleLine) {
      return (
        <input
          ref={inputRef}
          type="text"
          value={value}
          autoFocus
          onChange={handleChange}
          onBlur={e => {
            setIsFieldSelected(false);
            setTimeout(() => setEditing(false), 300);
            // if (onBlur) onBlur(e); // call parent onBlur if needed
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            onFocus();
            setIsFieldSelected(true);
            console.log('focused');
          }}
          className={className + '-span scrollable dark-bg'}
          style={{
            height,
            fontSize,
            whiteSpace: 'nowrap',
            width,
            color: value === '' ? lightDark[0] : lightDark[1],
            overflowX: 'auto'
          }}
        />
      );
    } else {
      return (
        <textarea
          ref={textareaRef}
          type="text"
          value={value}
          autoFocus
          onChange={handleChange}
          onBlur={e => {
            setIsFieldSelected(false);
            setTimeout(() => setEditing(false), 300);
            // if (onBlur) onBlur(e); // call parent onBlur if needed
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            onFocus();
            setIsFieldSelected(true);
            console.log('focused');
          }}
          className={className + '-span scrollable dark-bg'}
          style={{
            height,
            fontSize,
            whiteSpace,
            paddingTop: '7px',
            width,
            color: value === '' ? lightDark[0] : lightDark[1],
            overflow: 'auto',
          }}
        />
      );
    }
  }

  return (
    <div
      onClick={() => {
        if (!editing) setEditing(true);
      }}
      className={className + ' scrollable dark-bg'}
      style={{
        height,
        fontSize,
        whiteSpace: singleLine ? 'nowrap' : 'pre-wrap',
        width,
        color: value === '' ? lightDark[0] : lightDark[1],
        overflowX: singleLine ? 'hidden' : 'auto',
        overflowY: singleLine ? 'hidden' : 'auto',
        cursor: 'text',
        display: 'flex'
      }}
      onFocus={() => {
        onFocus();
        setIsFieldSelected(true);
        console.log('focused');
      }}
      tabIndex={0}
    >
      {searchField ? (
        <Search size={15} style={{ marginRight: '5px', flexShrink: 0 }} />
      ) : (
        ''
      )}
      <span
        className="scrollable dark-bg"
        style={{
          overflowX: singleLine ? 'hidden' : 'auto',
          overflowY: singleLine ? 'hidden' : 'auto',
          whiteSpace: singleLine ? 'nowrap' : 'pre-wrap',
          wordBreak: singleLine ? 'normal' : 'break-word',
          padding: !searchField ? '7px' : '0px',
          flex: 1,
        }}
        onFocus={() => {
          onFocus();
          setIsFieldSelected(true);
          console.log('focused');
        }}
      >
        {searchField ? value || defaultText : value || defaultText}
      </span>
    </div>
  );
};

export default Field;
