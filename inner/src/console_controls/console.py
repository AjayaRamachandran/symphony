# console_controls/console.py
# module for operating the pseudo-console's data.
###### IMPORT ######

import time

###### METHODS / CLASSES ######

consoleMessages = []

class console:
    @staticmethod
    def log(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Symphony] ' + str(message)
        print(_msg)
        consoleMessages.append(((_msg), "gray"))

    @staticmethod
    def message(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Message] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "magenta"))

    @staticmethod
    def warn(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Warning] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "yellow"))

    @staticmethod
    def error(message):
        _msg = time.strftime('%Y-%m-%d %H:%M:%S') + ' > [Error] ' + str(message)
        print(_msg)
        consoleMessages.append((_msg, "red"))