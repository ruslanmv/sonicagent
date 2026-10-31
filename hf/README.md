# SonicAgent voice image

This directory deploys the same SonicAgent speech service in two places:

1. A Windows or Linux PC, with Docker Desktop or Docker Engine.
2. The existing Hugging Face Docker Space `ruslanmv/SonicAgent`.

The inference code stays in `src/sonicagent_rt`. Nothing in `hf/` is a second speech engine. The image listens on `0.0.0.0:7860`. Local Compose publishes that port on the host as `8000`.

The default model is multilingual Whisper Tiny through `faster-whisper` and CTranslate2, CPU INT8. English-only checkpoints such as `tiny.en` are rejected because Italian is required. Speech synthesis with Piper is optional and is off until voice files are installed and `SONIC_TTS_ENABLED=true`.

Hugging Face is a remote CPU host. It is not on-device inference and it is not an offline Quest mode. A Space can sleep, cold-start, and run out of memory. This repository does not claim the Space is always on.

## 1. Windows with Docker Desktop

Install Docker Desktop and leave it running. In PowerShell, from the SonicAgent repository:

```powershell
Copy-Item hf\.env.example hf\.env
# Edit hf\.env and set SONIC_API_KEY to a private value of at least 16 characters.
notepad hf\.env
.\hf\scripts\run-local.ps1
```

Or, without the script:

```powershell
$env:SONIC_API_KEY = "replace-with-a-private-local-key"
docker compose -f hf/docker-compose.yml up --build
```

The first build downloads the pinned `tiny` checkpoint into the image. Later starts reuse the `sonicagent-models` volume.

Local API: `http://127.0.0.1:8000`

Container listen address: `0.0.0.0:7860`

Change the host port with `SONIC_PUBLISH_PORT` in `hf/.env`. Do not commit `hf/.env`.

## 2. Linux

From the repository root:

```bash
cp hf/.env.example hf/.env
# Set SONIC_API_KEY in hf/.env (16+ characters for local development).
chmod +x hf/scripts/*.sh
./hf/scripts/build-local.sh
./hf/scripts/run-local.sh
```

The equivalent Compose command is:

```bash
docker compose -f hf/docker-compose.yml up --build
```

## 3. Whisper model selection

| Size | Use |
| --- | --- |
| `tiny` | Default. Multilingual. Fits a small CPU host. English and Italian. |
| `base` | Optional larger multilingual checkpoint. Not bundled. Checksum is not pinned yet. |
| `tiny.en`, `base.en` | Rejected. They cannot transcribe Italian. |

Environment variables, using the existing `SONIC_` prefix:

```env
SONIC_STT_PROVIDER=faster-whisper
SONIC_STT_MODEL=tiny
SONIC_STT_DEVICE=cpu
SONIC_STT_COMPUTE_TYPE=int8
SONIC_STT_LANGUAGE=auto
SONIC_STT_ALLOW_DOWNLOAD=false
SONIC_STT_WARMUP=true
```

`auto` detects English or Italian. A request may also send `language=en` or `language=it`.

Requests never download weights. Warmup downloads only when `SONIC_STT_ALLOW_DOWNLOAD=true`. The Hugging Face image bundles Tiny at build time and sets download to false, so a restart does not depend on Hugging Face Hub being reachable. The trade-off is a larger image and a rebuild when the pinned revision changes. The pin is repository `Systran/faster-whisper-tiny`, revision `d90ca5fe260221311c53c58e660288d3deb8d356`.

Install or refresh the cache without Docker:

```bash
python hf/scripts/setup-models.py --model tiny --cache-dir ~/.cache/sonicagent-rt
```

The script skips a download when `model.bin` and `tokenizer.json` are already present and the Tiny checksum matches. It does not substitute another size. `base` and `small` are listed in `model_registry/stt_models.json` as metadata only. Do not advertise them as ready unless that exact checkpoint is loaded. `/health/ready` reports the loaded model id, which is `whisper-tiny` for the default.

