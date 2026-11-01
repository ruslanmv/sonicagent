from enum import IntEnum

MAGIC = b"SA"
PROTOCOL_VERSION = 1
HEADER_SIZE = 24


class MessageType(IntEnum):
    AUDIO_INPUT = 1
    AUDIO_OUTPUT = 2


class Codec(IntEnum):
    PCM16 = 1
    OPUS_RESERVED = 2


FLAG_END_OF_UTTERANCE = 1 << 0

CONTROL_EVENTS = ("ping", "session.update", "response.cancel")
SERVER_EVENTS = (
    "session.created",
    "session.updated",
    "speech.started",
    "speech.frame",
    "speech.stopped",
    "transcript.partial",
    "transcript.final",
    "transcript.failed",
    "response.created",
    "response.text.delta",
    "response.text.done",
    "response.audio.started",
    "response.audio.done",
    "response.cancelled",
    "metrics.turn",
    "error",
)
