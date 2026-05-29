import Tooltip from "@/ui/tooltip";

/**
 * Renders a toolbar icon button with tooltip, active state, and optional sizing content.
 */
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
  const classes = [
    "editor-icon-button",
    sizingContent ? "has-sizer" : "",
    isActive ? "active" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tooltip text={label} altText={shortcut} align="bottom">
      <button
        className={classes}
        style={buttonStyle}
        aria-label={label}
        aria-pressed={isActive}
        onClick={onClick}
        type="button"
      >
        {sizingContent && (
          <span className="editor-cycle-button-sizer">{sizingContent}</span>
        )}
        <span className="editor-icon-button-content">{children}</span>
      </button>
    </Tooltip>
  );
}
