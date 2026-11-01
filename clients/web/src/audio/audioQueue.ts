/** Bounded playback queue. Overrun drops the oldest audio and reports backpressure. */

export interface QueuedAudio {
  samples: Float32Array;
  timestampUs: number;
}

export class PcmQueue {
  private readonly chunks: QueuedAudio[] = [];
  private samples = 0;
  readonly sampleRate: number;
  readonly maxSamples: number;

  constructor(sampleRate: number, maxMs: number) {
    if (sampleRate <= 0 || maxMs <= 0) throw new Error("queue bounds must be positive");
    this.sampleRate = sampleRate;
    this.maxSamples = Math.max(1, Math.round((sampleRate * maxMs) / 1000));
  }

  get queuedMs(): number {
    return (this.samples / this.sampleRate) * 1000;
  }

  get lastTimestampUs(): number {
    const last = this.chunks[this.chunks.length - 1];
    return last ? last.timestampUs : 0;
  }

  push(samples: Float32Array, timestampUs: number): { dropped: boolean } {
    let dropped = false;
    this.chunks.push({ samples, timestampUs });
    this.samples += samples.length;
    while (this.samples > this.maxSamples && this.chunks.length > 1) {
      const removed = this.chunks.shift();
      if (removed) this.samples -= removed.samples.length;
      dropped = true;
    }
    return { dropped };
  }

  pull(frameSize: number): Float32Array {
    const out = new Float32Array(frameSize);
    let filled = 0;
    while (filled < frameSize && this.chunks.length > 0) {
      const head = this.chunks[0];
      if (!head) break;
      const need = frameSize - filled;
      if (head.samples.length <= need) {
        out.set(head.samples, filled);
        filled += head.samples.length;
        this.samples -= head.samples.length;
        this.chunks.shift();
      } else {
        out.set(head.samples.subarray(0, need), filled);
        head.samples = head.samples.subarray(need);
        this.samples -= need;
        filled += need;
      }
    }
    return out;
  }

  clear(): void {
    this.chunks.length = 0;
    this.samples = 0;
  }
}
