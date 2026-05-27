# utils/note.py
# Pure data class for editor notes.
#
# Originally lived in `gui/custom.py` alongside pygame rendering. The editor
# UI now ships as React under `inner/src/gui/`, so the runtime needs a
# pygame-free Note type that `state_loading.py`, `project_state.py`, and
# `editor/editor_session.py` can all share.
###### CLASSES ######

class Note():
    '''
    Editor note data. Pure container; rendering is handled by the React
    frontend.
    '''
    def __init__(self, noteData: dict):
        '''
        fields:
            noteData (dict) - {pitch, time, duration, data_fields}
        outputs: nothing
        '''
        self.pitch = noteData.get('pitch', 1)
        self.time = noteData.get('time', 1)
        self.duration = noteData.get('duration', 1)
        self.dataFields = noteData.get('data_fields', {})

        self.selected = False
        self.visible = True
        self.dragInitialPosition = None
        self.extendOriginalDuration = self.duration

    def __repr__(self):
        return (
            f"Note object with Pitch: {self.pitch}, Time: {self.time}, "
            f"Duration: {self.duration}, Data Fields: {self.dataFields}, "
            f"Selected?: {self.selected}"
        )

    def getData(self):
        '''
        fields: none
        outputs: dict

        Returns a save-ready dict for pickling.
        '''
        return {
            "pitch": self.pitch,
            "time": self.time,
            "duration": self.duration,
            "data_fields": self.dataFields,
        }

    def select(self):
        '''
        fields: none
        outputs: nothing

        Marks the note as selected and caches its drag origin.
        '''
        self.selected = True
        self.drag()

    def unselect(self):
        '''
        fields: none
        outputs: nothing
        '''
        self.selected = False
        self.undrag()

    def hide(self):
        '''
        fields: none
        outputs: nothing
        '''
        self.visible = False

    def unhide(self):
        '''
        fields: none
        outputs: nothing
        '''
        self.visible = True

    def drag(self):
        '''
        fields: none
        outputs: nothing

        Snapshots the current position so a drag can later restore from it.
        '''
        self.dragInitialPosition = [self.time, self.pitch]

    def undrag(self):
        '''
        fields: none
        outputs: nothing
        '''
        self.dragInitialPosition = None

    def setNoteData(self, newData: dict):
        '''
        fields:
            newData (dict) - partial update payload
        outputs: nothing

        Non-destructively updates note properties.
        '''
        self.pitch = newData.get('pitch', self.pitch)
        self.time = newData.get('time', self.time)
        self.duration = newData.get('duration', self.duration)
        self.dataFields = newData.get('data_fields', self.dataFields)
