"""Optional Piper synthesis using the open-source ``piper`` package.

This module does not call a paid speech API. When Piper or the voice files are
absent, synthesis reports ``voice_unavailable`` instead of returning silence.
"""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import logging
import threading
import time
import wave
from pathlib import Path

from sonicagent_rt.audio.pcm import floats_to_pcm16
from sonicagent_rt.config import Settings
from sonicagent_rt.stt.errors import Cancelled, InferenceFailed, InvalidRequest, TextTooLong, VoiceUnavailable
from sonicagent_rt.tts.base import SynthesizedSpeech, TtsStatus
from sonicagent_rt.tts.models import (
    VoiceRecord,
    registry_voices,
    resolve_voice_files,
    validate_voice_id,
    voice_record,
)

logger = logging.getLogger("sonicagent_rt.tts")


class PiperSynthesizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # HV9. Loaded Piper voices are keyed by the MODEL FILE, not the voice id. Several presets
        # are one ONNX model with different synthesis settings or speaker ids — Paola companion
        # and secretary, Sharvard companion/secretary/male, Ald, UPMC Jessica and Pierre — and
        # keying by voice id loaded each of them again: the same ~60 MB twice in memory and a
        # second cold start when the person switched speaking style. The synthesis settings
        # and speaker id are per call (``_synthesis_config``), so one loaded model serves all.
        self._voices: dict[str, object] = {}  # model path → loaded PiperVoice
        self._lock = threading.Lock()
        self._loading: dict[str, threading.Lock] = {}  # model path → lock held while loading
        self._loaded: set[str] = set()  # voice ids served by a loaded model
        self._load_ms: dict[str, float] = {}  # model path → measured cold load

    def describe(self) -> TtsStatus:
        if not self._settings.tts_enabled:
            return TtsStatus(False, False, (), "disabled")
        if importlib.util.find_spec("piper") is None:
            return TtsStatus(False, False, (), "not-installed")
        installed = tuple(sorted(self._installed_voice_ids()))
        if not installed:
            return TtsStatus(False, False, (), "voice-missing")
        return TtsStatus(True, True, installed, None)

    def warmup(self) -> None:
        """Load the default voice. Other installed voices load on first use."""
        if not self._settings.tts_enabled:
            return
        installed = self._installed_voice_ids()
        preferred = self._settings.tts_voice
        if preferred in installed:
            self._voice(preferred)
        elif installed:
            self._voice(sorted(installed)[0])

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
        record = voice_record(voice_id)
        if record is None:
            raise VoiceUnavailable("voice is not in the local voice registry")
        engine = self._voice(voice_id)
        if _cancelled(cancel):
            raise Cancelled("synthesis was cancelled")
        wav = _synthesize_wav(engine, cleaned, record)
        if not wav.startswith(b"RIFF") or b"WAVE" not in wav[:16]:
            raise InferenceFailed("synthesis did not produce WAV audio")
        return SynthesizedSpeech(wav=wav, voice=voice_id, sample_rate=_wav_rate(wav))

    def iter_pcm(self, text: str, *, voice: str, language: str | None, cancel: object):
        """Yield one PCM16 buffer per Piper sentence. Later sentences are not synthesized first."""
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
        validate_voice_id(voice_id)
        record = voice_record(voice_id)
        if record is None:
            raise VoiceUnavailable("voice is not in the local voice registry")
        engine = self._voice(voice_id)
        method = getattr(engine, "synthesize", None)
        if not callable(method):
            speech = self.synthesize(cleaned, voice=voice_id, language=None, cancel=cancel)
            yield speech.sample_rate, _wav_pcm(speech.wav)
            return
        for chunk in method(cleaned, syn_config=_synthesis_config(record)):
            if _cancelled(cancel):
                raise Cancelled("synthesis was cancelled")
            audio = getattr(chunk, "audio_float_array", None)
            if audio is None:
                continue
            yield int(chunk.sample_rate), _float_array_to_pcm16(audio)

    def _installed_voice_ids(self) -> set[str]:
        directory = self._model_dir()
        if not directory.is_dir():
            return set()
        present: set[str] = set()
        for record in registry_voices():
            model = directory / record.model_filename
            config = model.with_name(record.config_filename)
            if model.is_file() and config.is_file():
                present.add(record.id)
        return present

    def _voice(self, voice_id: str) -> object:
        model, config = resolve_voice_files(self._model_dir(), voice_id)
        key = str(model)
        with self._lock:
            cached = self._voices.get(key)
            if cached is not None:
                self._loaded.add(voice_id)
                return cached
            gate = self._loading.setdefault(key, threading.Lock())
        # One load per model even when two presets ask at once: the second waits and reuses it.
        with gate:
            with self._lock:
                cached = self._voices.get(key)
                if cached is not None:
                    self._loaded.add(voice_id)
                    return cached
            if importlib.util.find_spec("piper") is None:
                raise VoiceUnavailable("Piper is not installed")
            config = _loadable_config(config)
            piper = importlib.import_module("piper")
            voice_type = getattr(piper, "PiperVoice", None)
            if voice_type is None or not hasattr(voice_type, "load"):
                raise VoiceUnavailable("installed Piper package cannot load voices")
            started = time.perf_counter()
            try:
                try:
                    loaded = voice_type.load(str(model), config_path=str(config))
                except TypeError:
                    loaded = voice_type.load(str(model))
            except Exception as exc:
                logger.exception("piper voice load failed")
                raise VoiceUnavailable("voice model could not be loaded") from exc
            with self._lock:
                self._voices[key] = loaded
                self._loaded.add(voice_id)
                self._load_ms[key] = round((time.perf_counter() - started) * 1000, 1)
        return loaded

    def is_loaded(self, voice_id: str) -> bool:
        """Is the model behind this voice in memory (whichever preset loaded it)?"""
        try:
            model, _config = resolve_voice_files(self._model_dir(), voice_id)
        except Exception:
            return False
        with self._lock:
            return str(model) in self._voices

    def warm(self, voice_id: str) -> dict[str, object]:
        """Load one voice's model ahead of its first sentence. Never the whole catalogue."""
        cold = not self.is_loaded(voice_id)
        started = time.perf_counter()
        self._voice(voice_id)
        model, _config = resolve_voice_files(self._model_dir(), voice_id)
        return {
            "voice_id": voice_id,
            "cold": cold,
            "ms": round((time.perf_counter() - started) * 1000, 1),
            "load_ms": self._load_ms.get(str(model)),
        }

    def loaded_models(self) -> int:
        with self._lock:
            return len(self._voices)

    def _model_dir(self) -> Path:
        configured = self._settings.tts_model_dir.strip()
        if configured:
            return Path(configured).expanduser()
        return Path(self._settings.resolved_model_cache_dir()) / "tts"