GPU (`SONIC_STT_DEVICE=cuda` or `gpu`) is accepted only when CTranslate2 reports a CUDA device. `auto` stays on CPU unless CUDA is present. The published image is CPU-only.

## 4. Test speech-to-text

Wait until readiness is true. Live only means the process is listening.

```bash
curl -sS http://127.0.0.1:8000/health/live
curl -sS http://127.0.0.1:8000/health/ready
```

`ready` is true only after Whisper is loaded. A loading model returns `ready: false` and `missing: ["stt"]`.

English WAV:

```bash
curl -sS -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -F "file=@tests/fixtures/audio/en_hello.wav" \
  -F "language=en" \
  -F "request_id=utt_en" \
  http://127.0.0.1:8000/v1/audio/transcriptions
```

Italian WAV:

```bash
curl -sS -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -F "file=@tests/fixtures/audio/it_ciao.wav" \
  -F "language=it" \
  http://127.0.0.1:8000/v1/audio/transcriptions
```

WebM/Opus, the format Quest and Chrome `MediaRecorder` usually produce:

```bash
curl -sS -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -F "file=@tests/fixtures/audio/en_hello.webm;type=audio/webm" \
  -F "language=en" \
  http://127.0.0.1:8000/v1/audio/transcriptions
```

The `audio` field name is accepted as an alias of `file`. A successful body looks like:

```json
{
  "text": "Hello. Can you help me?",
  "language": "en",
  "model": "whisper-tiny",
  "is_final": true,
  "request_id": "utt_en",
  "duration_ms": 2854
}
```

Tiny is small. Expect occasional wording differences, especially on Italian. An empty `text` means the recording was silent or below the RMS threshold. It is not a fake transcript. Silence is returned only when the engine itself is available. If the model is not loaded, the same request returns HTTP 503.

Capability discovery:

```bash
curl -sS -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  http://127.0.0.1:8000/v1/audio/capabilities
```

`stt.available` means the library and configured model can be used. `stt.ready` means the weights are loaded. `tts.available` stays false until Piper is actually installed. `realtime` stays `not-implemented`.

There is no separate local and hosted transcription schema.

## 5. Optional Piper speech synthesis

Piper is not enabled in the default image. The endpoint exists and returns HTTP 503 `voice_unavailable` until all of the following are true:

- `piper-tts` is installed in the environment.
- `SONIC_TTS_ENABLED=true`.
- The voice ONNX file and its JSON config are in the model cache.
- The voice id is one of `en_US-lessac-medium` or `it_IT-paola-medium`.

Download the two voices explicitly:

```bash
python hf/scripts/setup-models.py --model tiny --tts --cache-dir ~/.cache/sonicagent-rt
```

Those files come from `rhasspy/piper-voices`. Review their license before redistributing them. This image does not bundle them, because the STT milestone does not depend on TTS and the extra files increase the Space image.

Request:

```bash
curl -sS -D - -o reply.wav \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello! Welcome to our virtual world.","voice":"en_US-lessac-medium","language":"en","format":"wav"}' \
  http://127.0.0.1:8000/v1/audio/speech
```

A working response is `audio/wav`. Text is limited by `SONIC_TTS_MAX_CHARS` (default 2000). This does not replace Piper inside the 3D Avatar Chatbot. Remote synthesis is an optional alternative.

Real Piper output was not verified in the implementation environment that produced this package. Treat TTS as unavailable until a WAV from this endpoint plays.

## 6. Authentication

Every transcription, speech, and capabilities call requires:

```http
Authorization: Bearer <SONIC_API_KEY>
```

Rules:

