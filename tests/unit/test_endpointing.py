"""Energy endpointing is the detector that runs without a Silero file."""

from sonicagent_rt.vad.energy_fallback import EnergyEndpoint
from sonicagent_rt.vad.silero_onnx import silero_available


def test_energy_endpoint_requires_speech_then_silence() -> None:
    detector = EnergyEndpoint(
        threshold=0.2,
        min_speech_ms=20,
        min_silence_ms=40,
        pre_roll_ms=0,
        max_utterance_sec=2,
        sample_rate=16000,
    )
    assert detector.push([0.0] * 320) == []
    assert [event.kind for event in detector.push([0.8] * 320)] == ["started"]
    assert detector.push([0.8] * 320) == []
    finished = detector.push([0.0] * 640)
    assert [event.kind for event in finished] == ["utterance"]
    assert finished[0].samples


def test_silero_is_not_bundled() -> None:
    assert silero_available() is False
