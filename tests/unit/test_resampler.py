from sonicagent_rt.audio.pcm import floats_to_pcm16, pcm16_to_floats
from sonicagent_rt.audio.resampler import resample_pcm16_mono


def test_resampler_downsamples_pcm16_mono() -> None:
    source = floats_to_pcm16([0.0, 0.25, 0.5, 0.75])
    out = resample_pcm16_mono(source, source_rate=4, target_rate=2)
    samples = pcm16_to_floats(out)
    assert len(samples) == 2
    assert samples[0] == 0.0
    assert 0.74 < samples[1] < 0.76


def test_resampler_same_rate_returns_bytes() -> None:
    source = floats_to_pcm16([0.1, -0.1])
    assert resample_pcm16_mono(source, source_rate=16000, target_rate=16000) == source
