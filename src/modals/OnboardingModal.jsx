import React, { useState, useEffect } from "react";

import { ArrowRight, LoaderCircle } from "lucide-react";
import Field from "@/ui/Field";
import Tooltip from "@/ui/Tooltip";
import "./modals-styling/onboarding-modal.css";

import note from "@/assets/note-element.svg";

function OnboardingModal({ onComplete }) {
  const [userName, setUserName] = useState("");
  const [page, setPage] = useState(0);

  const handleUpdateUser = () => {
    window.electronAPI.updateUserSettings("needs_onboarding", false);
    onComplete();
  };

  const handleUserNameChange = (name) => {
    setUserName(name);
    window.electronAPI.updateUserSettings("user_name", name);
  };

  useEffect(() => {
    if (page === 1) {
      const timeout = setTimeout(
        () => {
          handleUpdateUser();
        },
        4000 + Math.random() * 500,
      );

      return () => clearTimeout(timeout);
    }
  }, [page]);

  return (
    <>
      <img
        src={note}
        style={{
          opacity: "0.9",
          position: "absolute",
          left: "540px",
          top: "90px",
        }}
      ></img>
      <div
        className="modal-big-title"
        style={{ margin: "15px 0px", width: "500px" }}
      >
        Welcome to Symphony v1.1
      </div>
      {page === 0 ? (
        <>
          <div className="modal-big-body" >
            What's your name?
          </div>
          <div style={{ display: "flex", flexDirection: "row", gap: "10px" }}>
            <Field
              placeholder={<span style={{ color: "#d9d9d977" }}>Enter Name Here</span>}
              value={userName}
              className="field onboarding-field"
              style={{ height: "38px", fontSize: "16px", width: "300px" }}
              onChange={(e) => handleUserNameChange(e.target.value || "")}
              singleLine={true}
            />
            <Tooltip text={userName ? "Continue" : "Skip"}>
              <button
                className={"onboarding-button"}

                onClick={() => setPage(1)}
              >
                <ArrowRight />
              </button>
            </Tooltip>
          </div>
        </>
      ) : (
        <>
          <div
            style={{
              height: "120px",
              fontSize: "20px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              fontFamily: "Instrument Sans, sans-serif",
            }}
          >
            <LoaderCircle className="spin" />
            Getting things ready for you...
          </div>
        </>
      )}
      <div style={{ width: "470px", marginTop: "80px" }}>
        We do not share your information with any third parties. Your name is
        only used to address you personally inside the application, and is
        competely voluntary.
      </div>
    </>
  );
}

export default OnboardingModal;
