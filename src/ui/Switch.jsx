import React from "react";

import "./switch.css";

function Switch({
  checked = false,
  onChange,
  dangerous = false,
  disabled = false,
  className = "",
}) {
  const rootClassName = ["ui-switch", className].filter(Boolean).join(" ");
  const sliderClassName = [
    "ui-switch-slider",
    dangerous ? "ui-switch-slider-dangerous" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <label className={rootClassName}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
      />
      <span className={sliderClassName}></span>
    </label>
  );
}

export default Switch;
