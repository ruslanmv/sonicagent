from __future__ import annotations
from dataclasses import dataclass
import struct
from .constants import HEADER_SIZE, MAGIC, PROTOCOL_VERSION, Codec, MessageType

_HEADER = struct.Struct(">2sBBBBH I Q I")


class BinaryFrameError(ValueError):
    pass


@dataclass(frozen=True)
class BinaryAudioFrame:
    message_type: int
    codec: int
    flags: int
    sample_rate: int
    sequence: int
    timestamp_us: int
    payload: bytes

    def encode(self) -> bytes:
        return encode_frame(self)


def encode_frame(frame: BinaryAudioFrame) -> bytes:
    if frame.codec != int(Codec.PCM16):
        raise BinaryFrameError("protocol v1 supports only PCM16")
    if not 0 <= frame.flags <= 255:
        raise BinaryFrameError("flags out of range")
    if not 1 <= frame.sample_rate <= 192000:
        raise BinaryFrameError("sample_rate out of range")
    if not 0 <= frame.sequence <= 0xFFFFFFFF:
        raise BinaryFrameError("sequence out of range")
    if not 0 <= frame.timestamp_us <= 0xFFFFFFFFFFFFFFFF:
        raise BinaryFrameError("timestamp_us out of range")
    payload = bytes(frame.payload)
    header = _HEADER.pack(
        MAGIC,
        PROTOCOL_VERSION,
        frame.message_type,
        frame.codec,
        frame.flags,
        frame.sample_rate,
        frame.sequence,
        frame.timestamp_us,
        len(payload),
    )
    assert len(header) == HEADER_SIZE
    return header + payload


def decode_frame(data: bytes | bytearray | memoryview) -> BinaryAudioFrame:
    raw = bytes(data)
    if len(raw) < HEADER_SIZE:
        raise BinaryFrameError("frame shorter than 24-byte header")
    magic, version, message_type, codec, flags, sample_rate, sequence, timestamp_us, payload_len = (
        _HEADER.unpack(raw[:HEADER_SIZE])
    )
    if magic != MAGIC:
        raise BinaryFrameError("bad magic")
    if version != PROTOCOL_VERSION:
        raise BinaryFrameError("unsupported protocol version")
    if codec != int(Codec.PCM16):
        raise BinaryFrameError("protocol v1 supports only PCM16")
    if message_type not in {int(MessageType.AUDIO_INPUT), int(MessageType.AUDIO_OUTPUT)}:
        raise BinaryFrameError("unknown message type")
    if len(raw) - HEADER_SIZE != payload_len:
        raise BinaryFrameError("payload length mismatch")
    return BinaryAudioFrame(
        message_type, codec, flags, sample_rate, sequence, timestamp_us, raw[HEADER_SIZE:]
    )
