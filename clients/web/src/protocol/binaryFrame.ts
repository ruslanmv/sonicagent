import { Codec, HEADER_SIZE, MAGIC, MessageType, PROTOCOL_VERSION } from "./constants";

export interface BinaryAudioFrame { messageType:number; codec:number; flags:number; sampleRate:number; sequence:number; timestampUs:bigint; payload:Uint8Array; }
export class BinaryFrameError extends Error {}

export function encodeFrame(frame: BinaryAudioFrame): ArrayBuffer {
  if (frame.codec !== Codec.PCM16) throw new BinaryFrameError("protocol v1 supports only PCM16");
  const out = new ArrayBuffer(HEADER_SIZE + frame.payload.byteLength);
  const view = new DataView(out);
  const bytes = new Uint8Array(out);
  bytes.set(MAGIC, 0);
  view.setUint8(2, PROTOCOL_VERSION); view.setUint8(3, frame.messageType); view.setUint8(4, frame.codec); view.setUint8(5, frame.flags);
  view.setUint16(6, frame.sampleRate); view.setUint32(8, frame.sequence); view.setBigUint64(12, frame.timestampUs); view.setUint32(20, frame.payload.byteLength);
  bytes.set(frame.payload, HEADER_SIZE);
  return out;
}

export function decodeFrame(data: ArrayBuffer | Uint8Array): BinaryAudioFrame {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  if (bytes.byteLength < HEADER_SIZE) throw new BinaryFrameError("frame shorter than 24-byte header");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.getUint8(0) !== MAGIC[0] || view.getUint8(1) !== MAGIC[1]) throw new BinaryFrameError("bad magic");
  if (view.getUint8(2) !== PROTOCOL_VERSION) throw new BinaryFrameError("unsupported protocol version");
  const messageType = view.getUint8(3); const codec = view.getUint8(4);
  if (codec !== Codec.PCM16) throw new BinaryFrameError("protocol v1 supports only PCM16");
  if (![MessageType.AUDIO_INPUT, MessageType.AUDIO_OUTPUT].includes(messageType as 1|2)) throw new BinaryFrameError("unknown message type");
  const payloadLength = view.getUint32(20);
  if (bytes.byteLength - HEADER_SIZE !== payloadLength) throw new BinaryFrameError("payload length mismatch");
  return { messageType, codec, flags: view.getUint8(5), sampleRate: view.getUint16(6), sequence: view.getUint32(8), timestampUs: view.getBigUint64(12), payload: bytes.slice(HEADER_SIZE) };
}
