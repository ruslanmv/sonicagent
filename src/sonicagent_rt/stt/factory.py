"""Construct the configured batch speech engine."""

from __future__ import annotations

from sonicagent_rt.config import Settings
from sonicagent_rt.stt.faster_whisper import FasterWhisperTranscriber


def create_stt_engine(settings: Settings) -> FasterWhisperTranscriber:
    return FasterWhisperTranscriber(settings)
