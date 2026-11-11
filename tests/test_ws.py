import asyncio
import time

from yoink import ws
from yoink.ws import Broadcaster


def test_server_stops_once_the_last_window_is_gone(monkeypatch):
    stops = []
    monkeypatch.setattr(ws, "stop_server", lambda: stops.append(time.monotonic()))

    async def scenario():
        broadcaster = Broadcaster(exit_when_closed=True)
        first = broadcaster.subscribe()  # a window opens before the start-up limit
        await asyncio.sleep(0.15)
        second = broadcaster.subscribe()
        broadcaster.unsubscribe(first)  # one of two windows closes
        await asyncio.sleep(0.15)
        broadcaster.unsubscribe(second)  # page reload: gone, and back within the grace time
        await asyncio.sleep(0.05)
        reloaded = broadcaster.subscribe()
        await asyncio.sleep(0.15)
        assert stops == []
        broadcaster.unsubscribe(reloaded)  # the last window closes for good
        await asyncio.sleep(0.15)
        assert len(stops) == 1

    monkeypatch.setattr(ws, "EXIT_GRACE", 0.1)
    asyncio.run(scenario())


def test_server_stops_when_no_window_ever_opens(monkeypatch):
    stops = []
    monkeypatch.setattr(ws, "stop_server", lambda: stops.append(1))
    monkeypatch.setattr(ws, "START_GRACE", 0.05)

    async def scenario():
        Broadcaster(exit_when_closed=True)
        await asyncio.sleep(0.15)

    asyncio.run(scenario())
    assert stops == [1]


def test_plain_server_never_stops_itself(monkeypatch):
    stops = []
    monkeypatch.setattr(ws, "stop_server", lambda: stops.append(1))
    monkeypatch.setattr(ws, "EXIT_GRACE", 0.01)
    monkeypatch.setattr(ws, "START_GRACE", 0.01)

    async def scenario():
        broadcaster = Broadcaster()
        broadcaster.unsubscribe(broadcaster.subscribe())
        await asyncio.sleep(0.1)

    asyncio.run(scenario())
    assert stops == []


def test_closed_window_is_noticed_without_waiting_for_an_event(client):
    broadcaster = client.app.state.broadcaster
    with client.websocket_connect("ws://127.0.0.1:8090/ws") as sock:
        assert len(broadcaster._queues) == 1
        client.post("/api/vault/lock")  # any change the page is told about
        assert sock.receive_json()["type"] == "vault_status"
    deadline = time.monotonic() + 2
    while broadcaster._queues and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not broadcaster._queues
