import React, { useState, useEffect } from "react";

import { TriangleAlert, Settings } from "lucide-react";

import Field from "@/ui/Field";
import Switch from "@/ui/Switch";

function UserSettings({ onComplete }) {
  const [focused, setFocused] = useState(false);
  const [userName, setUserName] = useState("");

  const [settings, setSettings] = useState({
    needs_onboarding: true,
    search_for_updates: true,
    show_splash_screen: true,
    user_name: "",
    show_console: false,
    fancy_graphics: true,
    disable_auto_save: false,
    disable_delete_confirm: false,
    show_button_tooltips: true,
    clef_presets: {},
  });

  const handleUserNameChange = (name) => {
    setUserName(name);
    window.electronAPI.updateUserSettings("user_name", name);
    // console.log(name + 'is the username');
  };

  useEffect(() => {
    window.electronAPI.getUserSettings().then((data) => {
      setSettings(data ?? {});
      setUserName(data.user_name ?? "");
    });
  }, []);

  const handleToggle = (key) => {
    const updatedValue = !settings[key];
    setSettings((prev) => ({ ...prev, [key]: updatedValue }));
    window.electronAPI.updateUserSettings(key, updatedValue);
  };

  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "15px" }}
      >
        <Settings size={20} />
        User Settings
      </div>
      <div
        className="modal-paragraph"
        style={{ width: "100%", color: "var(--muted-foreground)" }}
      >
        Configure your Symphony to work best for you. These settings can be
        reverted at any time.
      </div>

      <div
        className="scrollable"
        style={{
          height: "400px",
          width: "550px",
          overflowY: "auto",
          overflowX: "hidden",
          outline: "1px solid #434343",
          padding: "15px 20px 0px 20px",
          borderRadius: "6px",
        }}
      >
        <div className="setting-row">
          <div className="modal-body2">
            Change My Name
          </div>
        </div>
        <div
          className="modal-subtext wide"
          style={{ marginBottom: "10px", width: "100%" }}
        >
          Change how you're addressed on various text windows across Symphony.
        </div>
        <Field
          value={userName}
          style={{ height: "33px", fontSize: "14px", width: "300px" }}
          onChange={(e) => handleUserNameChange(e.target.value || "")}
          singleLine={true}
        />

        <div className="setting-row" style={{ marginTop: "30px" }}>
          <div className="modal-body2">
            Automatically Search for Updates and Notify Me
          </div>
          <Switch
            checked={settings.search_for_updates}
            onChange={() => handleToggle("search_for_updates")}
          />
        </div>
        <div className="modal-subtext wide">
          On launch, get the latest Symphony version and prompt an update if I'm
          behind.
        </div>

        <div className="setting-row" style={{ marginTop: "30px" }}>
          <div className="modal-body2">
            Show Button Tooltips in Editor
          </div>
          <Switch
            checked={settings.show_button_tooltips}
            onChange={() => handleToggle("show_button_tooltips")}
          />
        </div>
        <div className="modal-subtext wide">
          Show tooltips for each button in the Editor toolbar when hovering over them.
        </div>

        {/*<div className="setting-row">
          <div className="modal-body2">
            Close Project Manager when in Editor
          </div>
          <Switch
            checked={settings.close_project_manager_when_editing}
            onChange={() => handleToggle("close_project_manager_when_editing")}
          />
        </div>
        <div className="modal-subtext wide">
          Closes the Project Manager when you decide to open a Symphony in the
          editor.
        </div>*/}

        <div className="setting-row">
          <div className="modal-body2">
            Show Splash Screen on Startup
          </div>
          <Switch
            checked={settings.show_splash_screen}
            onChange={() => handleToggle("show_splash_screen")}
          />
        </div>
        <div className="modal-subtext wide">
          Shows the splash screen, with quick launch and resources, upon
          starting the project manager.
        </div>

        <div className="setting-row" style={{ marginTop: "30px" }}>
          <div className="modal-body2">
            Use Fancy Graphics
          </div>
          <Switch
            checked={settings.fancy_graphics}
            onChange={() => handleToggle("fancy_graphics")}
          />
        </div>
        <div className="modal-subtext wide">
          Enables some modern graphic effects within the UI. Only disable if you
          are experiencing significant slowness across the system. This setting
          does not affect the editor.{" "}
          <i>You may need to restart Symphony to see changes.</i>
        </div>

        {/* <div className='setting-row'>
          <div className='modal-body2 wide display'>Launch Symphony on Startup</div>
          <label className='switch'>
            <input type='checkbox' checked={settings.launch_on_startup} onChange={() => handleToggle('launch_on_startup')} />
            <span className='slider'></span>
          </label>
        </div>
        <div className='modal-subtext wide'>Opens Symphony Project Manager when you turn on your PC, so you can jump right in whenever you're inspired.</div> */}

        <div className="divider">
          <span className="divider-label red">DANGER ZONE</span>
        </div>

        <div className="setting-row">
          <div className="modal-body2">
            <TriangleAlert size={14} style={{ marginRight: "5px" }} />
            Disable Auto-Save Backup
          </div>
          <Switch
            checked={settings.disable_auto_save}
            onChange={() => handleToggle("disable_auto_save")}
            dangerous
          />
        </div>
        <div className="modal-subtext wide">
          Disables saving backup copies of every session in the dedicated
          auto-save folder. Switching this off does not impact auto-saving to
          the working file.
        </div>

        <div className="setting-row">
          <div className="modal-body2">
            <TriangleAlert size={14} style={{ marginRight: "5px" }} /> Disable
            Delete Confirmation
          </div>
          <Switch
            checked={settings.disable_delete_confirm}
            onChange={() => handleToggle("disable_delete_confirm")}
            dangerous
          />
        </div>
        <div className="modal-subtext wide">
          Disables the confirmation upon deleting files, and removing folders.
        </div>

        {window.electronAPI.platform.startsWith("win") && 1 === 2 && (
          <>
            <div className="setting-row">
              <div className="modal-body2">
                <TriangleAlert size={14} style={{ marginRight: "5px" }} />
                Show Console
              </div>
              <Switch
                checked={settings.show_console}
                onChange={() => handleToggle("show_console")}
                dangerous
              />
            </div>
            <div className="modal-subtext wide">
              Shows the console output of the Editor in a separate window. May
              cause program instability in some fringe cases. Proceed with
              caution.
            </div>
          </>
        )}
      </div>

      <button
        className="call-to-action-2"
        onClick={() => onComplete()}
      >
        Save & Exit
      </button>
    </>
  );
}

export default UserSettings;