def _loadable_config(config: Path) -> Path:
    """Rewrite mirror configs that store ``PhonemeType.ESPEAK`` instead of ``espeak``."""
    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    raw = payload.get("phoneme_type")
    if not isinstance(raw, str) or not raw.startswith("PhonemeType."):
        return config
    payload["phoneme_type"] = raw.split(".", 1)[1].lower()
    destination = config.with_name(config.name + ".sonic.json")
    try:
        destination.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        return config
    return destination


def _synthesize_wav(voice: object, text: str, record: VoiceRecord) -> bytes:
    method = getattr(voice, "synthesize_wav", None)
    if not callable(method):
        raise VoiceUnavailable("installed Piper package cannot write WAV audio")
    buffer = io.BytesIO()
    try:
        _write_wav(method, buffer, text, _synthesis_config(record))
    except TypeError:
        buffer.seek(0)
        buffer.truncate(0)
        try:
            _write_wav(method, buffer, text, None)
        except Exception as exc:
            logger.exception("piper synthesis failed")
            raise InferenceFailed("speech synthesis failed") from exc
    except Exception as exc:
        logger.exception("piper synthesis failed")
        raise InferenceFailed("speech synthesis failed") from exc
    return buffer.getvalue()


def _write_wav(method: object, buffer: io.BytesIO, text: str, syn_config: object | None) -> None:
    with wave.open(buffer, "wb") as wav_file:
        if syn_config is None:
            method(text, wav_file)
        else:
            method(text, wav_file, syn_config=syn_config)


def _synthesis_config(record: VoiceRecord) -> object:
    piper_config = importlib.import_module("piper.config")
    config_type = getattr(piper_config, "SynthesisConfig")
    return config_type(
        speaker_id=record.speaker_id,
        length_scale=record.length_scale,
        noise_scale=record.noise_scale,
        noise_w_scale=record.noise_w_scale,
    )


def _wav_rate(payload: bytes) -> int:
    with wave.open(io.BytesIO(payload), "rb") as handle:
        return int(handle.getframerate())


def _cancelled(cancel: object) -> bool:
    is_set = getattr(cancel, "is_set", None)
    return bool(is_set()) if callable(is_set) else False


def _wav_pcm(payload: bytes) -> bytes:
    with wave.open(io.BytesIO(payload), "rb") as handle:
        return handle.readframes(handle.getnframes())


def _float_array_to_pcm16(audio: object) -> bytes:
    samples = [float(sample) for sample in audio]  # type: ignore[arg-type]
    return floats_to_pcm16(samples)
