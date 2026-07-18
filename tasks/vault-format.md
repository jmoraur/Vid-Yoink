# Vault file format (v1)

Specification of `~/.local/share/yoink/vault.json`, written so the format can be
read, debugged, or reimplemented (e.g. in a rewrite, see
[distribution-plan.md](distribution-plan.md) §3.6) without the Python source.
Reference implementation: `yoink/vault.py`.

## File

A single JSON document, file mode `0600`, replaced atomically (write to
`vault.json.tmp`, fsync, `rename`) on every mutation:

```json
{
  "version": 1,
  "kdf": {"name": "scrypt", "n": 131072, "r": 8, "p": 1},
  "salt": "<base64, 16 bytes>",
  "nonce": "<base64, 12 bytes>",
  "ct": "<base64, ciphertext || 16-byte GCM tag>"
}
```

All binary fields are standard base64 (with padding).

## Key derivation

- **scrypt** over the UTF-8 encoded master password, output length 32 bytes.
- Parameters come **from the file's `kdf` object**, not from constants — a
  reader must honor them so cost tuning never locks out old vaults. Current
  writer defaults: n=2^17, r=8, p=1 (~128 MiB memory).
- A fresh 16-byte random salt is generated at `init` and at password change
  (not on ordinary re-encryption).

## Encryption

- **AES-256-GCM** with the derived key.
- Fresh random 12-byte nonce for **every write** (key reuse across writes is
  safe because the nonce is never reused; random 96-bit nonces are fine at this
  write volume).
- Additional authenticated data (AAD): the ASCII bytes `yoink-vault-v1`.
- `ct` is the GCM output: ciphertext with the 16-byte auth tag appended
  (the `cryptography` library convention).
- **There is no separate password verifier.** A GCM tag mismatch on decrypt
  *is* the wrong-password signal (also triggered by file corruption — the two
  are indistinguishable by design).

## Plaintext payload

The decrypted bytes are UTF-8 JSON:

```json
{
  "credentials": {"<label>": {"username": "...", "password": "..."}},
  "cookies": {"<label>": "<full cookies.txt content as one string>"}
}
```

Labels are free-form user strings, unique per map.

## Lifecycle invariants

- Plaintext payload and derived key exist **only in process memory** while
  unlocked; locking drops both references. No secret is ever written to disk
  unencrypted (cookies reach yt-dlp as an in-memory text stream).
- Password change = decrypt with old params/salt → new salt → derive with the
  **writer's current** params → re-encrypt. So a password change also upgrades
  the vault to current KDF parameters.
- Forgotten password is unrecoverable by design; the remedy is deleting the
  file and starting over.

## Versioning

`version` is 1. A reader encountering an unknown version or `kdf.name` should
refuse rather than guess.
