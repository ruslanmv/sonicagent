"""Optional batch text-to-speech."""

from __future__ import annotations

from typing import Any

__all__ = ["create_tts_engine"]


def __getattr__(name: str) -> Any:
    if name == "create_tts_engine":
        from sonicagent_rt.tts.factory import create_tts_engine

        return create_tts_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
