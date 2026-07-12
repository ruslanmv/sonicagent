from sonicagent_rt.sessions.state import SessionState


def test_session_state_values_match_protocol() -> None:
    assert [state.value for state in SessionState] == [
        "created",
        "connecting",
        "listening",
        "transcribing",
        "thinking",
        "speaking",
        "interrupted",
        "closing",
        "closed",
        "error",
    ]
