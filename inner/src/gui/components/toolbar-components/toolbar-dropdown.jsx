import Dropdown from "@/ui/dropdown";
import Tooltip from "@/ui/tooltip";

/**
 * Wraps the shared dropdown with toolbar sizing and tooltip behavior.
 */
export function ToolbarDropdown({ label, value, options, onSelect }) {
  return (
    <Tooltip text={label} align="bottom">
      <div className="editor-toolbar-dropdown">
        <div className="editor-toolbar-dropdown-sizer" aria-hidden="true">
          {options.map((option) => (
            <span
              key={option.label}
              className="editor-toolbar-dropdown-sizer-item"
            >
              {(option.icon || option.node || option.selectedNode) && (
                <span className="editor-toolbar-dropdown-icon-space" />
              )}
              <span>{option.label}</span>
            </span>
          ))}
        </div>
        <Dropdown options={options} value={value} onSelect={onSelect} />
      </div>
    </Tooltip>
  );
}
