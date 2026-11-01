/** Linear resampler. Enough to feed 16 kHz frames from a browser AudioContext. */

export function resampleLinear(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate <= 0 || toRate <= 0) throw new Error("sample rate must be positive");
  if (input.length === 0 || fromRate === toRate) return input.slice();
  const outLength = Math.max(1, Math.round((input.length * toRate) / fromRate));
  const out = new Float32Array(outLength);
  const scale = fromRate / toRate;
  for (let index = 0; index < outLength; index += 1) {
    const position = index * scale;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const mix = position - left;
    const a = input[left] ?? 0;
    const b = input[right] ?? a;
    out[index] = a + (b - a) * mix;
  }
  return out;
}
