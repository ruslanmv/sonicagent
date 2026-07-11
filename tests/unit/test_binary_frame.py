import pytest
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, BinaryFrameError, decode_frame, encode_frame
from sonicagent_rt.protocol.constants import HEADER_SIZE, Codec, MessageType


def test_binary_frame_round_trip_matches_golden() -> None:
    frame = BinaryAudioFrame(MessageType.AUDIO_INPUT, Codec.PCM16, 0, 16000, 7, 123456, b"\x00\x01")
    encoded = encode_frame(frame)
    assert len(encoded) == HEADER_SIZE + 2
    assert encoded.hex() == "5341010101003e8000000007000000000001e240000000020001"
    assert decode_frame(encoded) == frame


def test_rejects_non_pcm_v1() -> None:
    with pytest.raises(BinaryFrameError, match="PCM16"):
        encode_frame(BinaryAudioFrame(MessageType.AUDIO_INPUT, Codec.OPUS_RESERVED, 0, 16000, 1, 1, b""))


def test_rejects_payload_length_mismatch() -> None:
    encoded = bytearray(
        encode_frame(BinaryAudioFrame(MessageType.AUDIO_INPUT, Codec.PCM16, 0, 16000, 1, 1, b"12"))
    )
    encoded[-1:] = b""
    with pytest.raises(BinaryFrameError, match="payload length"):
        decode_frame(encoded)
