"""Build the configured text provider. Mock is explicit and local."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from sonicagent_rt.config import Settings
from sonicagent_rt.llm.mock import MockLLMProvider
from sonicagent_rt.llm.openai_compatible import OpenAICompatibleLLM


class LanguageModel(Protocol):
    async def stream(self, messages: list[object], cancellation: object | None = None) -> AsyncIterator[str]:
        """Yield text deltas. Stop when ``cancellation.cancelled`` is true."""


def create_llm(settings: Settings) -> LanguageModel:
    provider = settings.llm_provider.strip().lower()
    if provider in {"", "mock"}:
        return MockLLMProvider()
    if provider in {"openai", "openai-compatible", "ollama"}:
        return OpenAICompatibleLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    raise ValueError("SONIC_LLM_PROVIDER must be mock, openai-compatible, or ollama")
