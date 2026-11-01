"""Voice Studio integration tests; no model downloads or inference required."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "hf" / "ui"


def test_speak_panel_has_ready_examples_and_autoplay():
    html = (UI / "index.html").read_text(encoding="utf-8")
    script = (UI / "app.js").read_text(encoding="utf-8")
    catalog = (UI / "catalog.json").read_text(encoding="utf-8")
    assert 'id="voiceGrid"' in html
    assert 'id="voiceFilters"' in html
    assert 'id="voiceSearch"' in html
    assert 'id="playerDock"' not in html
    assert "player-dock" not in (UI / "style.css").read_text(encoding="utf-8")
    assert "<audio id=\"audioPlayer\" class=\"sr-only\" preload=\"none\"></audio>" in html
    assert "controls" not in html.split("audioPlayer")[1][:80]
    assert "audioPlayer.play" in script
    assert "audioPlayer.pause" in script
    assert "⏸" in script
    assert "maybeAutoTranscribe" in script
    assert "Transcription starts when you stop." in script
    assert "Audio is sent only when you click Transcribe" not in script
    assert "Playing now. Replay on the player is optional." not in script
    assert "Playing generated voice" not in script
    assert "/ui-assets/examples/" in script
    assert "grid-template-columns:1fr 1fr" in (UI / "style.css").read_text(encoding="utf-8")
    assert "Lessac · English" not in html + script
    examples = UI / "examples"
    for voice in (
        "en_US-kristin-medium",
        "en_US-lessac-medium",
        "en_GB-cori-medium",
        "en_GB-alba-medium",
        "es_ES-sharvard-companion",
        "es_ES-sharvard-secretary",
        "es_MX-ald-companion",
        "es_MX-ald-medium",
        "fr_FR-upmc-medium",
        "fr_FR-siwis-medium",
        "de_DE-eva_k-x_low",
        "de_DE-kerstin-low",
        "it_IT-paola-companion",
        "it_IT-paola-medium",
    ):
        sample = examples / f"{voice}.wav"
        assert sample.is_file(), voice
        assert sample.read_bytes()[:4] == b"RIFF"
        assert voice in catalog


def test_static_frontend_complete():
    html = (UI / "index.html").read_text(encoding="utf-8")
    css = (UI / "style.css").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert 'href="/ui-assets/style.css' in html
    assert 'src="/ui-assets/app.js' in html
    assert 'id="downloadSpeechBtn"' in html
    assert "E.downloadSpeechBtn.disabled = !S.speechBlob" in js
    for field in ("recordBtn", "uploadTab", "transcribeBtn", "transcriptText",
                  "synthesizeBtn", "audioPlayer", "guestModeBtn", "tokenInput"):
        assert 'id="' + field + '"' in html
    assert len(css) > 1000 and len(js) > 1000
    assert "localStorage" not in js
    assert "SONIC_API_KEY=" not in html + css + js


def test_frontend_calls_protected_and_optional_demo_endpoints():
    script = (UI / "app.js").read_text(encoding="utf-8")
    assert "/v1/audio/transcriptions" in script
    assert "/v1/audio/speech" in script
    assert "/v1/audio/capabilities" in script
    assert "/demo/transcriptions" in script
    assert "/demo/speech" in script
    assert "Authorization" in script
    assert 'S.demoEnabled' in script


def test_huggingface_packaging_contains_frontend():
    dockerfile = (ROOT / "hf" / "Dockerfile").read_text(encoding="utf-8")
    staging = (ROOT / "hf" / "scripts" / "prepare-space.py").read_text(encoding="utf-8")
    assert "COPY hf/ui ./ui" in dockerfile
    assert 'source / "hf" / "ui"' in staging
    assert '"hf/ui"' in staging


def test_public_demo_is_opt_in_and_bounded(monkeypatch):
    from sonicagent_rt.api.routes import demo
    monkeypatch.delenv("SONIC_PUBLIC_DEMO_ENABLED", raising=False)
    monkeypatch.delenv("SONIC_PUBLIC_DEMO_TTS_ENABLED", raising=False)
    assert demo._enabled() is False
    assert demo._tts_enabled() is False
    assert demo.DEMO_SECONDS <= 8
    assert demo.DEMO_BYTES <= 1_200_000
    assert demo.limiter.total_per_minute <= 8


def test_demo_rate_limiter_rejects_excess():
    from fastapi import HTTPException
    from sonicagent_rt.api.routes.demo import DemoRateLimiter
    limiter = DemoRateLimiter(total_per_minute=2, per_client_minute=2)
    limiter.check("client-a")
    limiter.check("client-a")
    try:
        limiter.check("client-a")
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("demo limiter accepted too many requests")


def test_demo_disabled_does_not_bypass_auth(monkeypatch):
    from sonicagent_rt.api.routes.demo import _check
    from fastapi import HTTPException, Request
    monkeypatch.delenv("SONIC_PUBLIC_DEMO_ENABLED", raising=False)
    scope = {"type": "http", "method": "POST", "path": "/demo/transcriptions",
             "headers": [], "client": ("127.0.0.1", 7777)}
    request = Request(scope)
    try:
        _check(request)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("disabled demo permitted anonymous access")


def test_hf_entrypoint_serves_voice_studio_and_keeps_api():
    """Test root routing without starting the heavyweight STT model lifespan."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("sonicagent_hf_ui_app", ROOT / "hf" / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    client = TestClient(module.app)  # no context manager: avoids inference startup
    index = client.get("/")
    assert index.status_code == 200
    assert "Voice Studio" in index.text
    script = client.get("/ui-assets/app.js")
    assert script.status_code == 200
    assert script.headers["cache-control"] == "no-cache"
    style = client.get("/ui-assets/style.css")
    assert style.status_code == 200
    assert style.headers["cache-control"] == "no-cache"
    assert client.get("/api-info").json()["service"] == "sonicagent"
    assert client.get("/health/live").json()["status"] == "ok"
    assert client.get("/demo/status").json()["enabled"] is False
    assert client.post("/demo/transcriptions", headers={"X-Sonic-Demo-UI": "1"}).status_code in (404, 422)
