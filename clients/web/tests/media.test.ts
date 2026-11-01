import { describe, expect, it } from "vitest";
import { PcmQueue } from "../src/audio/audioQueue";
import { floatToPcm16, takeFrames } from "../src/audio/capture";
import { PlaybackClock } from "../src/audio/playback";
import { resampleLinear } from "../src/audio/resampler";
import { nextDelayMs } from "../src/realtime/reconnect";
import { applyControlEvent } from "../src/realtime/realtimeClient";

describe("browser media", () => {
  it("resamples and frames 20 ms blocks", () => {
    const input = new Float32Array(480);
    input.fill(0.5);
    const down = resampleLinear(input, 48000, 16000);
    expect(down.length).toBe(160);
    const { frames, rest } = takeFrames(new Float32Array(), down, 160);
    expect(frames).toHaveLength(1);
    expect(rest.length).toBe(0);
    expect(floatToPcm16(frames[0]!).length).toBe(320);
  });

  it("drops old audio under backpressure and clears on cancel", () => {
    const clock = new PlaybackClock(16000, 20);
    const dropped = clock.enqueue(new Float32Array(320), 0);
    const pressured = clock.enqueue(new Float32Array(320), 20_000);
    expect(dropped).toBe(false);
    expect(pressured).toBe(true);
    expect(clock.queue.queuedMs).toBeLessThanOrEqual(40);
    applyControlEvent(clock, { type: "response.cancelled", clear_audio: true });
    expect(clock.cleared).toBe(1);
    expect(clock.queue.queuedMs).toBe(0);
    expect(nextDelayMs(3)).toBe(1600);
  });
});
