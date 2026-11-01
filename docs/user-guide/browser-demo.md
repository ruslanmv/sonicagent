# Voice Studio

Voice Studio is the page that runs. Open it on the voice image at `http://127.0.0.1:8000/` or on the Space [ruslanmv/SonicAgent](https://huggingface.co/spaces/ruslanmv/SonicAgent).

## Listen

Press the microphone and speak. Transcription starts when you stop. You do not press a second button for the first pass. The button becomes "Transcribe again" if you want another pass on the same recording.

The public demo does this only when `SONIC_PUBLIC_DEMO_ENABLED` is on. Otherwise paste the bearer token into the page. The token stays in that tab.

## Speak

Choose a language. The list shows only that language. Italiano is Paola and Riccardo. Español is the Spanish voices. Companion and Secretary are the female presets. Male speakers stay labeled male.

Press the card control to play a saved example, or generate a line. Playback stays on that card. There is no separate player bar.

## The other browser page

`make dev` also serves `http://localhost:5173`. That page is the unfinished realtime client. It is not Voice Studio, and it does not run a live turn.
