"""Shared rate-limit retry for provider calls.

Free-tier quotas are the failure we actually hit in practice, and every provider
call wants the same backoff, so it lives in one place.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.services.vision.base import RateLimitError

logger = logging.getLogger(__name__)

_RETRY_DELAYS_SECONDS = (2.0, 5.0)

T = TypeVar("T")


async def with_rate_limit_retry(call: Callable[[], Awaitable[T]], provider_name: str) -> T:
    """Await `call()`, retrying on RateLimitError; re-raises once delays run out."""
    for delay in _RETRY_DELAYS_SECONDS:
        try:
            return await call()
        except RateLimitError:
            logger.info("Rate limited by %s, retrying in %.0fs", provider_name, delay)
            await asyncio.sleep(delay)
    return await call()
