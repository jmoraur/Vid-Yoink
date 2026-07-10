"""WebSocket fan-out: one asyncio.Queue per connected client.

Broadcaster.publish() must only be called from the event loop thread; worker
threads reach it via loop.call_soon_threadsafe (see jobs.JobManager)."""

import asyncio

from fastapi import APIRouter, WebSocket


class Broadcaster:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()

    def publish(self, event: dict) -> None:
        for q in self._queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow client: drop; UI refetches on status changes anyway

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    broadcaster: Broadcaster = ws.app.state.broadcaster
    q = broadcaster.subscribe()
    try:
        while True:
            await ws.send_json(await q.get())
    except Exception:
        pass  # client disconnected (starlette/uvicorn raise different types on send)
    finally:
        broadcaster.unsubscribe(q)
