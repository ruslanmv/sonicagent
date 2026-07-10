class CaptureProcessor extends AudioWorkletProcessor { process(inputs: Float32Array[][]): boolean { const input=inputs[0]?.[0]; if(input){ this.port.postMessage(input.slice()); } return true; } }
registerProcessor("sonic-capture", CaptureProcessor);
