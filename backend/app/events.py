from __future__ import annotations

import json
import os
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis


class EventBroker:
    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._subscriber_task: asyncio.Task[None] | None = None
        self.redis_url = os.getenv("REDIS_URL")

    async def publish(self, event: dict[str, Any]) -> None:
        if not self.redis_url:
            return
        try:
            if self._redis is None:
                self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.publish("operator-assistant.events", json.dumps(event, default=str))
        except Exception:
            await self.close()

    async def close(self) -> None:
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            self._subscriber_task = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def start_subscriber(self, callback: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        if not self.redis_url or self._subscriber_task is not None:
            return
        self._subscriber_task = asyncio.create_task(self._consume(callback))

    async def _consume(self, callback: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        redis: Redis | None = None
        try:
            redis = Redis.from_url(self.redis_url, decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe("operator-assistant.events")
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    await callback(json.loads(message["data"]))
        except asyncio.CancelledError:
            raise
        except Exception:
            return
        finally:
            if redis is not None:
                await redis.aclose()


broker = EventBroker()


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_json(event)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


connection_manager = ConnectionManager()
