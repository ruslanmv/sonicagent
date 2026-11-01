"""Per-voice, per-profile Piper timings on THIS machine (HV9).

Real Piper, real voice files from ruslanmv/hp-piper-voices, the engine the speech socket uses.
For each voice: cold model load, warm time to the first sentence's audio, synthesis real-time
factor, and whether a second preset on the same model loaded it again. Not a Quest number:
Quest timings come from the Avatar's stt-check.html#remote against a deployed Space.

    python -m benchmarks.voices.profiles --voices /tmp/sonic-voices/tts
"""

from __future__ import annotations

import argparse
import json
import threading
import time

from sonicagent_rt.config import Settings
from sonicagent_rt.tts.models import voice_record
from sonicagent_rt.tts.piper_process import PiperSynthesizer

SAMPLES = {
    ("en", "companion"): "Hello, I'm here. How can I help you today?",
    (
        "en",
        "secretary",
    ): "Good morning. Let's review your schedule. You have three meetings, at 9:30, 11:00 and 2:15.",
    ("it", "companion"): "Ciao, sono qui con te. Come stai oggi?",
    (
        "it",
        "secretary",
    ): "Buongiorno. Vediamo insieme gli impegni di oggi: tre riunioni, alle 9:30, alle 11 e alle 14:15.",
    ("es", "companion"): "Hola, estoy aquí contigo. ¿Cómo estás hoy?",
    (
        "es",
        "secretary",
    ): "Buenos días. Revisemos tu agenda: tres reuniones, a las 9:30, a las 11 y a las 14:15.",
}


def measure(engine: PiperSynthesizer, voice_id: str) -> dict[str, object]:
    record = voice_record(voice_id)
    assert record is not None
    warm = engine.warm(voice_id)
    text = SAMPLES.get((record.language, record.role)) or SAMPLES[(record.language, "companion")]
    cancel = threading.Event()
    runs = []
    for _ in range(3):
        t0 = time.perf_counter()
        first = None
        samples = 0
        rate = 22050
        for rate, pcm in engine.iter_pcm(text, voice=voice_id, language=record.language, cancel=cancel):
            if first is None:
                first = (time.perf_counter() - t0) * 1000
            samples += len(pcm) // 2
        total = (time.perf_counter() - t0) * 1000
        audio_ms = samples / rate * 1000
        runs.append((first, total, audio_ms))
    best = min(runs, key=lambda r: r[1])
    # Cancellation: how long until synthesis stops once asked, mid-reply.
    stop = threading.Event()
    long_text = " ".join([text] * 6)
    t0 = time.perf_counter()
    stopped_after = None
    try:
        for _rate, _pcm in engine.iter_pcm(long_text, voice=voice_id, language=record.language, cancel=stop):
            stop.set()
            t_set = time.perf_counter()
    except Exception:
        stopped_after = round((time.perf_counter() - t_set) * 1000, 1)
    return {
        "voice": voice_id,
        "role": record.role,
        "speaker_id": record.speaker_id,
        "length_scale": record.length_scale,
        "cold_load_ms": warm["load_ms"] if warm["cold"] else None,
        "model_reused": not warm["cold"],
        "first_audio_ms": round(best[0], 1),
        "synthesis_ms": round(best[1], 1),
        "audio_ms": round(best[2], 1),
        "rtf": round(best[1] / best[2], 3),
        "cancel_ms": stopped_after,
        "loaded_models": engine.loaded_models(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voices", default="/tmp/sonic-voices/tts")
    parser.add_argument(
        "--ids",
        default="en_US-kristin-medium,en_US-lessac-medium,it_IT-paola-medium,it_IT-paola-companion,"
        "es_ES-sharvard-companion,es_ES-sharvard-secretary,es_ES-sharvard-male",
    )
    args = parser.parse_args()
    engine = PiperSynthesizer(
        Settings(_env_file=None, tts_enabled=True, tts_model_dir=args.voices, tts_max_chars=2000)
    )
    rows = [measure(engine, v) for v in args.ids.split(",")]
    print(json.dumps(rows, indent=1))
    print("| voice | profile | speaker | cold load | model reused | first audio | RTF | cancel |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        cold = "—" if r["cold_load_ms"] is None else f"{r['cold_load_ms']:.0f} ms"
        print(
            f"| `{r['voice']}` | {r['role']} | {r['speaker_id']} | {cold} | {'yes' if r['model_reused'] else 'no'} |"
            f" {r['first_audio_ms']:.0f} ms | {r['rtf']} | {r['cancel_ms']} ms |"
        )


if __name__ == "__main__":
    main()
