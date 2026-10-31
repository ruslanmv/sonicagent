"""Optional Piper synthesis using the open-source ``piper`` package.

This module does not call a paid speech API. When Piper or the voice files are
absent, synthesis reports ``voice_unavailable`` instead of returning silence.
"""

from __future__ import annotations

import importlib
import importlib.util
import io
import logging
import threading
import wave
from pathlib import Path

from sonicagent_rt.config import Settings
from sonicagent_rt.stt.errors import Cancelled, InferenceFailed, InvalidRequest, TextTooLong, VoiceUnavailable
from sonicagent_rt.tts.base import SynthesizedSpeech, TtsStatus
from sonicagent_rt.tts.models import registry_voice_ids, resolve_voice_files, validate_voice_id

logger = logging.getLogger("sonicagent_rt.tts")


class PiperSynthesizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._voices: dict[str, object] = {}
        self._lock = threading.Lock()
        self._loaded: set[str] = set()

    def describe(self) -> TtsStatus:
        if not self._settings.tts_enabled:
            return TtsStatus(False, False, (), "disabled")
        if importlib.util.find_spec("piper") is None:
            return TtsStatus(False, False, (), "not-installed")
        installed = tuple(sorted(self._installed_voice_ids()))
        ready = bool(self._loaded)
        reason = None if ready else ("voice-not-loaded" if installed else "voice-missing")
        return TtsStatus(True, ready, installed, reason)

    def synthesize(self, text: str, *, voice: str, language: str | None, cancel: object) -> SynthesizedSpeech:
        del language
        if not self._settings.tts_enabled:
            raise VoiceUnavailable("speech synthesis is disabled")
        cleaned = text.strip()
        if not cleaned:
            raise InvalidRequest("text is empty")
        if len(cleaned) > self._settings.tts_max_chars:
            raise TextTooLong("text is longer than the configured maximum")
        if _cancelled(cancel):
            raise Cancelled("synthesis was cancelled")
        voice_id = voice.strip() or self._settings.tts_voice
        try:
            validate_voice_id(voice_id)
        except Exception as exc:
            raise VoiceUnavailable("voice id is not allowed") from exc
        engine = self._voice(voice_id)
        if _cancelled(cancel):
            raise Cancelled("synthesis was cancelled")
        wav = _synthesize_wav(engine, cleaned)
        if not wav.startswith(b"RIFF") or b"WAVE" not in wav[:16]:
            raise InferenceFailed("synthesis did not produce WAV audio")
        return SynthesizedSpeech(wav=wav, voice=voice_id, sample_rate=_wav_rate(wav))

    def _installed_voice_ids(self) -> set[str]:
        directory = self._model_dir()
        if not directory.is_dir():
            return set()
        present: set[str] = set()
        for voice_id in registry_voice_ids():
            try:
                resolve_voice_files(directory, voice_id)
            except VoiceUnavailable:
                continue
            present.add(voice_id)
        return present

    def _voice(self, voice_id: str) -> object:
        with self._lock:
            cached = self._voices.get(voice_id)
            if cached is not None:
                return cached
        if importlib.util.find_spec("piper") is None:
            raise VoiceUnavailable("Piper is not installed")
        model, config = resolve_voice_files(self._model_dir(), voice_id)
        piper = importlib.import_module("piper")
        voice_type = getattr(piper, "PiperVoice", None)
        if voice_type is None or not hasattr(voice_type, "load"):
            raise VoiceUnavailable("installed Piper package cannot load voices")
        try:
            try:
                loaded = voice_type.load(str(model), config_path=str(config))
            except TypeError:
                loaded = voice_type.load(str(model))
        except Exception as exc:
            logger.exception("piper voice load failed")
            raise VoiceUnavailable("voice model could not be loaded") from exc
        with self._lock:
            self._voices[voice_id] = loaded
            self._loaded.add(voice_id)
        return loaded

    def _model_dir(self) -> Path:
        configured = self._settings.tts_model_dir.strip()
        if configured:
            return Path(configured).expanduser()
        return Path(self._settings.resolved_model_cache_dir()) / "tts"


def _synthesize_wav(voice: object, text: str) -> bytes:
    method = getattr(voice, "synthesize_wav", None)
    if not callable(method):
        raise VoiceUnavailable("installed Piper package cannot write WAV audio")
    buffer = io.BytesIO()
    try:
        with wave.open(buffer, "wb") as wav_file:
            method(text, wav_file)
    except Exception as exc:
        logger.exception("piper synthesis failed")
        raise InferenceFailed("speech synthesis failed") from exc
    return buffer.getvalue()


def _wav_rate(payload: bytes) -> int:
    with wave.open(io.BytesIO(payload), "rb") as handle:
        return int(handle.getframerate())


def _cancelled(cancel: object) -> bool:
    is_set = getattr(cancel, "is_set", None)
    return bool(is_set()) if callable(is_set) else False
