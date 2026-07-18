import base64
import json
import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from yoink.models import DownloadOptions
from yoink.vault import AAD, Vault, VaultError, VaultLocked, WrongPassword, _derive, resolve_secrets
from yoink.ydl.opts import build_ydl_opts


@pytest.fixture
def vault(tmp_path):
    return Vault(tmp_path / "vault.json")


def test_roundtrip(vault, tmp_path):
    assert vault.state == "uninitialized"
    vault.init("hunter2")
    vault.set_credential("mysite", "jan", "s3cret")
    vault.set_cookies("yt", "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\t...")
    vault.lock()
    assert vault.state == "locked"

    fresh = Vault(tmp_path / "vault.json")  # simulate app restart
    assert fresh.state == "locked"
    fresh.unlock("hunter2")
    assert fresh.credential("mysite") == ("jan", "s3cret")
    assert "youtube" in fresh.cookies("yt")
    assert fresh.labels() == {"credentials": ["mysite"], "cookies": ["yt"]}


def test_wrong_password(vault):
    vault.init("right")
    vault.lock()
    with pytest.raises(WrongPassword):
        vault.unlock("wrong")
    assert vault.state == "locked"


def test_locked_access_raises(vault):
    vault.init("pw")
    vault.lock()
    with pytest.raises(VaultLocked):
        vault.credential("anything")


def test_missing_label(vault):
    vault.init("pw")
    with pytest.raises(VaultError, match="nope"):
        vault.credential("nope")


def test_change_password(vault):
    vault.init("old")
    vault.set_credential("a", "u", "p")
    vault.change_password("old", "new")
    vault.lock()
    with pytest.raises(WrongPassword):
        vault.unlock("old")
    vault.unlock("new")
    assert vault.credential("a") == ("u", "p")


def test_unlock_uses_stored_kdf_params(vault, tmp_path):
    # A vault written with different scrypt params (e.g. before a cost tuning)
    # must still unlock: the params stored in the file are authoritative.
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive("pw", salt, n=2**14, r=8, p=1)
    payload = json.dumps({"credentials": {}, "cookies": {"c": "v"}}).encode()
    doc = {
        "version": 1,
        "kdf": {"name": "scrypt", "n": 2**14, "r": 8, "p": 1},
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ct": base64.b64encode(AESGCM(key).encrypt(nonce, payload, AAD)).decode(),
    }
    (tmp_path / "vault.json").write_text(json.dumps(doc))
    vault.unlock("pw")
    assert vault.cookies("c") == "v"


def test_no_plaintext_on_disk_and_0600(vault, tmp_path):
    vault.init("pw")
    vault.set_credential("site", "myuser", "mypassword")
    vault.set_cookies("c", "SECRETCOOKIEVALUE")
    raw = (tmp_path / "vault.json").read_bytes()
    for secret in (b"myuser", b"mypassword", b"SECRETCOOKIEVALUE"):
        assert secret not in raw
    assert json.loads(raw)["kdf"]["name"] == "scrypt"
    mode = os.stat(tmp_path / "vault.json").st_mode & 0o777
    assert mode == 0o600


def test_resolve_secrets_into_ydl_opts(vault):
    vault.init("pw")
    vault.set_credential("site", "jan", "pw123")
    vault.set_cookies("yt", "# cookies here")
    options = DownloadOptions(credential_label="site", cookies_label="yt")
    secrets = resolve_secrets(options, vault)
    opts = build_ydl_opts(options, secrets)
    assert opts["username"] == "jan"
    assert opts["password"] == "pw123"
    assert opts["cookiefile"].read() == "# cookies here"


def test_resolve_secrets_locked_vault_raises(vault):
    vault.init("pw")
    vault.set_cookies("yt", "x")
    vault.lock()
    with pytest.raises(VaultLocked):
        resolve_secrets(DownloadOptions(cookies_label="yt"), vault)
    # options without labels never touch the vault
    assert resolve_secrets(DownloadOptions(), vault) is None
