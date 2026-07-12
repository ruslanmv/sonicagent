from sonicagent_rt.stt.partial_stabilizer import PartialStabilizer


def test_partial_stabilizer_requires_repeated_hypothesis() -> None:
    stabilizer = PartialStabilizer(min_repeats=2)
    assert stabilizer.update("hello wor") == ""
    assert stabilizer.update("hello world") == ""
    assert stabilizer.update("hello world") == "hello world"
