"""
Batched detectors.
"""

import asyncio
from typing import Awaitable, Callable, Generic, List, Optional, TypeVar

from invariant.analyzer.runtime.utils.base import BaseDetector

T = TypeVar("T")
R = TypeVar("R")


class BatchAccumulator(Generic[T, R]):
    """
    A simple asyncio batch accumulator that collects items and processes them in batches.

    This is useful for batching API calls, database operations, or other operations
    where processing items in bulk is more efficient than processing them individually.
    """

    def __init__(
        self,
        batch_processor: Callable[[List[T]], Awaitable[List[R]]],
        max_batch_size: int = 100,
        max_wait_time: float = 1.0,
    ):
        """
        Initialize a new batch accumulator.

        Args:
            batch_processor: Async function that processes a batch of items
            max_batch_size: Maximum number of items to collect before processing
            max_wait_time: Maximum time to wait before processing a partial batch (in seconds)
        """
        self.batch_processor = batch_processor
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

        self._queue: List[asyncio.Future[R]] = []
        self._items: List[T] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._timer_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        """Start the batch accumulator."""
        if self._running:
            return

        self._running = True
        self._timer_task = asyncio.create_task(self._timer_loop())

    async def stop(self) -> None:
        """Stop the batch accumulator and process any remaining items."""
        if not self._running:
            return

        self._running = False

        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

        # Process any remaining items
        if self._items:
            await self._process_batch()

    async def add(self, item: T) -> R:
        """
        Add an item to the batch and return a future that will resolve when the item is processed.

        Args:
            item: The item to add to the batch

        Returns:
            A Future that resolves to the result of processing the item
        """
        if not self._running:
            raise RuntimeError("BatchAccumulator is not running. Call start() first.")

        future: asyncio.Future[R] = asyncio.Future()

        async with self._lock:
            self._items.append(item)
            self._queue.append(future)

            if len(self._items) >= self.max_batch_size:
                # We've hit the max batch size, process immediately
                await self._process_batch()

        return await future

    async def _timer_loop(self) -> None:
        """Background task that processes batches after max_wait_time has elapsed."""
        try:
            while self._running:
                await asyncio.sleep(self.max_wait_time)
                async with self._lock:
                    if self._items:
                        await self._process_batch()
        except asyncio.CancelledError:
            # if this gets cancelled, we are shutting down this instance
            # new start() call will re-initialize the instance
            self._running = False
        except Exception:
            import traceback

            traceback.print_exc()

    async def _process_batch(self) -> None:
        """Process the current batch of items."""
        if not self._items:
            return

        items = self._items.copy()
        futures = self._queue.copy()
        self._items = []
        self._queue = []

        try:
            results = await self.batch_processor(items)

            # Resolve futures with results
            if len(results) != len(futures):
                error = ValueError(
                    f"Batch processor returned {len(results)} results for {len(futures)} items"
                )
                for future in futures:
                    if not future.done():
                        future.set_exception(error)
            else:
                for future, result in zip(futures, results):
                    if not future.done():
                        future.set_result(result)
        except Exception as e:
            # If batch processing fails, propagate the error to all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)


class BatchedDetector(BaseDetector):
    """
    A batched detector that uses a BatchAccumulator to process items in batches.

    To subclass, implement the `adetect_batch` method.
    """

    def __init__(self, max_batch_size: int = 1, max_wait_time: float = 0.1):
        # separate accumulators for any serialized args-kwargs combination
        self.accumulators = {}
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

    def get_accumulator(self, args, kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in self.accumulators:

            async def batch_processor(texts):
                return await self.adetect_all_batch(texts, *args, **kwargs)

            self.accumulators[key] = BatchAccumulator(
                batch_processor=batch_processor,
                max_batch_size=self.max_batch_size,
                max_wait_time=self.max_wait_time,
            )
        return self.accumulators[key]

    async def adetect_all_batch(self, texts, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the adetect_all_batch method")

    async def adetect(self, text, *args, **kwargs):
        result = await self.adetect_all(text, *args, **kwargs)
        return len(result) > 0

    async def adetect_all(self, text, *args, **kwargs):
        accumulator = self.get_accumulator(args, kwargs)
        await accumulator.start()
        return await accumulator.add(text)

    def detect(self, text, *args, **kwargs):
        raise NotImplementedError(
            "Batched detectors do not support synchronous detect(). Please use adetect() instead"
        )

    def detect_all(self, text, *args, **kwargs):
        raise NotImplementedError(
            "Batched detectors do not support synchronous detect_all(). Please use adetect_all() instead"
        )
