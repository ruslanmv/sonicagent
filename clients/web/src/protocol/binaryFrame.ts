import { HEADER_SIZE, MAGIC, PROTOCOL_VERSION } from "./constants";

export interface BinaryAudioFrame { messageType:number; codec:number; flags:number; sampleRate:number; sequence:number; timestampUs:bigint; payload:Uint8Array; }

export function encodeFrame(frame: BinaryAudioFrame): ArrayBuffer {
  const out = new ArrayBuffer(HEADER_SIZE + frame.payload.byteLength);
  const view = new DataView(out);
  const bytes = new Uint8Array(out);
  bytes.set(MAGIC, 0); view.setUint8(2, PROTOCOL_VERSION); view.setUint8(3, frame.messageType); view.setUint8(4, frame.codec); view.setUint8(5, frame.flags);
  view.setUint16(6, frame.sampleRate); view.setUint32(8, frame.sequence); view.setBigUint64(12, frame.timestampUs); view.setUint32(20, frame.payload.byteLength); bytes.set(frame.payload, HEADER_SIZE);
  return out;
}
