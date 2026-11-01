# Speech endpoint capability

One measured pass of the HTTP speech API. This is not a production service level, and it is not a Quest, phone, or glasses test.

- Measured at: 2026-11-01T00:46:40+01:00
- Target: https://ruslanmv-sonicagent.hf.space
- Space stage: RUNNING · hardware: cpu-basic · region: us · runtime sha: 13489f2232797ba6e8ac99b16a7b4940f11c39f3
- Git commit recorded by the probe: da704b9ebd5d903814602556e0ab79aff3f74c2f · dirty: True
- Client: Linux-6.12.94+-x86_64-with-glibc2.39 · Python 3.12.3 · CPUs 4
- Authentication: bearer

The client is a Linux VM calling Hugging Face over HTTPS. A headset on another network would add its own radio and geographic delay. Time to first audio is the time until the entire WAV (or JSON transcript) has arrived. The API does not stream partial audio.

| Series | Samples | Errors | Warmup ms | Total p50 ms | Total p95 ms | Audio p50 ms | RTF p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| health_live_cold | 1 | 0 | — | 38 | 38 | — | — |
| health_live_warm | 20 | 0 | — | 6 | 9 | — | — |
| health_ready | 5 | 0 | — | 8 | 8 | — | — |
| example_wav | 5 | 0 | — | 8 | 9 | 1857 | 0.004 |
| capabilities | 3 | 0 | — | 10 | 10 | — | — |
| tts_en_lessac | 5 | 0 | 87 | 112 | 194 | 626 | 0.183 |
| tts_en_kristin | 5 | 0 | 2400 | 193 | 267 | 1277 | 0.151 |
| tts_it_paola | 5 | 0 | 290 | 183 | 199 | 464 | 0.394 |
| tts_es_sharvard | 5 | 0 | 2016 | 103 | 177 | 394 | 0.272 |
| tts_es_sharvard_male | 5 | 0 | 293 | 107 | 169 | 301 | 0.355 |
| stt_en | 3 | 0 | — | 504 | 509 | — | — |
| stt_it | 3 | 0 | — | 487 | 571 | — | — |

Warmup is the first call and is not included in the percentiles. A cold voice can spend that call loading its model. RTF is client-observed seconds divided by audio seconds. Below 1 means the full clip came back faster than its own duration. The listener still waits for that full clip before playback can start.

## VR, AR, and mobile

A conversational headset needs the first sound soon after the person stops speaking. This deployment answers with one batch request: record, upload, wait, then play. `/health/ready` reports realtime speech as not implemented, so barge-in and phrase-by-phrase playback are not available on this path.

Preset example WAVs are a different path. They are static files. A client can start those lines after a download, without Piper. Generated lines cannot.

CPU Basic is a shared cloud CPU. It can sleep. It is not an on-device mobile runtime and it is not a GPU speech cluster. Use these figures to size the next engine. Do not quote them as the latency of a VR product.

## Recognition

- stt_en: Hello? Can you help me?
- stt_it: Ciao come stai!

## Notes

- Warmup calls are excluded from the percentile rows.
- p99 is omitted when a series has fewer than 20 successful samples.
- The client is not a VR headset, phone, or AR device.
