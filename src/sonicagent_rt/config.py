"""Environment-backed application settings.

The production package uses :mod:`pydantic-settings` when it is installed, but
this module deliberately keeps a small stdlib fallback so lightweight protocol
and unit tests can run before optional service dependencies are bootstrapped.
"""
from __future__ import annotations

from functools import lru_cache
import importlib
import importlib.util
import os
from typing import Any, get_args, get_origin

if importlib.util.find_spec("pydantic_settings") is not None:  # pragma: no cover - optional dependency path.
    _pydantic_settings = importlib.import_module("pydantic_settings")
    BaseSettings = _pydantic_settings.BaseSettings
    SettingsConfigDict = _pydantic_settings.SettingsConfigDict
else:
    BaseSettings = object
    SettingsConfigDict = None


def _coerce_env(value: str, annotation: Any) -> Any:
    """Coerce a string environment value to a simple settings field type."""
    origin = get_origin(annotation)
    if origin is not None:
        annotation = get_args(annotation)[0] if origin is list else str
    if annotation is bool:
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    return value


class _FallbackSettings:
    """Tiny BaseSettings-compatible fallback for local tests and scripts."""

    def __init__(self, **overrides: Any) -> None:
        annotations = getattr(self, "__annotations__", {})
        for name, annotation in annotations.items():
            if name == "model_config":
                continue
            env_name = f"SONIC_{name.upper()}"
            if name in overrides:
                value = overrides[name]
            elif env_name in os.environ:
                value = _coerce_env(os.environ[env_name], annotation)
            else:
                value = getattr(self.__class__, name)
            setattr(self, name, value)


class Settings(BaseSettings if SettingsConfigDict is not None else _FallbackSettings):
    """Runtime settings sourced from ``SONIC_*`` environment variables."""

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(env_file=".env", env_prefix="SONIC_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"
    auth_mode: str = "development"
    jwt_secret: str = "change-me"
    allowed_origins: str = "http://localhost:5173"
    session_ttl_sec: int = 1800
    max_session_sec: int = 3600
    max_concurrent_sessions: int = 8
    resume_window_sec: int = 30
    input_sample_rate: int = 16000
    input_channels: int = 1
    audio_frame_ms: int = 20
    max_jitter_ms: int = 200
    max_outbound_queue_ms: int = 2000
    vad_provider: str = "silero"
    vad_threshold: float = 0.50
    vad_min_speech_ms: int = 200
    vad_min_silence_ms: int = 500
    vad_pre_roll_ms: int = 200
    vad_max_utterance_sec: int = 30
    stt_provider: str = "faster-whisper"
    stt_model: str = "tiny"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_language: str = "auto"
    stt_partials_enabled: bool = False
    stt_model_path: str = ""
    stt_allow_download: bool = False
    stt_warmup: bool = False
    stt_languages: str = "en,es,fr,de,it,pt"
    stt_vad_filter: bool = False
    stt_beam_size: int = 5
    stt_cpu_threads: int = 4
    stt_silence_rms: float = 0.005
    stt_timeout_sec: float = 30.0
    stt_max_concurrency: int = 2
    stt_rate_limit_per_minute: int = 60
    llm_provider: str = "mock"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.4
    llm_max_tokens: int = 256
    tts_provider: str = "piper"
    tts_voice: str = "en_US-lessac-medium"
    tts_workers: int = 2
    tts_phrase_min_chars: int = 24
    tts_phrase_max_chars: int = 180
    tts_cache_enabled: bool = True
    model_cache_dir: str = "~/.cache/sonicagent-rt"
    barge_in_enabled: bool = True
    barge_in_min_speech_ms: int = 80
    barge_in_cancel_timeout_ms: int = 200
    metrics_enabled: bool = True
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    store_transcripts: bool = False
    store_audio: bool = False
    log_transcript_content: bool = False
    voice_enabled: bool = True
    api_key: str = ""
    max_audio_seconds: float = 15.0
    max_upload_bytes: int = 2_097_152
    tts_enabled: bool = False
    tts_model_dir: str = ""
    tts_max_chars: int = 2000
    tts_timeout_sec: float = 30.0

    def parsed_allowed_origins(self) -> list[str]:
        """Browser origins allowed to call the voice API. Wildcard is never accepted."""
        origins: list[str] = []
        for item in self.allowed_origins.split(","):
            origin = item.strip()
            if origin and origin != "*":
                origins.append(origin)
        return origins

    def parsed_stt_languages(self) -> list[str]:
        return [item.strip().lower() for item in self.stt_languages.split(",") if item.strip()]

    def resolved_model_cache_dir(self) -> str:
        return os.path.expanduser(self.model_cache_dir)

    def requires_strong_api_key(self) -> bool:
        environment = self.environment.strip().lower()
        mode = self.auth_mode.strip().lower()
        return environment == "production" or mode == "token"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
