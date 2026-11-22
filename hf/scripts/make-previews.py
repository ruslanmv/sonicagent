"""Make Voice Studio preview WAVs (`hf/ui/examples/<voice>.wav`) and audition sentences for them.

A preview is the first thing a person hears of a voice, so it is synthesized exactly as the Space
would (SonicAgent's own Piper path, the voice's registry style), then finished for a clean start:
120 ms of silence, an 8 ms fade-in and a -1 dBFS peak. Raw Piper output starts at the first sample
and is normalized to 0 dBFS: Aurora's opened on a -34 dB hiss and both Piper Italiano voices lost a
lone opening "Ciao." (Whisper heard "Tu l'hai sta?"), which people heard as a strange sound.

    # compare sentences for one voice: onset level, clipping, what Whisper hears
    python hf/scripts/make-previews.py --cache /tmp/sa-cache audition it_IT-aurora-medium \
        "Buongiorno, sono Aurora. Come posso aiutarti oggi?" "Piacere di conoscerti."
    # write the preview (and keep catalog.json's `sample` the same sentence)
    python hf/scripts/make-previews.py --cache /tmp/sa-cache write it_IT-aurora-medium "Buongiorno, …"

`--cache` is a SONIC_MODEL_CACHE_DIR holding the voice under tts/ (benchmarks/quest_italian/
fetch_voices.py fills one). Audition needs faster-whisper (`small` is downloaded once).
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LEAD_S, FADE_S, PEAK_DBFS = 0.12, 0.008, -1.0


def synthesize(voice: str, text: str) -> tuple[np.ndarray, int]:
    sys.path.insert(0, str(ROOT / "src"))
    from sonicagent_rt.config import Settings
    from sonicagent_rt.tts.piper_process import PiperSynthesizer

    engine = PiperSynthesizer(Settings(tts_enabled=True, model_cache_dir=os.environ["SONIC_MODEL_CACHE_DIR"]))
    speech = engine.synthesize(text, voice=voice, language=None, cancel=None)
    with wave.open(io.BytesIO(speech.wav)) as w:
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return pcm, rate


def finish(x: np.ndarray, rate: int) -> np.ndarray:
    fade = int(rate * FADE_S)
    x = x.copy()
    x[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
    x[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    x *= (10 ** (PEAK_DBFS / 20)) / max(1e-9, float(np.abs(x).max()))
    return np.concatenate([np.zeros(int(rate * LEAD_S), dtype=np.float32), x])


def onset_db(x: np.ndarray, rate: int, ms: int = 30) -> float:
    head = x[: int(rate * ms / 1000)]
    return float(20 * np.log10(np.sqrt(np.mean(head * head)) + 1e-9))


def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def cer(ref: str, hyp: str) -> float:
    """Character error rate after normalizing: Whisper's "da casa" for "a casa" is not a defect."""
    r, h = norm(ref).replace(" ", ""), norm(hyp).replace(" ", "")
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / max(1, len(r))


_asr = None


def hear(x: np.ndarray, rate: int) -> str:
    global _asr
    if _asr is None:
        from faster_whisper import WhisperModel

        _asr = WhisperModel("small", device="cpu", compute_type="int8")
    t = np.arange(0, len(x) / rate, 1 / 16000)
    audio = np.interp(t, np.arange(len(x)) / rate, x).astype(np.float32)
    segs, _ = _asr.transcribe(audio, language=None, beam_size=5)
    return " ".join(s.text.strip() for s in segs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True)
    ap.add_argument("action", choices=["audition", "write"])
    ap.add_argument("voice")
    ap.add_argument("texts", nargs="+")
    a = ap.parse_args()
    os.environ["SONIC_MODEL_CACHE_DIR"] = a.cache
    if a.action == "audition":
        for text in a.texts:
            raw, rate = synthesize(a.voice, text)
            clipped = int(np.sum(np.abs(raw) >= 0.9995))
            heard = hear(finish(raw, rate), rate)
            match = f"CER {cer(text, heard):.2f}"
            print(
                f"{a.voice} | raw onset {onset_db(raw, rate):.0f} dB | clipped {clipped} | {len(raw) / rate:.2f}s"
            )
            print(f"   said : {text}\n   heard: {heard}  [{match}]")
        return 0
    # Gate the take: Whisper must hear the sentence (CER <= 0.10) and it must start quietly.
    # Piper's noise is fixed within one process and differs between processes, so a failed take
    # is retried by running this command again, not by looping here.
    raw, rate = synthesize(a.voice, a.texts[0])
    heard = hear(finish(raw, rate), rate)
    print(f"onset {onset_db(raw, rate):.0f} dB, CER {cer(a.texts[0], heard):.2f}, heard: {heard}")
    if cer(a.texts[0], heard) > 0.10 or onset_db(raw, rate) >= -45:
        print(
            "not clean: run again (a new process gives a new take) or choose another sentence",
            file=sys.stderr,
        )
        return 2
    out = finish(raw, rate)
    dest = ROOT / "hf" / "ui" / "examples" / f"{a.voice}.wav"
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"wrote {dest.relative_to(ROOT)} ({len(out) / rate:.2f}s): {a.texts[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
