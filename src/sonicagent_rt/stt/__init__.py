"""Batch speech-to-text."""

from __future__ import annotations

from typing import Any

__all__ = ["create_stt_engine"]


def __getattr__(name: str) -> Any:
    if name == "create_stt_engine":
        from sonicagent_rt.stt.factory import create_stt_engine

        return create_stt_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
