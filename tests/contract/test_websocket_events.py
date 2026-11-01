from sonicagent_rt.protocol.constants import SERVER_EVENTS


def test_realtime_events_are_in_the_server_catalog() -> None:
    required = {
        "session.created",
        "speech.started",
        "speech.stopped",
        "transcript.final",
        "response.created",
        "response.text.delta",
        "response.text.done",
        "response.audio.done",
        "response.cancelled",
        "metrics.turn",
        "error",
    }
    assert required <= set(SERVER_EVENTS)
