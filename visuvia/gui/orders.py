from enum import Enum

class ConnManOrder(Enum):
    STATUS_FAILED = 1
    STATUS_SYNCING = 2
    STATUS_CONNECTED = 3
    APPEND_TEXT = 4
    CH_INFO_UPDATE = 5
    CH_INFO_DRAW = 6

class CommTaskOrder(Enum):
    SEND_REQUEST: 1
    SEND_STOP: 2
    SEND_DROP: 3
