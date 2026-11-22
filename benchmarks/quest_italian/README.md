# Italian streaming bench (Quest client path)

Measures SonicAgent's Italian voices over the path the Meta Quest 3 client uses today, on one
machine:

```text
headless Chromium: the 3D Avatar Chatbot's own src/tts modules, unmodified
  RemoteSonicAgentTTS.speak / streamReply → PhraseSpeechScheduler → shared voice link
  → AudioJitterBuffer (per phrase) → StreamingAudioPlayer (AudioWorklet, 48 kHz like Quest Browser)
→ OllaBridge Cloud's real voice router (ollabridge_bench.py; only the caller lookup is patched)
→ SonicAgent (this repo) with real Piper, pinned to 2 cores like the free HF CPU Space
```

It is **desktop + server** measurement. It does not replace a run in the Quest Browser on a
headset: Quest's CPU, audio stack and Wi-Fi are not modelled, and the loopback network adds no
latency. Label results accordingly.

## What one run measures, per voice

A fresh SonicAgent process per voice, then:

| Case | What |
| --- | --- |
| `cold` | first reply of a fresh process, model not loaded, no client `warm` call |
| `short1`, `short2`, `medium`, `numbers`, `long` | warm replies through `speak()` (the Quest default; "speak while streaming" is off by default), `REPS` times (default 3) |
| `stream-long` | the long reply arriving as LLM tokens every 45 ms (`streamReply`, HV5) |
| `interrupt` / `after-interrupt` | `stop()` 1.5 s into the long reply, then the next short reply 300 ms later |

Per turn: first frame received, first **audible** sample (worklet `started`), end of playback,
server first-audio / synth time / RTF per phrase (`metrics.turn`), worklet underruns and their
measured length (the `underrun` message to the next `push`), and frames that arrived after a
stop. The PCM SonicAgent delivered is saved per turn as WAV.

`analyze.py` then measures silence at every phrase join, edge energy (a clipped syllable ends
loud), long pauses inside a phrase, and transcribes `medium`, `numbers` and `long` with
faster-whisper small (Italian) for a character error rate and the accented words heard.
`phonemize.py` shows how espeak-ng (Piper's front end, the same for every Italian voice) reads
numbers, dates and abbreviations.

## One-time setup (a cloud session with all three repositories)

```bash
# SonicAgent with Piper and faster-whisper
cd sonicagent && uv venv .venv -p 3.13 && . .venv/bin/activate
uv pip install -e ".[dev]" piper-tts==1.8.0 onnxruntime numpy "faster-whisper>=1.2.1,<1.3" "av>=13,<20"
python benchmarks/quest_italian/fetch_voices.py --cache /tmp/sonic-it-bench/sa-cache \
  it_IT-paola-medium it_IT-serena-high it_IT-aurora-medium it_IT-giorgio-high it_IT-riccardo-x_low
deactivate
# OllaBridge Cloud
cd ../ollabridge-cloud && uv venv .venv -p 3.13 && . .venv/bin/activate && uv pip install -e . && deactivate
```

Riccardo x_low is the process's default voice, so the four voices under test start cold.
Playwright and Chromium are preinstalled in Claude Code cloud containers (`NODE_PATH=$(npm root -g)`).

## Run

```bash
export AVATAR_DIR=/home/user/3D-Avatar-Chatbot OLLABRIDGE_DIR=/home/user/ollabridge-cloud
benchmarks/quest_italian/run_all.sh baseline '{}'                       # ~25 min, four voices
.venv/bin/python benchmarks/quest_italian/analyze.py baseline           # ~5 min (Whisper small)
node benchmarks/quest_italian/summarize.cjs baseline                    # Markdown table
```

Change one variable at a time and rerun the same cases under a new label:

- a **client** setting: the JSON is merged into `nexus_sonic_voice`, e.g.
  `run_all.sh jitter200 '{"jitterMs":200}'`;
- a **server** setting: export it first, e.g.
  `SONIC_MAX_OUTBOUND_QUEUE_MS=3000 run_all.sh queue3000 '{}'`;
- a **code** change: check it out in the relevant repository and rerun.

`node summarize.cjs baseline <label>` prints both tables and the before/after delta.
Results go to `benchmarks/results/quest_italian/` (gitignored); publish a snapshot under
`benchmarks/reports/` only from a real run.

Ports (`SA_PORT` 8701, `OB_PORT` 8702, `WWW_PORT` 8090), the cores (`SA_CPUS`), the work
directory (`WORK`) and the model cache (`SA_CACHE`) can be overridden from the environment.
