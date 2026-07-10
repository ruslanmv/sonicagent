"""Binary audio frame codec for protocol version 1."""
from __future__ import annotations
from dataclasses import dataclass
import struct
from .constants import MAGIC, PROTOCOL_VERSION, HEADER_SIZE, MessageType, Codec

_HEADER = struct.Struct(">2sBBBBHIQI")

@dataclass(slots=True)
class BinaryAudioFrame:
    message_type: MessageType
    codec: Codec
    flags: int
    sample_rate: int
    sequence: int
    timestamp_us: int
    payload: bytes
    version: int = PROTOCOL_VERSION

    def encode(self) -> bytes:
        if not 0 <= self.sequence <= 0xFFFFFFFF:
            raise ValueError("sequence out of range")
        if not 0 <= self.sample_rate <= 0xFFFF:
            raise ValueError("sample_rate out of range")
        header = _HEADER.pack(
            MAGIC, self.version, int(self.message_type), int(self.codec), self.flags,
            self.sample_rate, self.sequence, self.timestamp_us, len(self.payload),
        )
        return header + self.payload

    @classmethod
    def decode(cls, data: bytes) -> "BinaryAudioFrame":
        if len(data) < HEADER_SIZE:
            raise ValueError("frame is shorter than the 24-byte header")
        magic, version, message_type, codec, flags, sample_rate, sequence, timestamp_us, length = _HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ValueError("invalid frame magic")
        payload = data[HEADER_SIZE:]
        if len(payload) != length:
            raise ValueError("payload length mismatch")
        return cls(MessageType(message_type), Codec(codec), flags, sample_rate, sequence, timestamp_us, payload, version)
