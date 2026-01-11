import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

import "./generic-modal.css";

let blurOverlay = true;
window.electronAPI.getUserSettings().then((data) => {
  blurOverlay = data["fancy_graphics"];
});

function GenericModal({
  isOpen,
  onClose,
  children,
  showXButton = true,
  custom = null,
}) {
  const overlayRef = useRef(null);
  const modalRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const overlay = overlayRef.current;
    const modal = modalRef.current;
    if (overlay) {
      overlay.style.transition =
        "backdrop-filter 0.4s cubic-bezier(0.4,0,0.2,1), background 0.4s cubic-bezier(0.4,0,0.2,1)";
      overlay.style.backdropFilter = "none";
      if (blurOverlay) overlay.style.backdropFilter = "blur(0px)";
      overlay.style.background = "rgba(0,0,0,0)";

      modal.style.transition =
        "opacity 0.2s, transform 0.4s cubic-bezier(0.4,1.4,0.4,1)";
      modal.style.opacity = "0";
      modal.style.transform = "scale(0.9)";
      setTimeout(() => {
        if (blurOverlay) {
          overlay.style.backdropFilter = "blur(3px)";
          overlay.style.background = "rgba(0,0,0,0.35)";
        } else {
          overlay.style.background = "rgba(0,0,0,0.5)";
        }
        modal.style.opacity = "1";
        modal.style.transform = "scale(1)";
      }, 10);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className={`modal-overlay`} ref={overlayRef}>
      <div
        className={`modal-container${" " + custom}`}
        ref={modalRef}
        onClick={(e) => e.stopPropagation()}
      >
        {showXButton ? (
          <button className="close-button" onClick={onClose}>
            <X size={16} strokeWidth={2.5} />
          </button>
        ) : null}
        <div className={`modal-content${" " + custom}`}>{children}</div>
      </div>
    </div>
  );
}

export default GenericModal;
