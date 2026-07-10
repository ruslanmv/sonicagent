from sonicagent_rt.sessions.state import SessionState

def test_session_state_values() -> None:
    assert SessionState.LISTENING.value == "listening"
