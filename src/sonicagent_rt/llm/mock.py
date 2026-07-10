from collections.abc import AsyncIterator
import asyncio

class MockLLMProvider:
    async def stream(self, messages: list[object], cancellation: object | None = None) -> AsyncIterator[str]:
        for token in ("Hello", " from", " SonicAgent", "."):
            if getattr(cancellation, "cancelled", False):
                return
            await asyncio.sleep(0)
            yield token
