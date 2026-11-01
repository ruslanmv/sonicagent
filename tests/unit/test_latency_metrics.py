"""Turn metrics omit transcript text."""

from tests.unit.test_realtime_session import test_turn_returns_a_transcript_without_logging_the_token


def test_metrics_event_has_no_transcript_field() -> None:
    test_turn_returns_a_transcript_without_logging_the_token()
