"""WebSocket fan-out: one asyncio.Queue per connected client.

Broadcaster.publish() must only be called from the event loop thread; worker
threads reach it via loop.call_soon_threadsafe (see jobs.JobManager).

Every open window holds one connection, so the Broadcaster also knows when the
last window has closed. Started with --exit-when-closed, the server then stops."""

import asyncio
import signal

from fastapi import APIRouter, WebSocket

# Seconds without any window before the server stops. Reloading the page drops the
# connection and makes a new one within about two seconds; this must stay above that.
EXIT_GRACE = 10.0
# The first window gets longer: a browser that is not running yet can be slow to open.
START_GRACE = 60.0


def stop_server() -> None:
    """Same as the launcher's TERM: uvicorn shuts down in order and unfinished
    downloads go back in line for the next start."""
    signal.raise_signal(signal.SIGTERM)


class Broadcaster:
    def __init__(self, exit_when_closed: bool = False) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._exit_when_closed = exit_when_closed
        self._exit_timer: asyncio.TimerHandle | None = None
        self._windows_changed(starting=True)

    def publish(self, event: dict) -> None:
        for q in self._queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow client: drop; UI refetches on status changes anyway

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._queues.add(q)
        self._windows_changed()
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)
        self._windows_changed()

    def _windows_changed(self, starting: bool = False) -> None:
        if self._exit_timer is not None:
            self._exit_timer.cancel()
            self._exit_timer = None
        if self._exit_when_closed and not self._queues:
            self._exit_timer = asyncio.get_running_loop().call_later(
                START_GRACE if starting else EXIT_GRACE, lambda: stop_server()
            )


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    broadcaster: Broadcaster = ws.app.state.broadcaster
    q = broadcaster.subscribe()

    async def send_events() -> None:
        while True:
            await ws.send_json(await q.get())

    sender = asyncio.create_task(send_events())
    try:
        # The page never sends anything. Reading is how a closed window is noticed
        # at once, instead of at the next event that fails to send.
        while True:
            await ws.receive_text()
    except Exception:
        pass  # client disconnected (starlette/uvicorn raise different types)
    finally:
        sender.cancel()
        broadcaster.unsubscribe(q)
