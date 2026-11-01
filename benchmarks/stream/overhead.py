"""Per-second cost of streamed Piper audio on the speech-only socket (HV3).

Counts what the socket actually sends for one second of speech in each
negotiable framing, using the real frame encoder and the real JSON event, so
the numbers are the protocol's, not an estimate. It measures bytes and
WebSocket messages, not latency: how much a headset's network and event loop
handle per second of her voice. Latency needs a live run (see
``benchmarks/endpoints``) and a headset.

    python -m benchmarks.stream.overhead
"""

from __future__ import annotations

import json

from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, encode_frame
from sonicagent_rt.protocol.constants import Codec, MessageType

#: Piper "medium" voices are 22050 Hz; "low"/"x_low" are 16000.
RATES = (22050, 16000)


def per_second(rate: int, frame_ms: int, chunk_events: bool) -> dict[str, float]:
    samples = int(rate * frame_ms / 1000)
    frames = 1000 / frame_ms
    binary = len(
        encode_frame(
            BinaryAudioFrame(
                message_type=int(MessageType.AUDIO_OUTPUT),
                codec=int(Codec.PCM16),
                flags=0,
                sample_rate=rate,
                sequence=123456,
                timestamp_us=123456 * frame_ms * 1000,
                payload=b"\x00\x00" * samples,
            )
        )
    )
    event = 0
    if chunk_events:
        event = len(
            json.dumps(
                {
                    "type": "tts.audio.chunk",
                    "turn_id": "turn_" + "0" * 32,
                    "sequence": 123456,
                    "sample_rate": rate,
                    "timestamp_us": 123456 * frame_ms * 1000,
                    "bytes": samples * 2,
                    "t_ms": 123456,
                }
            ).encode()
        )
    payload = samples * 2
    total = (binary + event) * frames
    return {
        "messages_per_s": frames * (2 if chunk_events else 1),
        "bytes_per_s": round(total),
        "overhead_pct": round(100 * (total - payload * frames) / total, 2),
    }


def table() -> list[tuple[str, int, dict[str, float]]]:
    rows = []
    for rate in RATES:
        for frame_ms, events, label in (
            (20, True, "v1 default"),
            (20, False, "no chunk events"),
            (40, False, "40 ms, no chunk events"),
        ):
            rows.append((label, rate, per_second(rate, frame_ms, events)))
    return rows


def main() -> None:
    print("| framing | Piper rate | messages/s | bytes/s | overhead |")
    print("| --- | --- | --- | --- | --- |")
    for label, rate, row in table():
        print(
            f"| {label} | {rate} Hz | {row['messages_per_s']:.0f} | {row['bytes_per_s']} | {row['overhead_pct']}% |"
        )


if __name__ == "__main__":
    main()
