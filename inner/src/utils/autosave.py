# utils/autosave.py
# module for handling editor autosave timing and persistence cadence.
#
# The editor session passes a save callback and an interval (in seconds).
# Autosave runs on its own daemon thread so the cadence is unaffected by
# the React frontend's event loop or by the webview window thread. This
# keeps autosave a backend concern, with the frontend never having to
# know about it.
###### IMPORT ######

import threading
import time

###### INTERNAL MODULES ######

from console_controls.console import *

###### CLASSES ######

class AutoSave:
    '''
    Background autosave scheduler.

    The session passes a `saveCallback` that performs the actual write
    (using `utils/file_io.py`'s `dumpToFile`). AutoSave only owns the
    cadence and the thread, so swapping the persistence behavior later
    is a matter of changing the callback the session passes in.
    '''

    DEFAULT_INTERVAL_SECONDS = 20.0

    def __init__(self, saveCallback, intervalSeconds: float = DEFAULT_INTERVAL_SECONDS):
        '''
        fields:
            saveCallback (callable) - function called when an autosave is due
            intervalSeconds (float) - wall-clock delay between autosaves
        outputs: nothing

        Builds an inactive autosave scheduler. Call `start()` to begin.
        '''
        self.saveCallback = saveCallback
        self.intervalSeconds = float(intervalSeconds)
        self._stopEvent = threading.Event()
        self._thread = None
        self._running = False

    def start(self):
        '''
        fields: none
        outputs: nothing

        Spins up the background thread if it is not already running.
        '''
        if self._running:
            return
        self._stopEvent.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name='SymphonyEditorAutoSave',
            daemon=True,
        )
        self._thread.start()

    def stop(self, joinTimeout: float = 2.0):
        '''
        fields:
            joinTimeout (float) - seconds to wait for the thread to drain
        outputs: nothing

        Signals the thread to exit and joins briefly. Idempotent.
        '''
        if not self._running:
            return
        self._stopEvent.set()
        thread = self._thread
        self._running = False
        self._thread = None
        if thread and thread.is_alive():
            thread.join(timeout=joinTimeout)

    def setInterval(self, intervalSeconds: float):
        '''
        fields:
            intervalSeconds (float) - new cadence in seconds
        outputs: nothing

        Updates the interval. The current sleep finishes first; the new
        cadence applies on the next iteration.
        '''
        self.intervalSeconds = max(1.0, float(intervalSeconds))

    def saveOnClose(self):
        '''
        fields: none
        outputs: nothing

        Performs one synchronous save outside the autosave thread. Use this
        on close so the latest contents always land before the editor
        window goes away, regardless of where in the cadence we were.
        '''
        try:
            self.saveCallback()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"autosave saveOnClose failed: {exc}")

    def _loop(self):
        '''
        fields: none
        outputs: nothing

        Sleep / save loop. Uses an event so `stop()` interrupts the wait.
        '''
        while not self._stopEvent.wait(self.intervalSeconds):
            try:
                self.saveCallback()
            except Exception as exc:  # noqa: BLE001
                console.warn(f"autosave callback failed: {exc}")
