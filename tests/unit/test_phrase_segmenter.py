from sonicagent_rt.tts.phrase_segmenter import segment_text

def test_segment_text() -> None:
    assert segment_text("Hello. World!") == ["Hello.", "World!"]
