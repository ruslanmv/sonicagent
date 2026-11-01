"""Select the endpoint detector that can actually run."""

from __future__ import annotations

from sonicagent_rt.config import Settings
from sonicagent_rt.vad.energy_fallback import EnergyEndpoint
from sonicagent_rt.vad.silero_onnx import SileroScorer, silero_available


def create_endpoint(settings: Settings) -> EnergyEndpoint:
    scorer = None
    if vad_backend(settings) == "silero":
        scorer = SileroScorer(settings.vad_model_path)
    return EnergyEndpoint(
        threshold=settings.vad_threshold,
        min_speech_ms=settings.vad_min_speech_ms,
        min_silence_ms=settings.vad_min_silence_ms,
        pre_roll_ms=settings.vad_pre_roll_ms,
        max_utterance_sec=min(settings.vad_max_utterance_sec, settings.max_audio_seconds),
        sample_rate=settings.input_sample_rate,
        scorer=scorer,
    )


def vad_backend(settings: Settings) -> str:
    if settings.vad_provider.strip().lower() == "silero" and silero_available(settings.vad_model_path):
        return "silero"
    return "energy"
