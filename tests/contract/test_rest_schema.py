from tests.unit.test_voice_api import FakeStt, auth, client_for, settings


def test_session_create_returns_a_private_resume_token() -> None:
    with client_for(settings(), FakeStt()) as client:
        response = client.post(
            "/v1/sessions",
            headers=auth(),
            json={"language": "en", "voice_id": "en_US-lessac-medium"},
        )
    body = response.json()
    assert response.status_code == 200
    assert body["session_id"].startswith("ses_")
    assert body["websocket_url"] == f"/v1/realtime/{body['session_id']}"
    assert "development-token" not in body["resume_token"]
    assert body["server_capabilities"]["binary_audio"] is True
