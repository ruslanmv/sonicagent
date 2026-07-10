from enum import StrEnum

class SessionState(StrEnum):
    CREATED="created"
    CONNECTING="connecting"
    LISTENING="listening"
    TRANSCRIBING="transcribing"
    THINKING="thinking"
    SPEAKING="speaking"
    INTERRUPTED="interrupted"
    CLOSING="closing"
    CLOSED="closed"
    ERROR="error"
