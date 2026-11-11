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
