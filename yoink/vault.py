"""Encrypted credential vault: one file, scrypt-derived AES-256-GCM.

The decrypted payload and derived key live only in memory while unlocked; every
mutation re-encrypts with a fresh nonce and atomically replaces the file (0600).
GCM's auth tag doubles as the wrong-password check. Cookies are handed to yt-dlp
as io.StringIO, so no secret ever reaches disk in plaintext."""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

AAD = b"yoink-vault-v1"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**17, 8, 1


class VaultError(Exception):
    pass


class VaultLocked(VaultError):
    def __init__(self) -> None:
        super().__init__("Vault is locked — unlock it in Settings and retry")


class WrongPassword(VaultError):
    def __init__(self) -> None:
        super().__init__("Wrong master password")


def _derive(
    password: str, salt: bytes, n: int = SCRYPT_N, r: int = SCRYPT_R, p: int = SCRYPT_P
) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=n, r=r, p=p)
    return kdf.derive(password.encode())


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class Vault:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._key: bytes | None = None
        self._salt: bytes | None = None
        self._payload: dict | None = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def state(self) -> str:
        if self._payload is not None:
            return "unlocked"
        return "locked" if self._path.exists() else "uninitialized"

    # --- lifecycle ---

    def init(self, password: str) -> None:
        if self._path.exists():
            raise VaultError("Vault is already initialized")
        self._salt = os.urandom(16)
        self._key = _derive(password, self._salt)
        self._payload = {"credentials": {}, "cookies": {}}
        self._write()

    def unlock(self, password: str) -> None:
        doc = self._read()
        # Derive with the params stored in the file, not the current module
        # constants — otherwise tuning the scrypt cost would lock out every
        # existing vault with a bogus "wrong password".
        kdf = doc["kdf"]
        salt = base64.b64decode(doc["salt"])
        self._open(doc, _derive(password, salt, n=kdf["n"], r=kdf["r"], p=kdf["p"]))

    def export_key(self) -> str:
        """The key that opens this vault file, for safekeeping in the desktop
        keyring. It stops working when the master password changes."""
        self._require_unlocked()
        assert self._key is not None
        return _b64(self._key)

    def unlock_with_key(self, key: str) -> None:
        """Unlock with a key from export_key() instead of the master password."""
        try:
            raw = base64.b64decode(key)
        except ValueError:  # not base64: whatever this is, it is not our key
            raise WrongPassword() from None
        self._open(self._read(), raw)

    def _read(self) -> dict:
        if not self._path.exists():
            raise VaultError("Vault is not initialized")
        return json.loads(self._path.read_text())

    def _open(self, doc: dict, key: bytes) -> None:
        try:
            plaintext = AESGCM(key).decrypt(
                base64.b64decode(doc["nonce"]), base64.b64decode(doc["ct"]), AAD
            )
        except (InvalidTag, ValueError):  # ValueError: not a usable key at all
            raise WrongPassword() from None
        self._key, self._payload = key, json.loads(plaintext)
        self._salt = base64.b64decode(doc["salt"])

    def lock(self) -> None:
        self._key = self._salt = self._payload = None

    def change_password(self, old_password: str, new_password: str) -> None:
        self.unlock(old_password)  # raises WrongPassword if old is wrong
        self._salt = os.urandom(16)
        self._key = _derive(new_password, self._salt)
        self._write()

    # --- content ---

    def labels(self) -> dict[str, list[str]]:
        payload = self._require_unlocked()
        return {
            "credentials": sorted(payload["credentials"]),
            "cookies": sorted(payload["cookies"]),
        }

    def credential(self, label: str) -> tuple[str, str]:
        payload = self._require_unlocked()
        try:
            cred = payload["credentials"][label]
        except KeyError:
            raise VaultError(f"No stored credential named {label!r}") from None
        return cred["username"], cred["password"]

    def cookies(self, label: str) -> str:
        payload = self._require_unlocked()
        try:
            return payload["cookies"][label]
        except KeyError:
            raise VaultError(f"No stored cookies named {label!r}") from None

    def set_credential(self, label: str, username: str, password: str) -> None:
        payload = self._require_unlocked()
        payload["credentials"][label] = {"username": username, "password": password}
        self._write()

    def delete_credential(self, label: str) -> bool:
        payload = self._require_unlocked()
        removed = payload["credentials"].pop(label, None) is not None
        if removed:
            self._write()
        return removed

    def set_cookies(self, label: str, content: str) -> None:
        payload = self._require_unlocked()
        payload["cookies"][label] = content
        self._write()

    def delete_cookies(self, label: str) -> bool:
        payload = self._require_unlocked()
        removed = payload["cookies"].pop(label, None) is not None
        if removed:
            self._write()
        return removed

    # --- internals ---

    def _require_unlocked(self) -> dict:
        if self._payload is None:
            raise VaultLocked()
        return self._payload

    def _write(self) -> None:
        assert self._key is not None and self._salt is not None
        nonce = os.urandom(12)
        ct = AESGCM(self._key).encrypt(nonce, json.dumps(self._payload).encode(), AAD)
        doc = {
            "version": 1,
            "kdf": {"name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
            "salt": _b64(self._salt),
            "nonce": _b64(nonce),
            "ct": _b64(ct),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps(doc))
                f.flush()
                # fsync before the rename: os.replace is atomic but not durable,
                # and a torn vault file is unrecoverable by design.
                os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        os.replace(tmp, self._path)


# --- job-time secret resolution ---


@dataclass
class ResolvedSecrets:
    username: str | None = None
    password: str | None = None
    cookies_content: str | None = None


def resolve_secrets(options, vault: Vault) -> ResolvedSecrets | None:
    """Turn vault labels in DownloadOptions into actual secrets. Raises VaultLocked /
    VaultError with a user-facing message when that is not possible."""
    if not options.credential_label and not options.cookies_label:
        return None
    secrets = ResolvedSecrets()
    if options.credential_label:
        secrets.username, secrets.password = vault.credential(options.credential_label)
    if options.cookies_label:
        secrets.cookies_content = vault.cookies(options.cookies_label)
    return secrets