- No default key is compiled into the image or the repository.
- Placeholder values such as `development-token` and `change-me` are rejected.
- Local development (`SONIC_AUTH_MODE=development`) requires at least 16 characters.
- Production, and any `SONIC_AUTH_MODE=token` deployment, requires at least 24 characters.
- `SONIC_ALLOWED_ORIGINS=*` is ignored. Browser calls must use an explicit origin. Server-to-server calls that omit `Origin` are allowed after the bearer check.
- Credentials are not attached to CORS responses.

```env
SONIC_AUTH_MODE=token
SONIC_API_KEY=
SONIC_ALLOWED_ORIGINS=
SONIC_MAX_AUDIO_SECONDS=15
SONIC_MAX_UPLOAD_BYTES=2097152
SONIC_STT_MAX_CONCURRENCY=2
SONIC_STT_RATE_LIMIT_PER_MINUTE=60
```

Audio and transcripts are not written to disk. Logs record the result code, request id, and durations, not the transcript text and not the microphone bytes.

Public routes are `GET /`, `GET /health/live`, `GET /health/ready`, and `GET /metrics`. They do not include the API key, model filesystem path, or transcript text. Do not treat HTTP 200 from `/health/live` as proof that transcription works.

## 7. Deploy the existing Space

The Space already exists at `https://huggingface.co/spaces/ruslanmv/SonicAgent`. Do not create another Space.

Dry run, from the repository root. This builds a temporary staging directory and does not upload anything:

```bash
hf/scripts/deploy-space.sh
```

```powershell
.\hf\scripts\deploy-space.ps1
```

The staging copy includes the Dockerfile, `app.py`, `requirements.txt`, `src/sonicagent_rt`, `model_registry`, and the health check. `hf/README.space.md` becomes the Space root `README.md`. The GitHub `README.md` is left unchanged. The staging copy excludes `.git`, `.env`, credentials, test recordings, egg-info, and caches.

## 8. Hugging Face CLI or Git, without pasting a token

Install the official CLI and log in on your own machine. The login stores the credential in the Hugging Face credential store. Do not paste the token into a script, a commit, a chat, or `hf/.env`.

```bash
hf auth login
hf auth whoami
hf/scripts/deploy-space.sh --push
```

```powershell
hf auth login
hf auth whoami
.\hf\scripts\deploy-space.ps1 -Push
```

The upload command the script runs is:

```bash
hf upload ruslanmv/SonicAgent STAGING_DIR . --repo-type=space --commit-message "Deploy SonicAgent voice service"
```

It does not pass `--delete`, so files outside the managed set are left in place.

Git alternative, after you have cloned the Space with your own credentials:

```bash
git clone https://huggingface.co/spaces/ruslanmv/SonicAgent /tmp/sonicagent-space
python hf/scripts/prepare-space.py --dest /tmp/sonicagent-space
cd /tmp/sonicagent-space
git status
git add Dockerfile README.md app.py requirements.txt setup-models.py pyproject.toml src model_registry deploy .dockerignore
git commit -m "Deploy SonicAgent voice service"
git push
```

If `hf auth whoami` fails, stop. The dry run is still valid. Finish the login locally and rerun `--push`. This repository cannot authenticate for you.

## 9. Space secrets

In the Space settings, add repository secrets. Do not put them in `README.md` or in the Dockerfile.

| Secret | Value |
| --- | --- |
| `SONIC_API_KEY` | Private random string, 24 characters or more. |
| `SONIC_ALLOWED_ORIGINS` | The Avatar origin, if a browser calls SonicAgent directly. Leave unset when only OllaBridge calls the Space. |

The image already sets `SONIC_ENVIRONMENT=production` and `SONIC_AUTH_MODE=token`. An empty `SONIC_API_KEY` makes authenticated routes return 401. That is intentional. OllaBridge Cloud must store the same secret server-side. The Quest browser must never see it.

## 10. Build logs and runtime errors

On the Space page, open **Logs** and then the **Build** and **Container** tabs.

