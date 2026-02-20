# console_controls/console.py
# module for operating the pseudo-console's data.

###### IMPORT ######

import time
import sys
import os

###### METHODS / CLASSES ######

consoleMessages = []

class console:
    _ANSI_GRAY = "\033[90m"
    _ANSI_YELLOW = "\033[93m"
    _ANSI_RED = "\033[91m"
    _ANSI_CYAN = "\033[96m"
    _ANSI_RESET = "\033[0m"

    @staticmethod
    def _caller_info():
        """
        Returns (filename, line_number)
        """
        frame = sys._getframe(2)  # caller of log/warn/etc
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno
        return filename, lineno

    @staticmethod
    def log(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Log] ({file}:{line}) {message}"
        )
        print(f"{console._ANSI_GRAY}{_msg}{console._ANSI_RESET}")
        consoleMessages.append((_msg, "gray"))

    @staticmethod
    def message(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Message] ({file}:{line}) {message}"
        )
        print(f"{console._ANSI_CYAN}{_msg}{console._ANSI_RESET}")
        consoleMessages.append((_msg, "cyan"))

    @staticmethod
    def warn(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Warning] ({file}:{line}) {message}"
        )
        print(f"{console._ANSI_YELLOW}{_msg}{console._ANSI_RESET}")
        consoleMessages.append((_msg, "yellow"))

    @staticmethod
    def error(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Error] ({file}:{line}) {message}"
        )
        print(f"{console._ANSI_RED}{_msg}{console._ANSI_RESET}")
        consoleMessages.append((_msg, "red"))
