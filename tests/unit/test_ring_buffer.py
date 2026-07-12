from sonicagent_rt.audio.ring_buffer import RingBuffer


def test_ring_buffer_trims_oldest_bytes() -> None:
    buf = RingBuffer(5)
    buf.append(b"abc")
    buf.append(b"def")
    assert buf.read() == b"bcdef"
    assert buf.size_bytes == 5


def test_ring_buffer_clear() -> None:
    buf = RingBuffer(4)
    buf.append(b"data")
    buf.clear()
    assert buf.read() == b""
    assert buf.size_bytes == 0
