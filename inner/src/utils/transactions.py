# utils/transactions.py
# module for handling transactions.
###### IMPORT ######
from datetime import datetime


###### ENUMS ######
TRANSACTION_TYPE = {
    "NEW_NOTE": "new_note",
    "DELETE_NOTE": "delete_note",
    "MOVE_NOTE": "move_note",
    "CHANGE_TEMPO": "change_tempo",
    "CHANGE_TIME_SIGNATURE": "change_time_signature",
    "CHANGE_BEAT_LENGTH": "change_beat_length",
    "CHANGE_BEATS_PER_MEASURE": "change_beats_per_measure",
    "CHANGE_COLOR": "change_color",
    "CHANGE_WAVE_TYPE": "change_wave_type",
    "CHANGE_KEY": "change_key",
    "CHANGE_MODE": "change_mode",
}

###### CLASSES ######

class Transaction():
    '''
    Base parent object for all transactions.
    '''
    def __init__(self, userID=1, transactionType: TRANSACTION_TYPE = None, action=None, timestamp=None, partialTransaction: bool = False):
        self.userID = userID
        self.transactionType = transactionType
        self.action = action
        self.timestamp = timestamp if (timestamp != None) else datetime.now()
        self.partialTransaction = partialTransaction

    def setAction(self, action):
        '''
        fields:
            action (function | lambda) - the action to run
        outputs: nothing
        
        Sets the action for this transaction.
        '''
        self.action = action

    def execute(self, document):
        '''
        fields:
            document (any) - the document/object to apply the action to
        outputs: any

        Runs the callback action for this transaction.
        '''
        if callable(self.action):
            return self.action(document)
        return None

    def __repr__(self):
        return f'Transaction(UserID={self.userID}, Timestamp={self.timestamp}, PartialTransaction={self.partialTransaction})'

    def __str__(self):
        return f'{self.userID} completed {self.transactionType} at time {self.timestamp}, {"partial" if self.partialTransaction else "complete"}'