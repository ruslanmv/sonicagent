class PlaybackProcessor extends AudioWorkletProcessor { process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean { outputs[0]?.forEach(channel=>channel.fill(0)); return true; } }
registerProcessor("sonic-playback", PlaybackProcessor);
