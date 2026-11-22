"""Offline checks on the PCM SonicAgent delivered (results/<label>/*.json + wav/).

Per turn: silences at phrase joins (what the listener hears between phrases, before any
underrun), abrupt phrase edges (a clipped syllable ends/starts loud), long pauses inside a
phrase, and an Italian transcription (faster-whisper small) scored against the reference.
"""

import json
import os
import re
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

# Usage: python analyze.py <label> [cases to transcribe, default medium,numbers,long]
label = sys.argv[1]
root = (
    Path(
        os.environ.get("BENCH_RESULTS")
        or Path(__file__).resolve().parent.parent / "results" / "quest_italian"
    )
    / label
)
asr_cases = set((sys.argv[2] if len(sys.argv) > 2 else "medium,numbers,long").split(","))

WIN = 0.010  # 10 ms windows
SIL_DB = -45.0


def read(path):
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x, rate


def db(x):
    return 20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-9)


def frames_db(x, rate):
    n = int(rate * WIN)
    k = len(x) // n
    return np.array([db(x[i * n : (i + 1) * n]) for i in range(k)])


def run_silence(levels, start, step):
    i, c = start, 0
    while 0 <= i < len(levels) and levels[i] < SIL_DB:
        c += 1
        i += step
    return c * WIN * 1000


def boundary_report(x, rate, seg_samples):
    out = []
    pos = 0
    for i, n in enumerate(seg_samples[:-1]):
        pos += n
        a = x[max(0, pos - n) : pos]
        b = x[pos : pos + seg_samples[i + 1]]
        la, lb = frames_db(a, rate), frames_db(b, rate)
        tail = run_silence(la, len(la) - 1, -1)
        head = run_silence(lb, 0, 1)
        # Edge energy: the last/first 10 ms against the phrase's loud level (95th pct).
        ref_a = np.percentile(la, 95) if len(la) else 0
        ref_b = np.percentile(lb, 95) if len(lb) else 0
        out.append(
            {
                "join": i,
                "silenceMs": round(tail + head),
                "tailMs": round(tail),
                "headMs": round(head),
                "endEdgeDb": round(float(la[-1] - ref_a), 1) if len(la) else None,
                "startEdgeDb": round(float(lb[0] - ref_b), 1) if len(lb) else None,
            }
        )
    return out


def long_pauses(x, rate, min_ms=350):
    lv = frames_db(x, rate)
    res, c = [], 0
    for v in lv:
        if v < SIL_DB:
            c += 1
        else:
            if c * WIN * 1000 >= min_ms:
                res.append(round(c * WIN * 1000))
            c = 0
    return res


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def cer(ref, hyp):
    r, h = norm(ref).replace(" ", ""), norm(hyp).replace(" ", "")
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / max(1, len(r))


ACCENTED = [
    "città",
    "università",
    "perché",
    "così",
    "già",
    "venerdì",
    "identità",
    "caffè",
    "tiramisù",
    "più",
    "sì",
    "durerà",
]

model = None


def transcribe(path):
    global model
    if model is None:
        from faster_whisper import WhisperModel

        model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
    segs, _ = model.transcribe(str(path), language="it", beam_size=5, vad_filter=False)
    return " ".join(s.text.strip() for s in segs)


report = {}
for jf in sorted(root.glob("*.json")):
    if jf.name.startswith("analysis"):
        continue
    d = json.loads(jf.read_text())
    v = d["voice"]
    rows = []
    for r in d["results"]:
        if not r.get("wav"):
            continue
        x, rate = read(r["wav"])
        row = {"case": r["case"], "rep": r["rep"], "durMs": round(len(x) / rate * 1000)}
        segs = r.get("segmentSamples") or []
        if len(segs) > 1:
            row["joins"] = boundary_report(x, rate, segs)
        row["pausesMs"] = long_pauses(x, rate)
        row["leadSilenceMs"] = run_silence(frames_db(x, rate), 0, 1)
        if r["case"] in asr_cases and r["rep"] == 1:
            ref = d["texts"][r["case"]]
            hyp = transcribe(r["wav"])
            row["asr"] = hyp
            row["cer"] = round(cer(ref, hyp), 3)
            row["accentedHeard"] = [w for w in ACCENTED if w in ref.lower() and w in hyp.lower()]
            row["accentedMissed"] = [w for w in ACCENTED if w in ref.lower() and w not in hyp.lower()]
        rows.append(row)
    report[v] = rows
(root / "analysis.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
print(json.dumps(report, ensure_ascii=False)[:200])
