import pytest

from sonicagent_rt.protocol.sequence import SequenceError, SequenceValidator


def test_sequence_validator_accepts_in_order_from_first_seen() -> None:
    validator = SequenceValidator()
    validator.accept(10)
    validator.accept(11)


def test_sequence_validator_rejects_replay() -> None:
    validator = SequenceValidator()
    validator.accept(2)
    with pytest.raises(SequenceError, match="replay"):
        validator.accept(2)
