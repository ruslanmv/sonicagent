# Working in SonicAgent

Standing notes for coding sessions, verified on 2026-11-22 against this tree. If
something here is wrong, fix it in the same change.

SonicAgent is a server-side voice gateway (FastAPI): microphone PCM over a
binary WebSocket → VAD → faster-whisper → (optional LLM) → Piper phrases → PCM
back, with interruption. The 3D Avatar Chatbot uses it as speech only, through
OllaBridge Cloud (`/v1/voice/*` → SonicAgent `/v1/audio/*`), including on Meta
Quest 3. The public deployment is the Hugging Face Space `ruslanmv/SonicAgent`
(2 vCPU `cpu-basic`).

## Set up and check

```bash
uv venv .venv -p 3.13 && . .venv/bin/activate
uv pip install -e ".[dev]" piper-tts==1.8.0 onnxruntime numpy "faster-whisper>=1.2.1,<1.3" "av>=13,<20"
python -m pytest -q tests hf/tests        # 175 passed, 22 skipped on 2026-11-22
ruff check . && ruff format --check <files you touched>
```

- `pyproject.toml` sets pytest `pythonpath = ["src", "."]`, which is put **before**
  `PYTHONPATH`. To test the old code against a new test, check the old file out
  in that tree; `PYTHONPATH=<other>/src pytest` silently tests this tree.
- `hf/tests/test_deployment_config.py` was not ruff-formatted before 2026-11-22;
  format only what you touch.

## Where things are

| Path                                     | What                                                                                                                          |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `src/sonicagent_rt/api/websocket/speech_endpoint.py` | the speech-only socket the Avatar uses: `tts.speak` queue (`tts_queue`), pacing (`max_outbound_queue_ms`), acks, cancel |
| `src/sonicagent_rt/tts/piper_process.py` | Piper: models keyed by file, one sentence per `iter_pcm` chunk                                                                |
| `model_registry/voices.json`             | every selectable voice, SHA-256 pinned, licence + `attribution` for non-MIT                                                   |
| `hf/`                                    | the Space: `Dockerfile`, `ui/` (Voice Studio), `scripts/` (setup, prepare, upload, deploy)                                    |
| `benchmarks/quest_italian/`              | streaming bench over the Quest client's real path (its README)                                                                |
| `docs/api/speech-stream.md`              | the stream protocol and its options                                                                                           |

## Voice files: the mirror is the only source

`ruslanmv/hp-piper-voices` holds every voice file; the registry names no other
source (`hf/tests/test_setup_models.py`). Adding a voice:

1. Get the exact upstream bytes; note the upstream repo, revision and licence.
2. `HF_TOKEN=… python hf/scripts/mirror-add-voices.py --files <dir> <voice-id>`
   (dry run), then `--push`: additive only, SHA-checked against the registry,
   one commit pinned to the mirror head, a `MODEL_CARD` for non-MIT voices. The
   registry entry must exist locally first (the script reads its SHA-256s).
3. Registry entry (`voices.json`, with `attribution` for non-MIT voices:
   test-enforced; credits live there, in `catalog/README.md` and the mirror's
   `MODEL_CARD`, not on Voice Studio's cards, by the owner's choice),
   `hf/ui/catalog.json`, a preview WAV made with `hf/scripts/make-previews.py`
   (audition sentences first; a lone opening "Ciao." garbled both Piper
   Italiano voices) in `hf/ui/examples/<id>.wav`, `catalog/README.md`, the voice-count test in
   `tests/contract/test_model_manifest.py`.
4. Update the mirror's `README.md` (count, language rows, licence table) as its
   own reviewed commit; it is not additive.
5. `node hf/scripts/voice-studio-shot.cjs <locale> <out>` and look at both
   frames.

## Deploying the Space

Canonical: push to `main`/`master` runs `.github/workflows/huggingface-space.yml`.
To try a branch on the live Space before merging:

```bash
HF_TOKEN=… python hf/scripts/space-deploy.py                 # preview: NEW / CHANGED / DELETED, rollback commit
HF_TOKEN=… python hf/scripts/space-deploy.py --push --check it_IT-aurora-medium
```

`upload-space.py` mirrors the staged tree, so a remote file missing from the
stage is deleted: read the preview. The build takes ~2–3 minutes. The public
demo is off (`/demo/speech` → 403), so synthesis is tested by a person in Voice
Studio's token mode. Bump `?v=` in `hf/ui/index.html` when `app.js` or
`style.css` change, and `PREVIEWS_V` in `app.js` when a preview WAV changes
(previews are fetched with `force-cache`; same URL = the old recording).

## Italian voices on the Quest path (measured 2026-11-22)

`benchmarks/quest_italian/` (desktop Chromium running the Avatar's own modules →
OllaBridge → SonicAgent pinned to 2 cores; desktop + server numbers, not a
headset). Medians, ms to first audible sample:

| Voice         | Cold | Warm short · medium · numbers · long | RTF   | Gaps                       | Notes                                                    |
| ------------- | ---- | ------------------------------------ | ----- | -------------------------- | -------------------------------------------------------- |
| Paola Medium  | 1071 | 107 · 296 · 473 · 129                | 0.056 | none                       | clear; reads "dott." badly                               |
| Serena High   | 1680 | 403 · 1298 · 2090 · 576              | 0.246 | 45–627 ms (fixed, below)   | best prosody; ~5× slower, the only real "high" model     |
| Aurora Medium | 963  | 125 · 382 · 528 · 185                | 0.045 | none                       | worst ASR, long mid-sentence pauses (40 s vs 26 s)       |
| Giorgio High  | 879  | 94 · 352 · 542 · 166                 | 0.049 | none                       | medium-size model despite "high"; clear, slow            |

What the numbers mean for changes:

- First audio = the whole first Piper **sentence** (Piper yields per sentence),
  so it scales with the first sentence's length × RTF.
- Gaps: the next phrase used to be synthesized only after the current phrase's
  last frame was sent, with `max_outbound_queue_ms` (2000) of audio left on the
  client. Fixed by synthesizing one sentence/phrase ahead while pacing
  (`_look_ahead`, `_pull_ahead` in `speech_endpoint.py`; tests in
  `tests/unit/test_speech_stream_hardening.py`): Serena High on one core went
  from 30 underruns to 1. Do not raise the budget instead: OllaBridge's relay
  queue holds 64 messages and closes the socket (1013) when full.
- Report: `benchmarks/reports/quest3-italian-streaming.md`.
- Italian text goes to espeak-ng unchanged: `12,50 €` → "dodici virgola
  cinquanta euro", `24/12/2026` → "… barra …", `l'1 maggio` → "elle uno",
  `°C` → "gradi ci", `dott.` ends a sentence. Same for every voice
  (`python benchmarks/quest_italian/phonemize.py <model.onnx>`).

## Rules

- Never commit model files, `dev.db`, or `benchmarks/results/` (gitignored).
- Never print or commit a token; scripts read `HF_TOKEN` from the environment.
- Do not edit a shell script while it is running (bash reads it as it goes; a
  bench run was corrupted that way).
