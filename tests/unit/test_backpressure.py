from sonicagent_rt.audio.backpressure import BackpressurePolicy


def test_backpressure_accepts_within_limit() -> None:
    assert BackpressurePolicy(max_queued_ms=100).evaluate(queued_ms=40, incoming_ms=20).accepted


def test_backpressure_rejects_full_queue() -> None:
    decision = BackpressurePolicy(max_queued_ms=100).evaluate(queued_ms=90, incoming_ms=20)
    assert not decision.accepted
    assert decision.reason == "queue-full"
    assert not decision.purge


def test_backpressure_marks_slow_client_for_purge() -> None:
    decision = BackpressurePolicy(max_queued_ms=100, slow_client_ms=150).evaluate(140, 20)
    assert not decision.accepted
    assert decision.reason == "slow-client"
    assert decision.purge
