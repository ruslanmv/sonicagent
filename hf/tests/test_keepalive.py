"""The keep-alive decisions (hf/scripts/keepalive.py): every Hub stage, pinned."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "keepalive.py"
_spec = importlib.util.spec_from_file_location("keepalive", _PATH)
keepalive = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(keepalive)


@pytest.mark.parametrize(
    ("stage", "ready", "force", "action"),
    [
        ("RUNNING", True, False, "ok"),
        ("RUNNING", False, False, "restart"),
        ("SLEEPING", False, False, "wake"),
        ("RUNTIME_ERROR", False, False, "restart"),
        ("BUILDING", False, False, "wait"),
        ("APP_STARTING", False, False, "wait"),
        ("BUILD_ERROR", False, False, "broken"),
        ("CONFIG_ERROR", False, True, "broken"),
        ("PAUSED", False, False, "paused"),
        ("STOPPED", False, False, "paused"),
        ("PAUSED", False, True, "restart"),
        ("SOMETHING_NEW", True, False, "ok"),
        (None, False, False, "restart"),
    ],
)
def test_decide(stage, ready, force, action):
    assert keepalive.decide(stage, ready, force=force) == action


def test_space_url_prefers_the_hub_domain():
    rt = {"domains": [{"domain": "ruslanmv-sonicagent.hf.space", "stage": "READY"}]}
    assert keepalive.space_url(rt, "ruslanmv/SonicAgent") == "https://ruslanmv-sonicagent.hf.space"
    assert keepalive.space_url({}, "Ruslan_MV/Sonic.Agent") == "https://ruslan-mv-sonic-agent.hf.space"


def test_sleeping_space_is_woken_and_waited_for(monkeypatch):
    calls = []
    state = {"ready": False}

    def fake_request(url, *, token=None, method="GET", timeout=30.0):
        calls.append((method, url, bool(token)))
        if url.endswith("/runtime"):
            return 200, b'{"stage":"SLEEPING","domains":[{"domain":"x-y.hf.space","stage":"READY"}]}'
        if url.endswith("/restart"):
            state["ready"] = True
            return 200, b"{}"
        if url.endswith("/health/ready"):
            return (200, b'{"ready":true}') if state["ready"] else (503, b"")
        return 200, b""

    monkeypatch.setattr(keepalive, "_request", fake_request)
    t = {"now": 0.0}
    rc = keepalive.run(
        "x/y", "tok", wait_s=120, sleep=lambda s: t.__setitem__("now", t["now"] + s), clock=lambda: t["now"]
    )
    assert rc == 0
    assert ("POST", "https://huggingface.co/api/spaces/x/y/restart", True) in calls
    # The token goes only to huggingface.co, never to the Space itself.
    assert all(not authed for (_, url, authed) in calls if ".hf.space" in url)


def test_main_refuses_without_configuration(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert keepalive.main(["--repo-id", "x/y"]) == 2
