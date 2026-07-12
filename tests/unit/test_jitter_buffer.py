import pytest

from sonicagent_rt.audio.jitter_buffer import JitterBuffer


def test_jitter_buffer_reorders_contiguous_frames() -> None:
    jitter = JitterBuffer(capacity_frames=4)
    jitter.push(1, b"b")
    assert jitter.pop_ready() == []
    jitter.push(0, b"a")
    assert jitter.pop_ready() == [b"a", b"b"]


def test_jitter_buffer_rejects_over_capacity() -> None:
    jitter = JitterBuffer(capacity_frames=1)
    jitter.push(1, b"b")
    with pytest.raises(BufferError):
        jitter.push(2, b"c")