- Build failure while running `setup-models.py` means the pinned Tiny download or checksum failed. Do not switch the Dockerfile to an unpinned model to hide that.
- Container starts while `/health/ready` is false during warmup. Wait, then read `reason` (`model-loading`, `model-not-loaded`, `library-missing`).
- HTTP 401: missing or short bearer token.
- HTTP 413: upload or duration over the limit.
- HTTP 415: unsupported or undecodable audio.
- HTTP 422: empty or corrupt audio.
- HTTP 503 with `Retry-After`: model still loading or missing.
- HTTP 504: inference exceeded `SONIC_STT_TIMEOUT_SEC`.

The Docker `HEALTHCHECK` calls `/health/live` through `deploy/docker/healthcheck.py`, using `PORT` (7860 in this image). A healthy container can still be `ready: false`.

## 11. Test the hosted API

After the Space build is green, Hugging Face shows the application URL on the Space page. Use that hostname. Do not assume a URL that has not been opened successfully.

```bash
curl -sS "https://YOUR_SPACE_HOST/health/ready"
curl -sS -H "Authorization: Bearer YOUR_SPACE_SECRET" \
  -F "file=@tests/fixtures/audio/en_hello.wav" \
  -F "language=en" \
  "https://YOUR_SPACE_HOST/v1/audio/transcriptions"
```

A live check without a transcription does not prove the model works. If the Space is asleep, the first request can fail or hang while the container starts. Report that as warming, and retry `/health/ready` before sending audio.

## 12. OllaBridge Cloud as the caller

OllaBridge should select one voice backend:

| Mode | Behavior |
| --- | --- |
| `local` | The paired PC is on. OllaBridge calls SonicAgent at `http://127.0.0.1:8000`. |
| `huggingface` | The PC may be off. OllaBridge calls the Space directly with the server-side bearer token. |
| `disabled` | No speech route. Typed chat still works. |

The contract is documented in `docs/integrations/ollabridge-huggingface-voice.md`. The existing OllaBridge Hugging Face chat provider is not this API. Do not post microphone audio to the chat-completions stub.

When the PC is off, chat still needs an online LLM configured in OllaBridge Cloud. SonicAgent does not call that model and will not invent a chat reply inside `/v1/audio/transcriptions`. If transcription succeeds and the LLM is down, OllaBridge should return that LLM error rather than a fake assistant line.

## 13. Meta Quest microphone uploads

The Avatar page must be HTTPS. Call `getUserMedia` from a user gesture. Quest will not grant the microphone automatically.

```javascript
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  }
});
const recorder = new MediaRecorder(stream);
```

Send one bounded recording, preferably WebM/Opus or WAV, as `multipart/form-data` to OllaBridge. OllaBridge forwards that file to SonicAgent. Keep the clip within 15 seconds and 2 MiB. Do not stream continuous PCM through the JSON device relay. Do not use `webkitSpeechRecognition` and describe it as SonicAgent.

This path is the intended one for Quest 3 Browser, Quest WebXR, Quest mixed-reality browser sessions when the platform exposes a microphone, desktop Chrome, and Windows Chrome with Quest Air Link. Air Link does not guarantee the right input device. Check the Windows recording device and the browser input picker.

No physical headset test has been run for this change. The checklist in `docs/qa/quest-voice-manual-checklist.md` is still unchecked.

## 14. Roll back a failed deployment

The Space is a Git repository. On your machine:

```bash
git clone https://huggingface.co/spaces/ruslanmv/SonicAgent
cd SonicAgent
git log --oneline
git revert HEAD
git push
```

Or check out the last known good commit and push that. Hugging Face rebuilds from the new Space commit. Do not force-push unless you intend to discard the failed commit. The SonicAgent GitHub branch is independent. Reverting the Space does not revert the GitHub pull request.

## 15. Choose local mode or Hugging Face mode

Use local Docker while developing and while the Windows PC will stay on. The API, auth header, limits, and response JSON are the same as the Space.

Use the Space when the headset should work with the PC switched off. That still requires:

