import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """The whole app on a throwaway data folder, addressed like the real one."""
    monkeypatch.setenv("YOINK_DATA_DIR", str(tmp_path / "data"))
    from yoink.app import create_app

    with TestClient(create_app(), base_url="http://127.0.0.1:8090") as c:
        yield c
