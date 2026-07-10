import { describe, expect, it } from "vitest";
import { encodeFrame } from "../src/protocol/binaryFrame";
describe("binary frame",()=>{it("uses a 24-byte header",()=>{expect(encodeFrame({messageType:1,codec:1,flags:0,sampleRate:16000,sequence:0,timestampUs:0n,payload:new Uint8Array(2)}).byteLength).toBe(26);});});
