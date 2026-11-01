/** Microphone capture helpers. Echo control is requested from the browser, not invented here. */

export const MIC_CONSTRAINTS: MediaStreamConstraints = {
  audio: {
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
  },
};

export function floatToPcm16(samples: Float32Array): Uint8Array {
  const bytes = new Uint8Array(samples.length * 2);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < samples.length; index += 1) {
    const clipped = Math.max(-1, Math.min(1, samples[index] ?? 0));
    view.setInt16(index * 2, Math.round(clipped < 0 ? clipped * 32768 : clipped * 32767), true);
  }
  return bytes;
}

export function takeFrames(pending: Float32Array, incoming: Float32Array, frameSize: number): { frames: Float32Array[]; rest: Float32Array } {
  const joined = new Float32Array(pending.length + incoming.length);
  joined.set(pending, 0);
  joined.set(incoming, pending.length);
  const frames: Float32Array[] = [];
  let offset = 0;
  while (joined.length - offset >= frameSize) {
    frames.push(joined.slice(offset, offset + frameSize));
    offset += frameSize;
  }
  return { frames, rest: joined.slice(offset) };
}
