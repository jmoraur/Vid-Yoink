from fastapi import APIRouter, HTTPException

from .. import db
from ..models import ArchiveEntryOut

router = APIRouter()


@router.get("/archive")
async def list_archive(
    subscription_id: int | None = None, q: str | None = None
) -> list[ArchiveEntryOut]:
    return [ArchiveEntryOut.from_row(row) for row in db.list_archive(subscription_id, q)]


@router.delete("/archive/{archive_id}")
async def delete_archive_entry(archive_id: int) -> dict:
    if not db.delete_archive_entry(archive_id):
        raise HTTPException(404, "no such archive entry")
    return {"ok": True}
