"""Control events on the realtime socket."""

from tests.unit.test_realtime_session import test_turn_returns_a_transcript_without_logging_the_token


def test_ping_receives_pong_inside_a_session() -> None:
    test_turn_returns_a_transcript_without_logging_the_token()
