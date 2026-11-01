# Meta Quest voice checklist

This checklist was **not** executed on a Quest headset or with Air Link during the batch STT implementation. Passing automated WAV/WebM tests does not prove headset compatibility.

Use a physical Quest 3, an HTTPS Avatar page, and a SonicAgent deployment whose `/health/ready` reports `ready: true`.

## Before the headset

- [ ] `SONIC_API_KEY` is set only on OllaBridge or the Space secrets, not in the Avatar bundle.
- [ ] Capabilities show `stt.ready: true` and languages `en`, `es`, `fr`, `de`, `it`, and `pt`.
- [ ] `tts.ready` is false unless a real Piper voice was installed and a WAV response was played on a desktop.
- [ ] The LLM used for the reply is reachable with the Windows PC powered off, if that is the mode under test.
- [ ] Private-voice mode does not fall back to browser `SpeechRecognition`.

## Quest Browser, 2D page

- [ ] Microphone permission is requested from a user gesture.
- [ ] Denying permission leaves typed chat usable and does not show a stuck listening state.
- [ ] Push-to-talk records with `getUserMedia` and stops when released, including when permission is still pending.
- [ ] An English utterance returns one transcript and one chat turn.
- [ ] An Italian utterance returns one transcript and one chat turn.
- [ ] Silence or a failed upload does not send an empty or duplicate chat message.
- [ ] Backgrounding the browser or ending the page closes the microphone track.

## Immersive WebXR VR

- [ ] Controller push-to-talk uses the same capture path as the 2D microphone button.
- [ ] Releasing the controller before `getUserMedia` resolves does not start a late recording.
- [ ] Entering and leaving immersive mode does not leave the mic open.
- [ ] Lip-sync, animation, and controller input still work when voice is idle.

## Mixed reality / AR, where the browser supports it

- [ ] AR placement is unchanged.
- [ ] The microphone button or controller still records through the shared capture owner.
- [ ] Headset visibility changes stop or recover recording without a duplicate transcript.

## Quest 3 Air Link and Windows Chrome

- [ ] Windows sound settings show the microphone Meta Link actually exposes. This is not guaranteed.
- [ ] Chrome's site permission and input device match that microphone.
- [ ] The recording level moves while speaking.
- [ ] A WebXR session still renders while a short recording is uploaded.

Record the Quest OS version, browser version, SonicAgent model id, and whether the route was local Docker or the Hugging Face Space. Do not mark a row passed from a desktop emulator.
