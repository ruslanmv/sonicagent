import asyncio

from sonicagent_rt.pipeline.cancellation import CancellationToken


def test_cancellation_token_is_observable() -> None:
    token = CancellationToken()
    assert token.cancelled is False
    token.cancel()
    assert token.cancelled is True

    async def wait() -> bool:
        fresh = CancellationToken()
        waiter = asyncio.create_task(fresh.wait())
        fresh.cancel()
        await waiter
        return fresh.cancelled

    assert asyncio.run(wait()) is True
