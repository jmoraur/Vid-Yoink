import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """The whole app on a throwaway data folder, addressed like the real one."""
    monkeypatch.setenv("YOINK_DATA_DIR", str(tmp_path / "data"))
    from yoink.app import create_app

    with TestClient(create_app(), base_url="http://127.0.0.1:8090") as c:
        yield c


@pytest.fixture(autouse=True)
def notifications(monkeypatch):
    """No test may pop up a real desktop notification; they are collected here."""
    sent = []
    monkeypatch.setattr("yoink.notify.which", lambda name: "/usr/bin/notify-send")
    monkeypatch.setattr("yoink.notify.Popen", lambda argv, **kw: sent.append(argv))
    return sent


@pytest.fixture(autouse=True)
def keyring_entries(monkeypatch):
    """No test may touch the real desktop keyring; this dict stands in for it."""
    entries = {}

    def fake_secret_tool(action, vault_path, *options, secret=None):
        key = str(vault_path)
        if action == "store":
            entries[key] = secret
        elif action == "clear":
            entries.pop(key, None)
        found = entries.get(key) if action == "lookup" else ""
        return subprocess.CompletedProcess([], 0 if found is not None else 1, found or "", "")

    monkeypatch.setattr("yoink.keyring._run", fake_secret_tool)
    monkeypatch.setattr("yoink.keyring.which", lambda name: "/usr/bin/secret-tool")
    return entries


@pytest.fixture
def file_url(tmp_path):
    """A small file served from this machine, for real yt-dlp runs without internet."""
    (tmp_path / "www").mkdir()
    (tmp_path / "www" / "clip.mp4").write_bytes(b"\0" * 2048)
    handler = partial(SimpleHTTPRequestHandler, directory=str(tmp_path / "www"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/clip.mp4"
    server.shutdown()
