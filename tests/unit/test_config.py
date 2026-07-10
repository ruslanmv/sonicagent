from sonicagent_rt.config import Settings

def test_defaults_are_safe() -> None:
    settings = Settings(_env_file=None)
    assert settings.store_audio is False
    assert settings.store_transcripts is False
