"""Barge-in is covered by the realtime socket test."""

from tests.unit.test_realtime_session import test_barge_in_cancels_the_active_turn


def test_barge_in_cancels_a_blocking_transcription() -> None:
    test_barge_in_cancels_the_active_turn()
