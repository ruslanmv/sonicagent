"""Endpoint benchmark math and report text. No network."""

import wave
from io import BytesIO

from benchmarks.endpoints.report import render_markdown
from benchmarks.endpoints.stats import percentile, summarize


def test_percentile_interpolates_and_hides_p99_on_small_samples() -> None:
    assert percentile([10, 20, 30], 50) == 20
    summary = summarize([10, 20, 30, 40])
    assert summary["n"] == 4
    assert summary["p99"] is None
    wide = summarize([float(value) for value in range(20)])
    assert wide["p99"] is not None


def test_report_states_the_measurement_limits() -> None:
    text = render_markdown(
        {
            "measured_at": "2026-11-01T00:50:00+01:00",
            "auth": "bearer",
            "client": {"platform": "Linux", "python": "3.12", "cpu_count": 4},
            "target": {
                "base_url": "https://example.test",
                "space_stage": "RUNNING",
                "space_hardware": "cpu-basic",
                "space_region": "us",
                "space_sha": "abc",
                "git_commit": "deadbeef",
                "git_dirty": False,
            },
            "notes": ["Warmup calls are excluded from the percentile rows."],
            "series": [
                {
                    "name": "tts_it_paola",
                    "warmup": {"total_ms": 290},
                    "summary": {
                        "n": 5,
                        "errors": 0,
                        "total_ms": {"p50": 420, "p95": 510},
                        "audio_ms": {"p50": 600},
                        "rtf": {"p50": 0.7},
                    },
                }
            ],
        }
    )
    assert "not a Quest, phone, or glasses test" in text
    assert "does not stream partial audio" in text
    assert "realtime speech as not implemented" in text
    assert "| tts_it_paola | 5 | 0 | 290 | 420 | 510 | 600 | 0.700 |" in text


def test_fixture_wav_duration_is_readable() -> None:
    from pathlib import Path

    from benchmarks.endpoints.probe import wav_duration_ms

    path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "audio" / "it_ciao.wav"
    duration = wav_duration_ms(path.read_bytes())
    assert duration is not None and duration > 0
    assert wav_duration_ms(b"not-a-wav") is None
    silent = BytesIO()
    with wave.open(silent, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    assert wav_duration_ms(silent.getvalue()) == 1000
