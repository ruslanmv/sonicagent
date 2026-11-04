# Voice library and speaking profiles (HV9)

SonicAgent speaks with the Piper voices listed in `model_registry/voices.json` (mirror:
`ruslanmv/hp-piper-voices`): 52 voices, 47 model files, 7 locales with documented presets.

## Profiles

The role of a voice picks its synthesis settings (`styles` in the registry):

| Profile | `length_scale` | `noise_scale` | `noise_w_scale` | For |
| --- | --- | --- | --- | --- |
| Companion | 1.16 | 0.8 | 0.92 | warm, slightly slower conversation |
| Secretary / Productivity | 0.94 | 0.48 | 0.6 | clear, slightly faster schedules, lists, reminders |
| Catalog | 1.0 | 0.667 | 0.8 | every other voice, Piper's defaults |

A voice may carry its own scales in its registry entry; they win over the role's. Serena
(`it_IT-serena-medium`, `it_IT-serena-high`) uses 1.0 / 0.6 / 0.4, the settings she was trained
with — her model card says the catalog style swallows phonemes. No other voice has its own scales.

**Added 2026-11:** Serena (Italian, female, medium + high, CC-BY-4.0) and Daniela (Spanish,
Argentina, female, high, CC-BY-SA-4.0). Both are catalog voices under All Voices; Paola stays the
Italian Companion and Secretary, and es-AR has no preset. Their licences require attribution — see
the `attribution` field in `voices.json` and `catalog/README.md`.

Measured with real Piper on the same Paola model, the same Italian sentence: Companion audio is
on average ~15% longer than Secretary (12 single runs: 1.05–1.21). That is less than the nominal
1.16/0.94 because Piper does not stretch every pause.

## Presets (`GET /v1/voices` → `presets`)

| Locale | Companion | Secretary |
| --- | --- | --- |
| en-US | `en_US-kristin-medium` | `en_US-lessac-medium` |
| en-GB | `en_GB-cori-medium` | `en_GB-alba-medium` |
| es-ES | `es_ES-sharvard-companion` (speaker 1) | `es_ES-sharvard-secretary` (speaker 1) |
| es-MX | `es_MX-ald-companion` | `es_MX-ald-medium` |
| fr-FR | `fr_FR-upmc-medium` — Jessica (speaker 0) | `fr_FR-siwis-medium` |
| de-DE | `de_DE-eva_k-x_low` | `de_DE-kerstin-low` |
| it-IT | `it_IT-paola-companion` | `it_IT-paola-medium` |

Brazilian Portuguese has only male voices today (`pt_BR-edresson-low`, `pt_BR-faber-medium`),
so it has no preset; they are listed with the rest under All Voices. A test reads the registry and
fails if a preset is missing, has the wrong role, is not female, or has drifted settings.

## What `GET /v1/voices` adds per voice

`state` (`loaded` | `installed` | `missing`), `playable` (installed and Piper ready — only these
should be offered as selectable), `model_key` and `shares_model_with`.

## One loaded model per ONNX file

Paola Companion/Secretary, Sharvard Companion/Secretary/Male, Ald, and UPMC Jessica/Pierre are
each one model with different settings or speaker ids. The engine keys loaded voices by model
file, and a per-model lock makes two presets asking at once wait for one load. Switching
Companion ↔ Secretary therefore costs no second cold start. Warming one voice never loads the
catalogue.

## On the speech socket

- `tts.speak` takes an optional `voice_id`: a phrase can use another registry voice (a preview,
  a profile switch) without a new session. A voice not in the registry is `voice_unavailable`,
  never a silent substitute.
- `tts.warm` `{voice_id}` → `tts.warmed {voice_id, cold, ms, load_ms}`.
- `tts.started` adds `voice_id`, `role`, `cold`. `metrics.turn` adds `voice_id`, `role`, `cold`,
  `synth_ms` and `rtf` (synthesis time over audio time).

## Measured (`python -m benchmarks.voices.profiles`)

Real Piper 1.8, real files (SHA-256 checked against the registry), this build machine's CPU.
Not a Hugging Face CPU Basic or a Quest number.

| voice | profile | speaker | cold load | model reused | first audio (warm) | RTF | cancel |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `en_US-kristin-medium` | companion | — | 1761 ms | no | 96 ms | 0.058 | 91 ms |
| `en_US-lessac-medium` | secretary | — | 1223 ms | no | 47 ms | 0.059 | 64 ms |
| `it_IT-paola-medium` | secretary | — | 1475 ms | no | 47 ms | 0.055 | 274 ms |
| `it_IT-paola-companion` | companion | — | — | yes | 67 ms | 0.053 | 62 ms |
| `es_ES-sharvard-companion` | companion | 1 | 2089 ms | no | 105 ms | 0.060 | 50 ms |
| `es_ES-sharvard-secretary` | secretary | 1 | — | yes | 61 ms | 0.066 | 259 ms |
| `es_ES-sharvard-male` | catalog | 0 | — | yes | 84 ms | 0.050 | 44 ms |

Seven voices, four model loads. "cancel" is how long synthesis keeps running after it is told to
stop: Piper checks between sentences, so it is at most the sentence in progress. The socket stops
sending at once, so the person hears the cancel immediately; this is server CPU, not audio.
