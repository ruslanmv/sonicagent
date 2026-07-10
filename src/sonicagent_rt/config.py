"""Environment-backed application settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SONIC_", extra="ignore")
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"
    auth_mode: str = "development"
    max_concurrent_sessions: int = 8
    input_sample_rate: int = 16000
    audio_frame_ms: int = 20
    vad_provider: str = "silero"
    stt_provider: str = "faster-whisper"
    llm_provider: str = "mock"
    tts_provider: str = "piper"
    store_transcripts: bool = False
    store_audio: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
