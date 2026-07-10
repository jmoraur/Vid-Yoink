from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..vault import Vault, VaultError, VaultLocked, WrongPassword

router = APIRouter()


class PasswordIn(BaseModel):
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class CredentialIn(BaseModel):
    username: str
    password: str


class CookiesIn(BaseModel):
    content: str


def _vault(request: Request) -> Vault:
    return request.app.state.vault


def _status(request: Request) -> dict:
    vault = _vault(request)
    status: dict = {"state": vault.state}
    if vault.state == "unlocked":
        status |= vault.labels()
    return status


def _publish_status(request: Request) -> None:
    request.app.state.broadcaster.publish(
        {"type": "vault_status", "state": _vault(request).state}
    )


def _handle(request: Request, action) -> dict:
    try:
        action()
    except WrongPassword as exc:
        raise HTTPException(403, str(exc))
    except VaultLocked as exc:
        raise HTTPException(409, str(exc))
    except VaultError as exc:
        raise HTTPException(422, str(exc))
    _publish_status(request)
    return _status(request)


@router.get("/vault/status")
async def vault_status(request: Request) -> dict:
    return _status(request)


@router.post("/vault/init")
async def init_vault(body: PasswordIn, request: Request) -> dict:
    return _handle(request, lambda: _vault(request).init(body.password))


@router.post("/vault/unlock")
async def unlock_vault(body: PasswordIn, request: Request) -> dict:
    return _handle(request, lambda: _vault(request).unlock(body.password))


@router.post("/vault/lock")
async def lock_vault(request: Request) -> dict:
    return _handle(request, lambda: _vault(request).lock())


@router.post("/vault/change-password")
async def change_password(body: ChangePasswordIn, request: Request) -> dict:
    return _handle(
        request, lambda: _vault(request).change_password(body.old_password, body.new_password)
    )


@router.put("/vault/credentials/{label}")
async def set_credential(label: str, body: CredentialIn, request: Request) -> dict:
    return _handle(
        request, lambda: _vault(request).set_credential(label, body.username, body.password)
    )


@router.delete("/vault/credentials/{label}")
async def delete_credential(label: str, request: Request) -> dict:
    return _handle(request, lambda: _vault(request).delete_credential(label))


@router.put("/vault/cookies/{label}")
async def set_cookies(label: str, body: CookiesIn, request: Request) -> dict:
    return _handle(request, lambda: _vault(request).set_cookies(label, body.content))


@router.delete("/vault/cookies/{label}")
async def delete_cookies(label: str, request: Request) -> dict:
    return _handle(request, lambda: _vault(request).delete_cookies(label))
