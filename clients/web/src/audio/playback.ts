/** Playback clock. Cancelled turns drop every queued sample. */

import { PcmQueue } from "./audioQueue";

export class PlaybackClock {
  readonly queue: PcmQueue;
  cleared = 0;

  constructor(sampleRate: number, maxMs: number) {
    this.queue = new PcmQueue(sampleRate, maxMs);
  }

  enqueue(samples: Float32Array, timestampUs: number): boolean {
    return this.queue.push(samples, timestampUs).dropped;
  }

  render(frameSize: number): { samples: Float32Array; timestampUs: number; queuedMs: number } {
    return {
      samples: this.queue.pull(frameSize),
      timestampUs: this.queue.lastTimestampUs,
      queuedMs: this.queue.queuedMs,
    };
  }

  clear(): void {
    this.queue.clear();
    this.cleared += 1;
  }
}