- a built Space whose `/health/ready` is true,
- `SONIC_API_KEY` stored as a Space secret and in OllaBridge,
- an online LLM in OllaBridge Cloud,
- and the OllaBridge voice route from the contract doc, which is not in this repository yet.

GPU acceleration, WebSocket audio, and verified Piper output are later work. They are not implied by a successful Tiny transcription.

## 11. Voice Studio web interface

This image now serves a responsive web UI at `/` for **both** Docker Desktop
(`http://localhost:8000/`) and the existing Hugging Face Space
(`https://huggingface.co/spaces/ruslanmv/SonicAgent`).

The original root JSON discovery response is preserved at `/api-info`.
Existing `/docs`, `/health/*`, and `/v1/audio/*` endpoints keep their original
contracts.

Features: server/Whisper/Piper readiness, Quest/desktop microphone recording,
WebM/Opus or OGG/Opus uploads, WAV/audio uploads, English/Italian/auto STT,
copyable transcript, and Piper WAV synthesis/playback when available.

### Owner / service-token testing

By default transcription and TTS remain protected by `SONIC_API_KEY`.
The interface provides an **API token** panel for private testing only. The
token remains in browser tab memory; it is never embedded in source or saved
to localStorage. Use private trusted browsers and avoid pasting production
service credentials on shared machines. The browser still sends that token
in the Authorization header to your Space.

For browser token mode configure `SONIC_ALLOWED_ORIGINS` with the **exact**
origin of your Space app, normally
`https://ruslanmv-sonicagent.hf.space`, and any explicitly trusted local
origins. The backend rejects unlisted Origin values.

### Optional anonymous public demo

Owners can let Hugging Face visitors try short speech samples without
sharing their private API token. In Space Settings → Variables, set:

```env
SONIC_PUBLIC_DEMO_ENABLED=true
SONIC_PUBLIC_DEMO_TTS_ENABLED=false
```

**Public inference is off by default.** Anonymous STT has strict limits:
8 seconds, 1.2 MiB, one in-flight demo, 8 requests/minute globally and
3 requests/minute per observed client. These are single-process best-effort
limits, not a distributed security control; clients behind the Space proxy
may share one apparent IP. Browser-origin checks and custom demo headers
are not authentication, and non-browser clients may still request the
demo endpoints. Disable the public demo if compute resources are abused.
For a widely promoted service, add user authentication, provider quotas,
and a shared rate limiter before opening it publicly.

Anonymous TTS is independently disabled until you set
`SONIC_PUBLIC_DEMO_TTS_ENABLED=true` **and** deploy functioning Piper voice
models. It will otherwise show disabled, rather than fake a voice sample.
Avoid activating demo TTS unless its resource usage is acceptable.

UI routes:

```text
GET  /                        Voice Studio
GET  /ui-assets/style.css     Styles
GET  /ui-assets/app.js        Browser app
GET  /api-info                Original JSON root metadata
GET  /demo/status             Anonymous demo availability
POST /demo/transcriptions     Limited demo STT (optional)
POST /demo/speech             Limited demo TTS (optional)
```

Recordings are submitted **only after** clicking *Transcribe audio*. A Hugging
Face Space processes audio remotely. This is not on-device STT. Microphone
access requires HTTPS (or localhost) and browser permission, including on
Meta Quest.

### Deploy the new UI

The existing `hf/scripts/prepare-space.py` staging script includes
`hf/ui/` and the Dockerfile copies it to `/app/ui`. This avoids a mismatch
between the local Docker image and the hosted Space.

```powershell
# Dry-run first.
python hf/scripts/prepare-space.py --dest ./hf-space-stage
# Then, when your authenticated HF CLI and Space secrets are configured:
hf auth login
.\hf\scripts\deploy-space.ps1 -Push
```

Do not put a production service token into source control or into the Space
README. Test readiness and a **real** audio transcription after deployment.
