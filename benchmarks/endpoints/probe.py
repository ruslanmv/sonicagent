"""Measure SonicAgent speech endpoints from a real HTTP client.

The probe records client-observed time. It does not invent server time, and it
does not claim a headset result. Pass the API key only through SONIC_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import wave
from datetime import datetime
from http.client import HTTPConnection, HTTPSConnection, ResponseNotReady
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from benchmarks.endpoints.report import render_markdown
from benchmarks.endpoints.stats import summarize

ROOT = Path(__file__).resolve().parents[2]
SPEECH = (
    ("tts_en_lessac", "en_US-lessac-medium", "en-US", "Hello."),
    ("tts_en_kristin", "en_US-kristin-medium", "en-US", "Stay with me."),
    ("tts_it_paola", "it_IT-paola-medium", "it-IT", "Ciao."),
    ("tts_es_sharvard", "es_ES-sharvard-secretary", "es-ES", "Hola."),
    ("tts_es_sharvard_male", "es_ES-sharvard-male", "es-ES", "Hola."),
)
STT = (
    ("stt_en", "tests/fixtures/audio/en_hello.wav", "en"),
    ("stt_it", "tests/fixtures/audio/it_ciao.wav", "it"),
)


class ProbeError(RuntimeError):
    pass


def _git(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _space_info(base_url: str) -> dict[str, str]:
    host = urlparse(base_url).netloc
    info = {"space_stage": "", "space_hardware": "", "space_region": "", "space_sha": ""}
    if not host.endswith(".hf.space"):
        return info
    slug = host[: -len(".hf.space")].replace("-", "/", 1)
    try:
        import urllib.request

        with urllib.request.urlopen(f"https://huggingface.co/api/spaces/{slug}", timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError, TimeoutError):
        return info
    runtime = payload.get("runtime") if isinstance(payload, dict) else None
    if not isinstance(runtime, dict):
        return info
    info["space_stage"] = str(runtime.get("stage") or "")
    hardware = runtime.get("hardware") or {}
    if isinstance(hardware, dict):
        info["space_hardware"] = str(hardware.get("current") or hardware.get("requested") or "")
    else:
        info["space_hardware"] = str(hardware)
    info["space_region"] = str(
        runtime.get("region") or (payload.get("region") if isinstance(payload, dict) else "") or ""
    )
    info["space_sha"] = str(runtime.get("sha") or "")
    return info


def wav_duration_ms(payload: bytes) -> int | None:
    if not payload.startswith(b"RIFF"):
        return None
    try:
        with wave.open(BytesIO(payload), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
    except wave.Error:
        return None
    if rate <= 0:
        return None
    return int(frames / rate * 1000)


class Session:
    def __init__(self, base_url: str, token: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ProbeError("base URL must be http or https")
        self.base_url = base_url.rstrip("/")
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.token = token
        self._conn: HTTPConnection | None = None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 120,
    ) -> dict[str, object]:
        last_error = ""
        for attempt in (1, 2):
            started = time.perf_counter()
            try:
                connection = self._connection(timeout)
                outgoing = dict(headers or {})
                outgoing.setdefault("Connection", "keep-alive")
                outgoing.setdefault("User-Agent", "sonicagent-endpoint-probe")
                if self.token and path.startswith("/v1/"):
                    outgoing["Authorization"] = f"Bearer {self.token}"
                connection.request(method, path, body=body, headers=outgoing)
                response = connection.getresponse()
                first = time.perf_counter()
                payload = response.read()
                finished = time.perf_counter()
                return {
                    "status": response.status,
                    "ttfb_ms": (first - started) * 1000,
                    "total_ms": (finished - started) * 1000,
                    "bytes": len(payload),
                    "reconnected": attempt > 1,
                    "body": payload,
                    "headers": {key.lower(): value for key, value in response.getheaders()},
                }
            except (OSError, TimeoutError, ResponseNotReady) as exc:
                self.close()
                last_error = exc.__class__.__name__
                if attempt == 2:
                    finished = time.perf_counter()
                    return {
                        "status": 0,
                        "ttfb_ms": None,
                        "total_ms": (finished - started) * 1000,
                        "bytes": 0,
                        "reconnected": True,
                        "body": b"",
                        "headers": {},
                        "error": last_error,
                    }
        raise ProbeError(last_error or "request failed")

    def _connection(self, timeout: float) -> HTTPConnection:
        if self._conn is not None:
            return self._conn
        if self.scheme == "https":
            self._conn = HTTPSConnection(self.host, timeout=timeout)
        else:
            self._conn = HTTPConnection(self.host, timeout=timeout)
        return self._conn


def _sample(result: dict[str, object], *, audio_ms: int | None = None) -> dict[str, object]:
    total = result.get("total_ms")
    sample: dict[str, object] = {
        "status": result.get("status"),
        "ttfb_ms": _round(result.get("ttfb_ms")),
        "total_ms": _round(total),
        "bytes": result.get("bytes"),
    }
    if result.get("error"):
        sample["error"] = result["error"]
    if audio_ms is not None and isinstance(total, (int, float)) and audio_ms > 0:
        sample["audio_ms"] = audio_ms
        sample["rtf"] = round(float(total) / audio_ms, 3)
    header = result.get("headers")
    if isinstance(header, dict) and header.get("x-sonic-processing-ms"):
        sample["processing_ms"] = header["x-sonic-processing-ms"]
    return sample


def _round(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value), 1)


def _summary(samples: list[dict[str, object]]) -> dict[str, object]:
    ok = [item for item in samples if item.get("status") == 200]
    errors = len(samples) - len(ok)

    def numbers(key: str) -> list[float]:
        return [float(item[key]) for item in ok if isinstance(item.get(key), (int, float))]

    return {
        "n": len(samples),
        "errors": errors,
        "total_ms": summarize(numbers("total_ms")),
        "ttfb_ms": summarize(numbers("ttfb_ms")),
        "audio_ms": summarize(numbers("audio_ms")),
        "rtf": summarize(numbers("rtf")),
    }


def _series(name: str, method: str, path: str, samples: list[dict[str, object]]) -> dict[str, object]:
    public = [{key: value for key, value in sample.items() if key != "body"} for sample in samples]
    return {"name": name, "method": method, "path": path, "samples": public, "summary": _summary(public)}


def _multipart(field: str, filename: str, content: bytes, extra: dict[str, str]) -> tuple[bytes, str]:
    boundary = "sonicendpointprobe"
    chunks: list[bytes] = []
    for key, value in extra.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    chunks.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        + content
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _repeat(
    session: Session, method: str, path: str, count: int, **kwargs: object
) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    body = kwargs.get("body")
    headers = kwargs.get("headers")
    for _ in range(count):
        result = session.request(
            method,
            path,
            body=body if isinstance(body, bytes) else None,
            headers=headers if isinstance(headers, dict) else None,
        )
        audio = wav_duration_ms(result["body"]) if isinstance(result.get("body"), bytes) else None
        samples.append(_sample(result, audio_ms=audio))
    return samples


def _speech_body(voice: str, language: str, text: str) -> bytes:
    return json.dumps({"text": text, "voice": voice, "language": language, "format": "wav"}).encode()


def build_report(base_url: str, *, repeats: int, token: str) -> dict[str, object]:
    if repeats < 1 or repeats > 20:
        raise ProbeError("repeats must be from 1 to 20")
    session = Session(base_url, token)
    notes: list[str] = []
    series: list[dict[str, object]] = []
    try:
        cold = session.request("GET", "/health/live")
        series.append(_series("health_live_cold", "GET", "/health/live", [_sample(cold)]))
        series.append(
            _series(
                "health_live_warm",
                "GET",
                "/health/live",
                _repeat(session, "GET", "/health/live", max(repeats, 20)),
            )
        )
        series.append(
            _series(
                "health_ready",
                "GET",
                "/health/ready",
                _repeat(session, "GET", "/health/ready", min(repeats, 5)),
            )
        )
        example = "/ui-assets/examples/it_IT-paola-medium.wav"
        series.append(
            _series("example_wav", "GET", example, _repeat(session, "GET", example, min(repeats, 5)))
        )
        if token:
            series.append(
                _series(
                    "capabilities",
                    "GET",
                    "/v1/audio/capabilities",
                    _repeat(session, "GET", "/v1/audio/capabilities", min(repeats, 3)),
                )
            )
            speech_path = "/v1/audio/speech"
            speech_headers = {"Content-Type": "application/json"}
            stt_path = "/v1/audio/transcriptions"
            auth = "bearer"
        else:
            notes.append("No SONIC_API_KEY was set, so speech used the public demo limiter.")
            speech_path = "/demo/speech"
            speech_headers = {"Content-Type": "application/json", "X-Sonic-Demo-UI": "1"}
            stt_path = "/demo/transcriptions"
            auth = "public-demo"
            repeats = min(repeats, 2)
        for name, voice, language, text in SPEECH:
            body = _speech_body(voice, language, text)
            warmup = session.request("POST", speech_path, body=body, headers=speech_headers)
            warmup_sample = _sample(
                warmup,
                audio_ms=wav_duration_ms(warmup["body"]) if isinstance(warmup.get("body"), bytes) else None,
            )
            measured = _repeat(session, "POST", speech_path, repeats, body=body, headers=speech_headers)
            block = _series(name, "POST", speech_path, measured)
            block["warmup"] = warmup_sample
            block["voice"] = voice
            block["text"] = text
            series.append(block)
        for name, relative, language in STT:
            audio_path = ROOT / relative
            content = audio_path.read_bytes()
            body, content_type = _multipart("file", audio_path.name, content, {"language": language})
            headers = {"Content-Type": content_type}
            if not token:
                headers["X-Sonic-Demo-UI"] = "1"
            warmup = session.request("POST", stt_path, body=body, headers=headers)
            measured = _repeat(session, "POST", stt_path, min(repeats, 3), body=body, headers=headers)
            block = _series(name, "POST", stt_path, measured)
            block["warmup_status"] = warmup.get("status")
            block["fixture"] = relative
            if isinstance(warmup.get("body"), bytes) and warmup.get("status") == 200:
                try:
                    transcript = json.loads(warmup["body"].decode("utf-8"))
                except json.JSONDecodeError:
                    transcript = {}
                if isinstance(transcript, dict):
                    block["transcript"] = str(transcript.get("text") or "")
            series.append(block)
    finally:
        session.close()
    rome = datetime.now(ZoneInfo("Europe/Rome")).isoformat(timespec="seconds")
    target = {
        "base_url": base_url.rstrip("/"),
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_dirty": bool(_git(["status", "--porcelain"])),
    }
    target.update(_space_info(base_url))
    return {
        "schema_version": 1,
        "measured_at": rome,
        "auth": auth,
        "client": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "target": target,
        "notes": notes
        + [
            "Warmup calls are excluded from the percentile rows.",
            "p99 is omitted when a series has fewer than 20 successful samples.",
            "The client is not a VR headset, phone, or AR device.",
        ],
        "series": series,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure SonicAgent HTTP speech endpoints")
    parser.add_argument(
        "--base-url", default=os.environ.get("SONIC_BENCH_URL", "https://ruslanmv-sonicagent.hf.space")
    )
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "endpoints.json")
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    token = os.environ.get("SONIC_API_KEY", "").strip()
    try:
        report = build_report(args.base_url, repeats=args.repeats, token=token)
    except ProbeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
