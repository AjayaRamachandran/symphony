# console_controls/console.py
# module for operating the pseudo-console's data.

###### IMPORT ######

import time
import sys
import os

###### METHODS / CLASSES ######

consoleMessages = []

class console:
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
            f"[Symphony] ({file}:{line}) {message}"
        )
        print(_msg)
        consoleMessages.append((_msg, "gray"))

    @staticmethod
    def message(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Message] ({file}:{line}) {message}"
        )
        print(_msg)
        consoleMessages.append((_msg, "magenta"))

    @staticmethod
    def warn(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Warning] ({file}:{line}) {message}"
        )
        print(_msg)
        consoleMessages.append((_msg, "yellow"))

    @staticmethod
    def error(message):
        file, line = console._caller_info()
        _msg = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} > "
            f"[Error] ({file}:{line}) {message}"
        )
        print(_msg)
        consoleMessages.append((_msg, "red"))
