"""
Retry policies and exponential backoff implementation for the ULPF Integration Layer.
Supports at-least-once delivery with jitter, maximum retries, and transient vs permanent error classification.
"""

import time
import asyncio
import random
from typing import Callable, Any, TypeVar, Optional, List, Type
import structlog

logger = structlog.get_logger("integration.retry")

T = TypeVar("T")


class RetryPolicy:
    """
    Configurable exponential backoff retry policy for inter-module service invocations.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 2000.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = tuple(retryable_exceptions or [Exception])

    def calculate_delay(self, attempt: int) -> float:
        delay = self.base_delay_ms * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay_ms)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay / 1000.0

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        operation_name: str = "operation",
        **kwargs: Any
    ) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.retryable_exceptions as e:
                last_exception = e
                if attempt >= self.max_retries:
                    logger.error(
                        "Max retries exceeded",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                    )
                    raise
                
                sleep_s = self.calculate_delay(attempt)
                logger.warning(
                    "Transient failure, retrying",
                    operation=operation_name,
                    attempt=attempt + 1,
                    sleep_s=sleep_s,
                    error=str(e),
                )
                await asyncio.sleep(sleep_s)
        
        raise last_exception  # type: ignore

    def execute_sync(
        self,
        func: Callable[..., Any],
        *args: Any,
        operation_name: str = "operation",
        **kwargs: Any
    ) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retryable_exceptions as e:
                last_exception = e
                if attempt >= self.max_retries:
                    logger.error(
                        "Max retries exceeded",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                    )
                    raise
                
                sleep_s = self.calculate_delay(attempt)
                logger.warning(
                    "Transient failure, retrying",
                    operation=operation_name,
                    attempt=attempt + 1,
                    sleep_s=sleep_s,
                    error=str(e),
                )
                time.sleep(sleep_s)
        
        raise last_exception  # type: ignore
