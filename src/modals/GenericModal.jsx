import React from 'react';
import { X } from 'lucide-react'

import './generic-modal.css';

function GenericModal({ isOpen, onClose, children, showXButton = true }) {
  if (!isOpen) return null; // Don't render if modal is closed

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={e => e.stopPropagation()}>
        {showXButton ? <button className="close-button" onClick={onClose}><X size={16} strokeWidth={2.5}/></button> : null}
        {/* <button className="close-button" onClick={onClose}><X size={16} strokeWidth={2.5}/></button> */}
        <div className="modal-content">
          {children}
        </div>
      </div>
    </div>
  );
}

export default GenericModal;
