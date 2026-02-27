# utils/platform_controller.py
# module for handling platform-specific functionality.
###### INTERNAL MODULES ######

from console_controls.console import *

###### EXTERNAL MODULES ######

import sys
import pygame

###### FUNCTIONS ######

def getPlatformNameAndMeta():
    if sys.platform.startswith("win"):
        console.message("Running on Windows")
        platform = 'windows'
        CMD_KEY = pygame.K_LCTRL
    elif sys.platform == "darwin":
        console.message("Running on macOS")
        platform = 'mac'
        CMD_KEY = pygame.K_LMETA
    elif sys.platform.startswith("linux"):
        console.message("Running on Linux")
        platform = 'linux'
        CMD_KEY = pygame.K_LCTRL
    else:
        console.warn(f"Running on unknown platform: {sys.platform}")
        platform = 'unknown'
        CMD_KEY = pygame.K_LCTRL

    try:
        from ctypes import windll
        myappid = 'nimbial.symphony.editor.v1-1' # arbitrary string
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        console.warn('Error importing windll or setting Unique AppID. You might be gui_running on a non-Windows platform.')
        pass # Not on Windows or ctypes is not available

    return platform, CMD_KEY