# Audio fixtures

These files are checked in so speech tests do not need a microphone.

| File | Contents |
| --- | --- |
| `en_hello.wav` | English speech, 22050 Hz: "Hello. Can you help me?" |
| `en_hello.webm` | The same English line as WebM/Opus. |
| `it_ciao.wav` | Italian speech: "Ciao. Come stai?" |
| `silence_1s.wav` | One second of digital silence. |
| `tone_440hz.wav` | A 440 Hz tone with no speech. |

`en_hello.wav`, `en_hello.webm`, and `it_ciao.wav` were synthesized with espeak-ng for repeatable CPU tests. They are not recordings of a person. Whisper Tiny may change punctuation. Tests compare normalized words.
