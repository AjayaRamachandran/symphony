# main.py
# Entry point for the inner editor process.
#
# This file used to be a pygame mainloop with the entire editor UI inline.
# It has been pruned to act as a backend dispatcher: it boots the audio
# mixer, registers the localhost process command server, waits for an
# ``open`` payload from the project manager, then opens a pywebview
# editor window backed by ``editor.EditorSession`` and ``editor.EditorApi``.
#
# The React frontend handles UI mechanics; backend handlers live in
# ``editor/editor_session.py`` so transactions, autosave, audio, and
# persistence stay frontend-agnostic. See AGENTS.md.
###### CONSOLE ######

from console_controls.console import *

###### IMPORT ######

console.message('Welcome to Symphony v1.1.5.')

import time
lastTime = time.time()
START_TIME = lastTime

import os
import sys
import threading
import traceback

# Pygame is still required for ``pygame.mixer`` (note preview / full play)
# and for a few pickle-imported types used by older project files. The
# editor display itself is no longer pygame-driven.
import pygame

console.log("Imported External Libraries " + '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### INTERNAL MODULES ######

import process_command.read_write as pcrw
import sound.instruments as ins
import utils.platform_controller as plat
from editor.editor_api import EditorApi
from editor.editor_session import EditorSession
from editor.editor_window import EditorWindowHost

console.log("Imported Internal Modules " + '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PLATFORM DETECTION ######

platformName, _CMD_KEY = plat.getPlatformNameAndMeta()

###### SYSARG HANDLING ######

SAMPLE_RATE = 44100

def _readEnvBool(key: str, default: bool = False) -> bool:
    '''
    fields:
        key (string) - environment variable name
        default (boolean) - fallback value when the variable is absent
    outputs: boolean
    '''
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


DEBUG_UI_ENABLED = not getattr(sys, "frozen", False)
SHOW_DEBUG_BY_DEFAULT = DEBUG_UI_ENABLED and _readEnvBool("SYMPHONY_SHOW_DEBUG_BY_DEFAULT", True)

console.log(f"sysargs: {sys.argv}")
source_path = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

sessionID = time.strftime('%Y-%m-%d %H%M%S')

console.log("Platform Detection and Sysarg Handling " + '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### AUDIO INITIALIZE ######

# pygame.mixer needs to be initialized before any sp.playNote / playFull
# call. Display init is deliberately omitted: the editor UI now lives in
# a pywebview window.
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
ins.init(source_path)

console.log("Initialized Audio Mixer " + '(' + str(round(time.time() - lastTime, 5)) + ' secs)')
lastTime = time.time()

###### PROCESS COMMAND SERVER ######

console.message("Startup complete in " + str(round(time.time() - START_TIME, 5)) + ' seconds.')
pcrw.startProcessCommandServer()
console.message(f"Process command server listening on localhost:{pcrw.PROCESS_COMMAND_PORT}.")

###### EDITOR LIFECYCLE ######

def _loadOpenContext(pcData: dict) -> dict:
    '''
    fields:
        pcData (dict) - process command payload from the open call
    outputs: dict

    Pulls the per-open settings (autosave directory, tooltip flag) the
    session needs from the symphony data folder. Returns a dict with the
    fields ``EditorSession`` accepts.
    '''
    import json

    args = pcData['args']
    titleText = args['project_file_name']
    workingFilePath = os.path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'

    autoSaveDirectory = None
    try:
        userSettingsPath = os.path.join(args['symphony_data_path'], 'user-settings.json')
        with open(userSettingsPath) as settingsFile:
            settings = json.load(settingsFile)

        directoryPath = os.path.join(args['symphony_data_path'], 'directory.json')
        with open(directoryPath) as directoryFile:
            directory = json.load(directoryFile)

        if not settings.get('disable_auto_save', False):
            autoSaveSection = directory.get('Symphony Auto-Save') or []
            if autoSaveSection:
                autoSaveDirectory = autoSaveSection[0].get('Auto-Save')
    except Exception as exc:  # noqa: BLE001
        console.warn(f"loadOpenContext fell back to defaults: {exc}")

    return {
        "workingFilePath": workingFilePath,
        "titleText": titleText,
        "autoSaveDirectory": autoSaveDirectory,
        "debugUiEnabled": DEBUG_UI_ENABLED,
        "showDebugByDefault": SHOW_DEBUG_BY_DEFAULT,
    }


def runEditorWindowOnce(pcData: dict) -> None:
    '''
    fields:
        pcData (dict) - open command payload
    outputs: nothing

    Loads the requested project, opens one pywebview editor window, and
    blocks this command-loop thread until that window is closed.
    '''
    context = _loadOpenContext(pcData)
    session = EditorSession(
        workingFilePath=context["workingFilePath"],
        titleText=context["titleText"],
        sessionID=sessionID,
        autoSaveDirectory=context["autoSaveDirectory"],
        debugUiEnabled=context["debugUiEnabled"],
        showDebugByDefault=context["showDebugByDefault"],
    )

    host = EditorWindowHost(session=session, titleText=context["titleText"])
    api = EditorApi(session=session, getWindow=lambda: host.window, winmanModule=host.winman)
    host.createWindow(api)

    try:
        if sys.platform in ("win32", "darwin"):
            threading.Thread(
                target=host.installChromeDeferred,
                name="SymphonyEditorChromeInstall",
                daemon=True,
            ).start()
        host.closedEvent.wait()
    finally:
        try:
            session.close()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor session close (post-run) failed: {exc}")


def editorCommandLoop() -> None:
    '''
    fields: none
    outputs: nothing

    Runs inside pywebview's background function thread. The process command
    server stays alive between editor windows so closing the editor only tears
    down that window and its session state.
    '''
    while True:
        pcData = pcrw.waitForOpenCommand()
        if pcData is None:
            continue

        try:
            runEditorWindowOnce(pcData)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        finally:
            pcrw.setGuiIsOpen(False)


def createKeepAliveWindow():
    '''
    fields: none
    outputs: webview.Window

    Creates a hidden host window so pywebview's single event loop can remain
    alive after the visible editor window closes.
    '''
    import webview

    options = {
        "title": "Symphony Editor Host",
        "url": "about:blank",
        "width": 1,
        "height": 1,
        "frameless": True,
        "easy_drag": False,
        "hidden": True,
        "x": -32000,
        "y": -32000,
    }
    try:
        return webview.create_window(**options)
    except TypeError:
        options.pop("hidden", None)
        return webview.create_window(**options)


def runEditorEventLoop() -> None:
    '''
    fields: none
    outputs: nothing

    Starts pywebview once for the lifetime of this inner process.
    '''
    import webview

    createKeepAliveWindow()
    webview.start(debug=not getattr(sys, "frozen", False), func=editorCommandLoop)


###### MAIN ######

runEditorEventLoop()
