import React from "react";
import "./tooltip.css";

function Tooltip({
  text = "",
  altText = "",
  align = "top",
  children,
  className = "",
}) {
  const wrapperClassName = [`tooltip-wrapper ${align === "left" || align === "right" ? "align-horizontal" : ""}`, className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapperClassName}>
      {children}
      <span className={`tooltip-text tooltip-${align}`}>
        <span className="tooltip-inner-1">{text}</span>
        {altText && <span className="tooltip-inner-alt">{altText}</span>}
      </span>
    </div>
  );
}

export default Tooltip;
