import React, { useCallback, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "./tooltip.css";

let nextTooltipInstanceId = 0;
let suppressedTooltipInstanceId = null;

function Tooltip({
  text = "",
  altText = "",
  align = "top",
  children,
  className = "",
}) {
  const wrapperRef = useRef(null);
  const tooltipRef = useRef(null);
  const instanceIdRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  if (instanceIdRef.current === null) {
    nextTooltipInstanceId += 1;
    instanceIdRef.current = nextTooltipInstanceId;
  }

  const portalTarget = typeof document !== "undefined" ? document.body : null;
  const wrapperClassName = [`tooltip-wrapper ${align === "left" || align === "right" ? "align-horizontal" : ""}`, className]
    .filter(Boolean)
    .join(" ");

  const updatePosition = useCallback(() => {
    if (!wrapperRef.current || !tooltipRef.current) {
      return;
    }

    const triggerRect = wrapperRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const computedScale = Number.parseFloat(
      window.getComputedStyle(tooltipRef.current).scale,
    );
    const normalizedScale =
      Number.isFinite(computedScale) && computedScale > 0 ? computedScale : 1;
    const tooltipWidth = tooltipRect.width / normalizedScale;
    const tooltipHeight = tooltipRect.height / normalizedScale;
    const gap = 6;
    const viewportPadding = 8;

    let top = triggerRect.top - tooltipHeight - gap;
    let left = triggerRect.left + triggerRect.width / 2 - tooltipWidth / 2;

    if (align === "left") {
      top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2;
      left = triggerRect.left - tooltipWidth - gap;
    } else if (align === "right") {
      top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2;
      left = triggerRect.right + gap;
    }

    const maxLeft = window.innerWidth - tooltipWidth - viewportPadding;
    const maxTop = window.innerHeight - tooltipHeight - viewportPadding;
    setPosition({
      left: Math.max(viewportPadding, Math.min(left, maxLeft)),
      top: Math.max(viewportPadding, Math.min(top, maxTop)),
    });
  }, [align]);

  useLayoutEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);

    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [isOpen, updatePosition]);

  useLayoutEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const dismissOnClick = () => {
      suppressedTooltipInstanceId = instanceIdRef.current;
      setIsOpen(false);
    };

    window.addEventListener("pointerdown", dismissOnClick, true);

    return () => {
      window.removeEventListener("pointerdown", dismissOnClick, true);
    };
  }, [isOpen]);

  const tooltipNode = (() => {
    if (!portalTarget || (!text && !altText)) {
      return null;
    }

    return createPortal(
      <span
        ref={tooltipRef}
        className={`tooltip-text tooltip-${align} ${isOpen ? "is-visible" : ""}`.trim()}
        style={{ top: `${position.top}px`, left: `${position.left}px` }}
      >
        <span className="tooltip-inner-1">{text}</span>
        {altText && <span className="tooltip-inner-alt">{altText}</span>}
      </span>,
      portalTarget,
    );
  })();

  const handleOpen = () => {
    if (suppressedTooltipInstanceId === instanceIdRef.current) {
      return;
    }

    suppressedTooltipInstanceId = null;
    updatePosition();
    setIsOpen(true);
  };

  return (
    <div
      className={wrapperClassName}
      ref={wrapperRef}
      onMouseEnter={handleOpen}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={handleOpen}
      onBlur={() => setIsOpen(false)}
    >
      {children}
      {tooltipNode}
    </div>
  );
}

export default Tooltip;
