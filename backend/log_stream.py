from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone


class LogStream:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, str]]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncIterator[dict[str, str]]:
        queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def publish(self, message: str, level: str = "info") -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(payload)
