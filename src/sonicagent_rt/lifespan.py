"""Application startup hooks.

Model warmup runs after the server can accept health checks. Readiness stays
false until the acoustic model is actually loaded.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("sonicagent_rt.lifespan")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    task: asyncio.Task[None] | None = None
    if settings.voice_enabled and (settings.stt_warmup or settings.tts_enabled):
        task = asyncio.create_task(_warm_speech(app))
    try:
        yield
    finally:
        if task is not None and not task.done():
            logger.info("shutdown while speech warmup is still running")


async def _warm_speech(app: FastAPI) -> None:
    settings = app.state.settings
    if settings.stt_warmup:
        try:
            await asyncio.to_thread(app.state.stt.warmup)
        except Exception:
            logger.exception("speech model warmup failed")
    if settings.tts_enabled:
        try:
            await asyncio.to_thread(app.state.tts.warmup)
        except Exception:
            logger.exception("piper voice warmup failed")
