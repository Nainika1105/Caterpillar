from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class WeatherScheduler:
    def __init__(self, refresh: Callable[[], Awaitable[None]], interval_seconds: int = 900) -> None:
        self.refresh = refresh
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.refresh()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(self.interval_seconds)
