# Transaction Rules

This document outlines the foundation for how we are going to be processing the transaction system for undo and redo in the Editor of Symphony.

## What is a transaction?
A transaction is a specific beginning-to-end action whose data can be stored as a singular unit. The reductive principle that we define transactions from is the idea that using only a list of transactions on a specific document, we can build that entire document from zero.

In code, a transaction is defined as a child of the `Transaction` object. Transactions have a string representation, which will help us read back the transaction history of a document in detail. I'm purposefully not showing examples here, because the idea is that what is actually contained in a transaction is extremely open-ended, it should support any and all actions that we can take on a document.

Here is the general structure of a transaction:
```
TransactionType(Transaction)
- String representation
- UserID (for now, we use 1, but in Symphony v1.2, this could be a unique id for each collaborator)
- Action, defined as a callback that is performed on the document
- Timestamp
```

## How do we store transactions?
Transactions are stored in two stacks: the **undo stack**, and the **redo stack**. When transactions are created, they are pushed onto the undo stack automatically (and the redo stack is flushed).

If a user presses Ctrl + Z, *their* most recent transaction in the undo stack is moved to the redo stack, and if Ctrl + Shift + Z is pressed, then *their* oldest timestamped transaction (will be on top) in the redo stack is popped and pushed back onto the undo stack.

In code, these two stacks are instances of the `Stack` object. The stack object has the following methods:

```
- push (adds to end/top)
- pop (removes from end/top and returns)
- prepend (adds to start/bottom)
- snag (removes from start/bottom and returns)
- insert (inserts at index)
- flush (deletes all elements)
- safeFlush (deletes all elements and returns them as list)
- get (gets at index with optional default value)
- getAll (gets all elements as a list)
- indexOf (gets index of element matching input)
- tail (gets end/top 10 values as list, optional count)
- head (gets start/bottom 10 values as list, optional count)
```

## How do we use transactions?

When building the document, we have the current state of the document, and the initial state of the document (the state of the document when launching the GUI). Then, in parallel, as the user completes actions, we update the current version, and in parallel, we store each of the  finalized actions in an undoStack. When the user presses Undo (Ctrl + Z), we go from the initial state of the document, and apply the callbacks of all the transactions in the stack, without the most recent transaction.

## How do we save transactions?
Short answer: we don't.

Long answer: We save the current state of the file, but we don't reload it or anything when saving. Weonly load from the undo/redo stacks when undoing or redoing, and all other times we keep the existing functionality of the current state.
