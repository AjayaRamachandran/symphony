# utils/project_state.py
# module for handling editor project state transactions.
###### IMPORT ######

import copy
from datetime import datetime

###### INTERNAL MODULES ######

from utils.stack import Stack
from utils.transactions import Transaction
from gui.custom import Note

###### CLASSES ######

class ProjectStateManager():
    '''
    Object to manage transaction capture, undo, and redo replay for project state.
    '''
    def __init__(self, snapshotEditorState, applyEditorStateToRuntime, isCaptureSuspended, undoStack=None, redoStack=None):
        self.snapshotEditorState = snapshotEditorState
        self.applyEditorStateToRuntime = applyEditorStateToRuntime
        self.isCaptureSuspended = isCaptureSuspended

        self.undoStack = undoStack if undoStack is not None else Stack()
        self.redoStack = redoStack if redoStack is not None else Stack()

        self.initialEditorState = self.snapshotEditorState()
        self.pendingInteractionStartState = None
        self.pendingInteractionKind = None

    def replaceEditorState(self, targetState, snapshot):
        '''
        fields:
            targetState (dict) - state object to overwrite\n
            snapshot (dict) - snapshot to apply
        outputs: nothing

        Replaces one editor state map with another snapshot.
        '''
        targetState.clear()
        targetState.update(copy.deepcopy(snapshot))

    def noteMapWithoutSelection(self, noteMapSnapshot):
        '''
        fields:
            noteMapSnapshot (dict) - note map snapshot
        outputs: dict

        Returns a note-map snapshot stripped of selection flags for content comparisons.
        '''
        stripped = {}
        for colorName, notes in noteMapSnapshot.items():
            stripped[colorName] = []
            for noteData in notes:
                stripped[colorName].append({
                    "pitch": noteData["pitch"],
                    "time": noteData["time"],
                    "duration": noteData["duration"],
                    "data_fields": noteData.get("data_fields", {})
                })
        return stripped

    def selectedNoteCount(self, noteMapSnapshot):
        '''
        fields:
            noteMapSnapshot (dict) - note map snapshot
        outputs: number

        Counts selected notes across all color channels in a snapshot.
        '''
        count = 0
        for _colorName, notes in noteMapSnapshot.items():
            for noteData in notes:
                if noteData.get("selected", False):
                    count += 1
        return count

    def pushEditorSnapshotTransaction(self, transactionType, title):
        '''
        fields:
            transactionType (string) - transaction enum/type label\n
            title (string) - human-readable transaction title
        outputs: nothing

        Captures current editor state and pushes it as a finalized undo transaction.
        '''
        if self.isCaptureSuspended():
            return

        snapshot = self.snapshotEditorState()
        self.undoStack.push(
            Transaction(
                transactionType=transactionType,
                title=title,
                action=lambda document, s=snapshot: self.replaceEditorState(document, s),
                timestamp=datetime.now()
            )
        )
        self.redoStack.flush()

    def beginInteractionTransaction(self, kind):
        '''
        fields:
            kind (string) - interaction category (brush/eraser/select)
        outputs: nothing

        Starts a pending interaction transaction by storing the pre-action snapshot.
        '''
        if self.isCaptureSuspended():
            return

        self.pendingInteractionStartState = self.snapshotEditorState()
        self.pendingInteractionKind = kind

    def finalizeInteractionTransaction(self):
        '''
        fields: none\n
        outputs: nothing

        Finalizes an interaction transaction and records one intent-level undo entry if state changed.
        '''
        if self.isCaptureSuspended():
            self.pendingInteractionStartState = None
            self.pendingInteractionKind = None
            return

        if self.pendingInteractionStartState is None:
            return

        currentState = self.snapshotEditorState()
        if self.pendingInteractionStartState == currentState:
            self.pendingInteractionStartState = None
            self.pendingInteractionKind = None
            return

        if self.pendingInteractionKind == "brush":
            transactionType = "NEW_NOTE"
            title = "Draw note"
        elif self.pendingInteractionKind == "eraser":
            transactionType = "DELETE_NOTES"
            title = "Delete note(s)"
        else:
            noteDataBefore = self.noteMapWithoutSelection(self.pendingInteractionStartState["noteMap"])
            noteDataAfter = self.noteMapWithoutSelection(currentState["noteMap"])
            if noteDataBefore != noteDataAfter:
                transactionType = "MOVE_NOTES"
                title = "Move selection"
            else:
                selectedBefore = self.selectedNoteCount(self.pendingInteractionStartState["noteMap"])
                selectedAfter = self.selectedNoteCount(currentState["noteMap"])
                if selectedAfter >= selectedBefore:
                    transactionType = "SELECT_NOTES"
                    title = "Select notes"
                else:
                    transactionType = "UNSELECT_NOTES"
                    title = "Unselect notes"

        self.pushEditorSnapshotTransaction(transactionType, title)
        self.pendingInteractionStartState = None
        self.pendingInteractionKind = None

    def replayUndoTransactions(self):
        '''
        fields: none\n
        outputs: nothing

        Rebuilds runtime state from the initial snapshot and all current undo transactions.
        '''
        replayState = copy.deepcopy(self.initialEditorState)
        for transaction in self.undoStack.getAll():
            transaction.execute(replayState)
        self.applyEditorStateToRuntime(replayState)

    def performUndo(self):
        '''
        fields: none\n
        outputs: nothing

        Moves the latest undo transaction to redo and replays resulting editor state.
        '''
        transaction = self.undoStack.pop()
        if transaction is None:
            return
        self.redoStack.push(transaction)
        self.replayUndoTransactions()

    def performRedo(self):
        '''
        fields: none\n
        outputs: nothing

        Restores the latest redo transaction to undo and replays resulting editor state.
        '''
        transaction = self.redoStack.pop()
        if transaction is None:
            return
        self.undoStack.push(transaction)
        self.replayUndoTransactions()

    def resetTransactionHistory(self):
        '''
        fields: none\n
        outputs: nothing

        Resets initial replay baseline and clears undo/redo stacks for a newly loaded document.
        '''
        self.initialEditorState = self.snapshotEditorState()
        self.pendingInteractionStartState = None
        self.pendingInteractionKind = None
        self.undoStack.flush()
        self.redoStack.flush()


def snapshotNoteMapState(noteMap: dict[str, list[Note]]):
    '''
    fields:
        noteMap (dict) - note map to snapshot
    outputs: dict

    Returns a deep-serializable snapshot of the current note map, including selection state.
    '''
    out = {}
    for colorName, notes in noteMap.items():
        channel: list[dict] = []
        for note in notes:
            channel.append({
                "pitch": note.pitch,
                "time": note.time,
                "duration": note.duration,
                "data_fields": copy.deepcopy(note.dataFields),
                "selected": note.selected
            })
        out[colorName] = channel
    return out