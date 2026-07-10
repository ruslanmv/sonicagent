from enum import IntEnum

MAGIC = b"SA"
PROTOCOL_VERSION = 1
HEADER_SIZE = 24

class MessageType(IntEnum):
    MICROPHONE_AUDIO = 0x01
    SYNTHESIZED_AUDIO = 0x02

class Codec(IntEnum):
    PCM_S16LE = 0x01
    OPUS_RESERVED = 0x02
