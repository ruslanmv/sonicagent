"""Silero ONNX is not bundled with this service.

Energy endpointing in ``vad.energy_fallback`` is the detector the server runs.
Pointing ``SONIC_VAD_PROVIDER=silero`` does not download a model and does not
mark voice activity as ready.
"""

from __future__ import annotations


def silero_available() -> bool:
    return False
