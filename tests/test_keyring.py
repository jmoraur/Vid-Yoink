"""Opt-in: the vault key is kept in the desktop keyring and the vault opens itself
at launch. The keyring here is the stand-in from conftest."""

import subprocess

import pytest
from starlette.testclient import TestClient

from yoink import keyring
from yoink.app import create_app
from yoink.vault import Vault, WrongPassword


def restarted():
    """A second start of the app on the same data folder."""
    return TestClient(create_app(), base_url="http://127.0.0.1:8090")


def state(client):
    status = client.get("/api/vault/status").json()
    return status["state"], status["keyring"]


def test_key_opens_the_vault_and_is_not_the_password(tmp_path):
    vault = Vault(tmp_path / "vault.json")
    vault.init("hunter2")
    vault.set_credential("site", "jan", "s3cret")
    key = vault.export_key()
    assert "hunter2" not in key

    fresh = Vault(tmp_path / "vault.json")
    fresh.unlock_with_key(key)
    assert fresh.credential("site") == ("jan", "s3cret")
    fresh.set_credential("more", "a", "b")  # still writable when opened this way

    vault.change_password("hunter2", "new-password")
    for stale in (key, "not even a key", ""):
        with pytest.raises(WrongPassword):
            Vault(tmp_path / "vault.json").unlock_with_key(stale)


def test_opt_in_unlocks_at_launch(client, keyring_entries):
    client.post("/api/vault/init", json={"password": "hunter2"})
    assert state(client) == ("unlocked", False)
    assert keyring_entries == {}  # nothing is stored unless asked for

    assert client.put("/api/vault/keyring", json={"enabled": True}).json()["keyring"] is True
    (stored,) = keyring_entries.values()
    assert stored and "hunter2" not in stored
    with restarted() as second:
        assert state(second) == ("unlocked", True)

    # a new password makes a new key; the keyring follows
    client.post("/api/vault/change-password",
                json={"old_password": "hunter2", "new_password": "other"})
    assert list(keyring_entries.values()) != [stored]
    with restarted() as second:
        assert state(second) == ("unlocked", True)

    # a key that no longer fits leaves the vault locked, and the app still starts
    keyring_entries.update({path: stored for path in keyring_entries})
    with restarted() as second:
        assert state(second) == ("locked", True)
        assert second.post("/api/vault/unlock", json={"password": "other"}).status_code == 200

    assert client.put("/api/vault/keyring", json={"enabled": False}).json()["keyring"] is False
    assert keyring_entries == {}
    with restarted() as second:
        assert state(second) == ("locked", False)


def test_opt_in_needs_an_unlocked_vault_and_a_working_keyring(client, keyring_entries, monkeypatch):
    client.post("/api/vault/init", json={"password": "hunter2"})
    client.post("/api/vault/lock")
    assert client.put("/api/vault/keyring", json={"enabled": True}).status_code == 409

    client.post("/api/vault/unlock", json={"password": "hunter2"})

    def hangs(*args, **kwargs):  # e.g. the desktop is asking for the keyring password
        raise subprocess.TimeoutExpired("secret-tool", keyring.TIMEOUT)

    monkeypatch.setattr(keyring, "_run", hangs)
    assert client.put("/api/vault/keyring", json={"enabled": True}).status_code == 422
    assert state(client) == ("unlocked", False)
    assert keyring.lookup(client.app.state.vault.path) is None  # and lookups just find nothing
