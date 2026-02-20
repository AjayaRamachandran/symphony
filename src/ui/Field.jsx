import React, { useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { useDirectory } from "@/contexts/DirectoryContext";

import "./field.css";

const Field = ({
  value: controlledValue,
  onChange,
  onFocus = () => {},
  onBlur = () => {},
  initialValue = "",
  placeholder = null,
  className = "field",
  style = {},
  singleLine = false,
}) => {
  const isControlled = controlledValue !== undefined && onChange !== undefined;
  const [uncontrolledValue, setUncontrolledValue] = useState(initialValue);
  const inputRef = useRef(null);
  const { setIsFieldSelected } = useDirectory();
  const value = isControlled ? controlledValue : uncontrolledValue;

  const handleChange = (e) => {
    if (isControlled) {
      onChange(e);
      return;
    }
    setUncontrolledValue(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.target.blur();
    }
    if (e.key === "Tab") {
      e.preventDefault();
    }
  };

  const placeholderNode = useMemo(() => {
    if (placeholder === null || placeholder === undefined) return null;
    if (React.isValidElement(placeholder)) return placeholder;
    return <span>{placeholder}</span>;
  }, [placeholder]);

  const hasValue = String(value ?? "").length > 0;

  const controlProps = {
    ref: inputRef,
    value: value ?? "",
    onChange: handleChange,
    onBlur: (e) => {
      setIsFieldSelected(false);
      if (onBlur) onBlur(e);
    },
    onKeyDown: handleKeyDown,
    onFocus: () => {
      onFocus();
      setIsFieldSelected(true);
    },
    className: `${className}-span field-input-control scrollable dark-bg`,
    style: {
      whiteSpace: singleLine ? "nowrap" : "pre-wrap",
    },
  };

  return (
    <div
      className={`${className} field-shell scrollable dark-bg`}
      style={style}
      onClick={() => {
        inputRef.current?.focus();
      }}
    >
      <div className="field-input-wrapper">
        {!hasValue && placeholderNode ? (
          <span className={`field-placeholder ${singleLine ? "single-line" : "multi-line"}`}>{placeholderNode}</span>
        ) : null}
        {singleLine ? (
          <input type="text" {...controlProps} />
        ) : (
          <textarea rows={1} {...controlProps} />
        )}
      </div>
    </div>
  );
};

export default Field;
