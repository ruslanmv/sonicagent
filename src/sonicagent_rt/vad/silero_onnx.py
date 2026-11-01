"""Silero VAD ONNX scorer.

The model file is not stored in Git. Set ``SONIC_VAD_MODEL_PATH`` to the pinned
v5.1.2 ONNX file. The checksum is ``SILERO_VAD_SHA256``. A missing or mismatched
file does not pretend to be Silero.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

SILERO_VAD_SHA256 = "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"
SILERO_WINDOW = 512


def silero_available(path: str = "", expected_sha256: str = SILERO_VAD_SHA256) -> bool:
    file = Path(path).expanduser() if path else None
    if file is None or not file.is_file():
        return False
    return _sha256(file) == expected_sha256


class SileroScorer:
    """Return the latest speech probability for 16 kHz mono audio."""

    def __init__(self, model_path: str) -> None:
        if not silero_available(model_path):
            raise ValueError("silero model is missing or does not match the pinned checksum")
        import numpy as np
        import onnxruntime as ort

        self._np = np
        self._session = ort.InferenceSession(str(Path(model_path).expanduser()), providers=["CPUExecutionProvider"])
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._buffer: list[float] = []
        self.last = 0.0

    def __call__(self, samples: list[float]) -> float:
        self._buffer.extend(samples)
        while len(self._buffer) >= SILERO_WINDOW:
            window = self._np.asarray(self._buffer[:SILERO_WINDOW], dtype=self._np.float32).reshape(1, SILERO_WINDOW)
            del self._buffer[:SILERO_WINDOW]
            output, self._state = self._session.run(
                None,
                {
                    "input": window,
                    "state": self._state,
                    "sr": self._np.array(16000, dtype=self._np.int64),
                },
            )
            self.last = float(output.reshape(-1)[0])
        return self.last


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
