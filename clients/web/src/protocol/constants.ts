export const MAGIC = new Uint8Array([0x53, 0x41]);
export const PROTOCOL_VERSION = 1;
export const HEADER_SIZE = 24;
export const MessageType = { AUDIO_INPUT: 1, AUDIO_OUTPUT: 2 } as const;
export const Codec = { PCM16: 1, OPUS_RESERVED: 2 } as const;
export const FLAG_END_OF_UTTERANCE = 1 << 0;
export const CONTROL_EVENTS = ["ping", "session.update", "response.cancel"] as const;
export const SERVER_EVENTS = [
  "session.created", "speech.started", "speech.frame", "speech.stopped",
  "transcript.partial", "transcript.final", "transcript.failed",
  "response.created", "response.text.delta", "response.text.done",
  "response.audio.started", "response.audio.done", "response.cancelled", "metrics.turn", "error",
] as const;
