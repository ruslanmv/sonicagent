"""Construct the optional Piper engine."""

from __future__ import annotations

from sonicagent_rt.config import Settings
from sonicagent_rt.tts.piper_process import PiperSynthesizer


def create_tts_engine(settings: Settings) -> PiperSynthesizer:
    return PiperSynthesizer(settings)
