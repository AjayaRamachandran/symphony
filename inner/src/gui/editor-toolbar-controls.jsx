import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import Dropdown from "@/ui/dropdown";
import Tooltip from "@/ui/tooltip";

export function SvgAssetIcon({ source, size = 16 }) {
  return (
    <span
      className="editor-svg-icon"
      style={{ width: size, height: size }}
      dangerouslySetInnerHTML={{ __html: source }}
    />
  );
}

export function IconButton({
  label,
  shortcut,
  isActive = false,
  color,
  className = "",
  style = {},
  sizingContent = null,
  children,
  onClick,
}) {
  const buttonStyle = color ? { ...style, "--button-accent": color } : style;

  return (
    <Tooltip text={label} altText={shortcut} align="bottom">
      <button
        className={`editor-icon-button ${sizingContent ? "has-sizer" : ""} ${isActive ? "active" : ""} ${className}`.trim()}
        style={buttonStyle}
        aria-label={label}
        aria-pressed={isActive}
        onClick={onClick}
        type="button"
      >
        {sizingContent && <span className="editor-cycle-button-sizer">{sizingContent}</span>}
        <span className="editor-icon-button-content">{children}</span>
      </button>
    </Tooltip>
  );
}

export function StepperField({ label, suffix, value, min = 1, onCommit }) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const commitValue = (nextValue) => {
    const parsed = Number.parseInt(nextValue, 10);
    if (!Number.isFinite(parsed)) {
      setDraft(String(value));
      return;
    }

    const bounded = Math.max(min, parsed);
    setDraft(String(bounded));
    onCommit(bounded);
  };

  return (
    <div className="editor-stepper" aria-label={label}>
      <IconButton label={`Decrease ${label}`} onClick={() => commitValue(value - 1)}>
        <ChevronDown size={15} />
      </IconButton>
      <Tooltip text={label} align="bottom">
        <label
          className="editor-number-field"
          style={{ "--number-width": `${Math.max(1, draft.length)}ch` }}
        >
          <input
            aria-label={label}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onBlur={() => commitValue(draft)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.currentTarget.blur();
              }
            }}
          />
          <span>{suffix}</span>
        </label>
      </Tooltip>
      <IconButton label={`Increase ${label}`} onClick={() => commitValue(value + 1)}>
        <ChevronUp size={15} />
      </IconButton>
    </div>
  );
}

export function ToolbarDropdown({ label, value, options, onSelect }) {
  return (
    <Tooltip text={label} align="bottom">
      <div className="editor-toolbar-dropdown">
        <div className="editor-toolbar-dropdown-sizer" aria-hidden="true">
          {options.map((option) => (
            <span key={option.label} className="editor-toolbar-dropdown-sizer-item">
              {(option.icon || option.node || option.selectedNode) && <span className="editor-toolbar-dropdown-icon-space" />}
              <span>{option.label}</span>
            </span>
          ))}
        </div>
        <Dropdown options={options} value={value} onSelect={onSelect} />
      </div>
    </Tooltip>
  );
}
