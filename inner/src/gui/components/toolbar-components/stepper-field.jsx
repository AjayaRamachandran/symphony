import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import Tooltip from "@/ui/tooltip";
import { IconButton } from "./icon-button.jsx";

/**
 * Renders a compact numeric stepper that commits bounded integer values.
 */
export function StepperField({ label, suffix, value, min = 1, onCommit }) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  /**
   * Parses, bounds, and commits the current field draft.
   */
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
      <IconButton
        label={`Decrease ${label}`}
        onClick={() => commitValue(value - 1)}
      >
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
      <IconButton
        label={`Increase ${label}`}
        onClick={() => commitValue(value + 1)}
      >
        <ChevronUp size={15} />
      </IconButton>
    </div>
  );
}
