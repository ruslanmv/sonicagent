class PlaybackProcessor extends AudioWorkletProcessor {
  pending = new Float32Array(0);

  constructor() {
    super();
    this.port.onmessage = (event: MessageEvent<{ type?: string; samples?: Float32Array }>) => {
      if (event.data?.type === "clear") {
        this.pending = new Float32Array(0);
        return;
      }
      const samples = event.data?.samples;
      if (!samples) return;
      const joined = new Float32Array(this.pending.length + samples.length);
      joined.set(this.pending, 0);
      joined.set(samples, this.pending.length);
      this.pending = joined;
    };
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const channel = outputs[0]?.[0];
    if (!channel) return true;
    const count = Math.min(channel.length, this.pending.length);
    channel.fill(0);
    if (count > 0) channel.set(this.pending.subarray(0, count));
    this.pending = this.pending.subarray(count);
    return true;
  }
}

registerProcessor("sonic-playback", PlaybackProcessor);
