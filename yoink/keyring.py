"""The desktop keyring (KWallet, GNOME Keyring: anything that speaks the Secret
Service), reached through libsecret's `secret-tool`. It holds one thing: the vault
key, so the vault can open itself at launch for users who ask for that.

What is stored is the key derived from the master password, never the password
itself. It travels on stdin/stdout, never on a command line. Every call has a
time limit: a locked keyring makes the desktop ask for its password, and the app
must not hang on that."""

import logging
import subprocess
from pathlib import Path
from shutil import which

log = logging.getLogger(__name__)

TIMEOUT = 5  # seconds


def available() -> bool:
    return which("secret-tool") is not None


def _run(action: str, vault_path: Path, *options: str, secret: str | None = None):
    # One entry per vault file: a test copy with its own data folder can never
    # replace or remove the entry of the real one.
    return subprocess.run(
        ["secret-tool", action, *options, "application", "yoink", "vault", str(vault_path)],
        input=secret, capture_output=True, text=True, timeout=TIMEOUT,
    )


def store(vault_path: Path, key: str) -> bool:
    try:
        return _run("store", vault_path, "--label=Yoink vault key", secret=key).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def lookup(vault_path: Path) -> str | None:
    try:
        found = _run("lookup", vault_path)
    except (OSError, subprocess.SubprocessError):
        return None
    return found.stdout.strip() or None if found.returncode == 0 else None


def clear(vault_path: Path) -> None:
    try:
        _run("clear", vault_path)
    except (OSError, subprocess.SubprocessError):
        pass


def unlock(vault) -> bool:
    """Open the vault with the key from the keyring. Any failure (no keyring, no
    entry, an entry from before a password change) just leaves the vault locked:
    the master password still works."""
    key = lookup(vault.path)
    if key is None:
        return False
    try:
        vault.unlock_with_key(key)
        return True
    except Exception as exc:
        log.warning("the key in the desktop keyring did not open the vault: %s", exc)
        return False
