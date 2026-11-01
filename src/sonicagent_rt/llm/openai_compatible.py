"""Streaming chat client for an OpenAI-compatible HTTP endpoint, including Ollama."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from urllib.error import URLError
from urllib.request import Request, urlopen

from sonicagent_rt.stt.errors import InferenceFailed

logger = logging.getLogger("sonicagent.llm")


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_sec: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_sec = timeout_sec

    async def stream(self, messages: list[object], cancellation: object | None = None) -> AsyncIterator[str]:
        import asyncio

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()

        def worker() -> None:
            try:
                for piece in self._iter_tokens(messages, cancellation):
                    loop.call_soon_threadsafe(queue.put_nowait, piece)
            except Exception as exc:  # surfaced to the async consumer
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            loop.call_soon_threadsafe(queue.put_nowait, None)

        task = asyncio.create_task(asyncio.to_thread(worker))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            await task

    def _iter_tokens(self, messages: list[object], cancellation: object | None):
        yielded = False
        for attempt in range(2):
            try:
                for token in self._read_once(messages, cancellation):
                    yielded = True
                    yield token
                return
            except (URLError, TimeoutError) as exc:
                logger.info(
                    "llm request failed",
                    extra={"model": self._model, "attempt": attempt, "error_type": type(exc).__name__},
                )
                if yielded or attempt == 1 or getattr(cancellation, "cancelled", False):
                    raise InferenceFailed("language model request failed") from exc

    def _read_once(self, messages: list[object], cancellation: object | None):
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = Request(f"{self._base_url}/chat/completions", data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout_sec) as response:  # noqa: S310 - operator-configured URL
                for raw in response:
                    if getattr(cancellation, "cancelled", False):
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    parsed = json.loads(data)
                    choices = parsed.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content") or ""
                    if text:
                        yield text
        except json.JSONDecodeError as exc:
            raise InferenceFailed("language model request failed") from exc
