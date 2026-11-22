"""How Piper's espeak-ng front end reads Italian numbers, dates, units and abbreviations.

This is the same for every Italian voice (it runs before the model), so it separates text
problems from voice problems.

    python benchmarks/quest_italian/phonemize.py /tmp/sa-cache/tts/it_IT-paola-medium.onnx
"""

from __future__ import annotations

import sys

from piper import PiperVoice

CASES = [
    "alle 7:45 dal binario 3",
    "costa 12,50 €",
    "il 25% degli studenti",
    "-3,5 °C",
    "il 24/12/2026",
    "il dott. Rossi arriverà",
    "alle 9:30 c'è",
    "verso le 14:15",
    "l'1 maggio",
]

voice = PiperVoice.load(sys.argv[1])
for text in CASES:
    print(f"{text!r:32} -> {[''.join(p) for p in voice.phonemize(text)]}")
