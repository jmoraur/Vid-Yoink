"""Only this machine's own pages may talk to the server (yoink.app.LocalOnly)."""

import pytest
from starlette.websockets import WebSocketDisconnect

FOREIGN = [
    {"host": "evil.example"},  # DNS rebinding: foreign name pointed at 127.0.0.1
    {"host": "127.0.0.1.evil.example"},
    {"origin": "https://evil.example"},  # another site's script or form
    {"origin": "null"},  # sandboxed frame / local file
]
WS = "ws://127.0.0.1:8090/ws"  # the test client would otherwise say Host: testserver
DOWNLOAD = {"url": "http://127.0.0.1:1/x", "options": {"extra_args": "--exec 'touch /tmp/pwned'"}}


@pytest.mark.parametrize("headers", FOREIGN)
def test_foreign_requests_are_refused(client, headers):
    assert client.get("/api/settings", headers=headers).status_code == 403
    assert client.post("/api/downloads", json=DOWNLOAD, headers=headers).status_code == 403
    assert client.post("/api/vault/lock", headers=headers).status_code == 403
    assert client.get("/", headers=headers).status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(WS, headers=headers):
            pass
    assert client.get("/api/downloads").json() == []  # nothing was queued


@pytest.mark.parametrize(
    "headers",
    [{}, {"host": "localhost:8090"}, {"origin": "http://localhost:5173"}],  # 5173 = Vite dev
)
def test_local_requests_still_work(client, headers):
    assert client.get("/api/settings", headers=headers).status_code == 200
    assert client.post("/api/vault/lock", headers=headers).status_code == 200
    assert client.post("/api/downloads", json=DOWNLOAD, headers=headers).status_code == 201
    with client.websocket_connect(WS, headers=headers):
        pass
