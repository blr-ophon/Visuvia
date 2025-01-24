from enum import Enum

class ConnManOrder(Enum):
    STATUS_FAILED = 1
    STATUS_SYNCING = 2
    STATUS_CONNECTED = 3
    APPEND_TEXT = 4
    CH_INFO_UPDATE = 5
    CH_INFO_DRAW = 6

class CommTaskOrder(Enum):
    REQUEST = 1
    STOP = 2
    DROP = 3
