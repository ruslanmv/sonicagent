"""CPU/GPU Whisper transcription through faster-whisper and CTranslate2.

The model object is loaded once per process. Requests do not download weights.
Startup warmup may download only when ``SONIC_STT_ALLOW_DOWNLOAD`` is true.
"""

from __future__ import annotations

import importlib.util
import logging
import threading
from typing import Any

from sonicagent_rt.audio.decode import WHISPER_SAMPLE_RATE
from sonicagent_rt.config import Settings
from sonicagent_rt.stt.base import SttStatus, Transcript
from sonicagent_rt.stt.errors import (
    Cancelled,
    InferenceFailed,
    ModelUnavailable,
    RateLimited,
    UnsupportedModel,
)
from sonicagent_rt.stt.model_store import verify_manifest
from sonicagent_rt.stt.models import canonical_size, installed_model_dir, public_model_id

logger = logging.getLogger("sonicagent_rt.stt")


class FasterWhisperTranscriber:
    """Thread-bounded faster-whisper adapter. One loaded model is reused."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max(1, settings.stt_max_concurrency))
        self._model: Any = None
        self._ready = False
        self._loading = False
        self._failed = False
        self._resolved_device, self._resolved_compute = _planned_device(settings)
        try:
            self._public_model = public_model_id(settings.stt_model)
            self._size = canonical_size(settings.stt_model)
            self._config_reason: str | None = None
        except UnsupportedModel as exc:
            self._public_model = settings.stt_model
            self._size = ""
            self._config_reason = "unsupported-model"
            self._config_error = exc.message
        else:
            self._config_error = ""

    def describe(self) -> SttStatus:
        with self._lock:
            ready = self._ready
            loading = self._loading
            failed = self._failed
        library = _library_installed()
        reason: str | None
        if self._config_reason:
            reason = self._config_reason
            available = False
        elif not library:
            reason = "library-missing"
            available = False
        elif ready:
            reason = None
            available = True
        elif failed:
            reason = "load-failed"
            available = True
        elif loading:
            reason = "model-loading"
            available = True
        else:
            reason = "model-not-loaded"
            available = True
        return SttStatus(
            available=available,
            ready=ready and available,
            model=self._public_model if not self._config_reason else "",
            device=self._resolved_device,
            compute_type=self._resolved_compute,
            languages=tuple(self._settings.parsed_stt_languages()),
            reason=reason,
        )

    def warmup(self) -> None:
        self._load(allow_download=self._settings.stt_allow_download)

    def transcribe(
        self,
        samples: list[float],
        *,
        sample_rate: int,
        language: str | None,
        model: str,
        request_id: str,
        cancel: object,
    ) -> Transcript:
        del request_id
        if sample_rate != WHISPER_SAMPLE_RATE:
            raise InferenceFailed("audio was not normalized before transcription")
        if _cancelled(cancel):
            raise Cancelled("transcription was cancelled")
        requested = public_model_id(model) if model else self._public_model
        if requested != self._public_model:
            raise UnsupportedModel("requested speech model is not the loaded model")
        model_object = self._load(allow_download=False)
        if _cancelled(cancel):
            raise Cancelled("transcription was cancelled")
        if not self._slots.acquire(blocking=False):
            raise RateLimited("too many transcriptions are in progress")
        try:
            if _cancelled(cancel):
                raise Cancelled("transcription was cancelled")
            return self._infer(model_object, samples, language, cancel)
        finally:
            self._slots.release()

    def _load(self, *, allow_download: bool) -> Any:
        if self._config_reason:
            raise ModelUnavailable(self._config_error or "speech model configuration is invalid")
        if not _library_installed():
            raise ModelUnavailable("faster-whisper is not installed")
        with self._load_lock:
            if self._model is not None:
                return self._model
            with self._lock:
                self._loading = True
            try:
                loaded = self._build_model(allow_download=allow_download)
            except ModelUnavailable:
                with self._lock:
                    self._loading = False
                    self._failed = True
                raise
            except Exception as exc:
                logger.exception("speech model load failed")
                with self._lock:
                    self._loading = False
                    self._failed = True
                raise ModelUnavailable("speech model could not be loaded") from exc
            with self._lock:
                self._model = loaded
                self._loading = False
                self._ready = True
                self._failed = False
            logger.info(
                "speech model loaded model=%s device=%s compute_type=%s",
                self._public_model,
                self._resolved_device,
                self._resolved_compute,
            )
            return loaded

    def _build_model(self, *, allow_download: bool) -> Any:
        source, local_only = self._source(allow_download=allow_download)
        device, compute_type = _resolve_runtime_device(self._settings)
        self._resolved_device = device
        self._resolved_compute = compute_type
        from faster_whisper import WhisperModel

        return WhisperModel(
            source,
            device=device,
            compute_type=compute_type,
            cpu_threads=max(1, self._settings.stt_cpu_threads),
            num_workers=1,
            download_root=self._settings.resolved_model_cache_dir(),
            local_files_only=local_only,
        )

    def _source(self, *, allow_download: bool) -> tuple[str, bool]:
        explicit = self._settings.stt_model_path.strip()
        if explicit:
            from pathlib import Path

            path = Path(explicit).expanduser()
            if not (path / "model.bin").is_file():
                raise ModelUnavailable("speech model is not installed")
            try:
                verify_manifest(path)
            except RuntimeError as exc:
                raise ModelUnavailable("speech model files failed validation") from exc
            return str(path), True
        cache = installed_model_dir(self._settings.resolved_model_cache_dir(), self._size)
        if (cache / "model.bin").is_file():
            try:
                verify_manifest(cache)
            except RuntimeError as exc:
                raise ModelUnavailable("speech model files failed validation") from exc
            return str(cache), True
        if allow_download:
            return self._size, False
        raise ModelUnavailable("speech model is not installed")

    def _infer(self, model_object: Any, samples: list[float], language: str | None, cancel: object) -> Transcript:
        import numpy as np

        audio = np.asarray(samples, dtype=np.float32)
        try:
            segments, info = model_object.transcribe(
                audio,
                language=language,
                task="transcribe",
                beam_size=max(1, self._settings.stt_beam_size),
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=self._settings.stt_vad_filter,
                without_timestamps=True,
                word_timestamps=False,
            )
            parts: list[str] = []
            for segment in segments:
                if _cancelled(cancel):
                    raise Cancelled("transcription was cancelled")
                text = str(getattr(segment, "text", "") or "").strip()
                if text:
                    parts.append(text)
        except Cancelled:
            raise
        except Exception as exc:
            logger.exception("speech transcription failed")
            raise InferenceFailed("transcription failed") from exc
        detected = language or str(getattr(info, "language", "") or "und")
        duration_ms = int(round(len(samples) * 1000 / WHISPER_SAMPLE_RATE))
        return Transcript(
            text=" ".join(parts).strip(),
            language=detected,
            model=self._public_model,
            duration_ms=duration_ms,
        )


def _library_installed() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def _cancelled(cancel: object) -> bool:
    is_set = getattr(cancel, "is_set", None)
    return bool(is_set()) if callable(is_set) else False


def _planned_device(settings: Settings) -> tuple[str, str]:
    device = settings.stt_device.strip().lower() or "cpu"
    compute = settings.stt_compute_type.strip().lower() or "int8"
    if device in {"cuda", "gpu"}:
        return "cuda", "float16" if compute in {"int8", "default", ""} else compute
    if device == "auto":
        return "auto", compute or "int8"
    return "cpu", compute or "int8"


def _resolve_runtime_device(settings: Settings) -> tuple[str, str]:
    requested = settings.stt_device.strip().lower() or "cpu"
    compute = settings.stt_compute_type.strip().lower() or "int8"
    if requested in {"cpu", ""}:
        return "cpu", compute or "int8"
    cuda = _cuda_device_count()
    if requested == "auto":
        if cuda > 0:
            return "cuda", "float16" if compute in {"int8", "default", ""} else compute
        return "cpu", "int8" if compute in {"default", ""} else compute
    if requested in {"cuda", "gpu"}:
        if cuda <= 0:
            raise ModelUnavailable("GPU inference was requested but no CUDA device is available")
        return "cuda", "float16" if compute in {"int8", "default", ""} else compute
    raise ModelUnavailable("unsupported inference device")


def _cuda_device_count() -> int:
    if importlib.util.find_spec("ctranslate2") is None:
        return 0
    import ctranslate2

    counter = getattr(ctranslate2, "get_cuda_device_count", None)
    if not callable(counter):
        return 0
    try:
        return int(counter())
    except Exception:
        return 0
