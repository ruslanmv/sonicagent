from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame
from sonicagent_rt.protocol.constants import MessageType, Codec

def test_binary_frame_round_trip() -> None:
    original = BinaryAudioFrame(MessageType.MICROPHONE_AUDIO, Codec.PCM_S16LE, 1, 16000, 7, 123456, b"\x00\x01")
    assert BinaryAudioFrame.decode(original.encode()) == original
