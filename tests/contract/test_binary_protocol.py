from pathlib import Path
from sonicagent_rt.protocol.binary_frame import decode_frame, encode_frame


def test_golden_binary_frame_v1_is_stable() -> None:
    golden = Path("tests/golden/protocol/binary-frame-v1.hex").read_text().replace(" ", "").strip()
    frame = decode_frame(bytes.fromhex(golden))
    assert len(bytes.fromhex(golden)[:24]) == 24
    assert frame.sample_rate == 16000
    assert frame.sequence == 7
    assert frame.timestamp_us == 123456
    assert frame.payload == b"\x00\x01"
    assert encode_frame(frame).hex() == golden
