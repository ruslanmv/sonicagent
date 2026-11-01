"""Select the endpoint detector that can actually run."""

from __future__ import annotations

from sonicagent_rt.config import Settings
from sonicagent_rt.vad.energy_fallback import EnergyEndpoint


def create_endpoint(settings: Settings) -> EnergyEndpoint:
    return EnergyEndpoint(
        threshold=settings.vad_threshold,
        min_speech_ms=settings.vad_min_speech_ms,
        min_silence_ms=settings.vad_min_silence_ms,
        pre_roll_ms=settings.vad_pre_roll_ms,
        max_utterance_sec=min(settings.vad_max_utterance_sec, settings.max_audio_seconds),
        sample_rate=settings.input_sample_rate,
    )


def vad_backend(settings: Settings) -> str:
    """Silero is not bundled. Energy endpointing is the running detector."""
    del settings
    return "energy"
