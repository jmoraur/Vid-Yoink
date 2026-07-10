import asyncio

from fastapi import APIRouter, HTTPException

from .. import db
from ..models import ProbeRequest, ProbeResult
from ..ydl.probe import probe_url

router = APIRouter()


@router.post("/probe")
async def probe(req: ProbeRequest) -> ProbeResult:
    keys = db.archive_keys()
    try:
        return await asyncio.to_thread(probe_url, req.url, keys)
    except Exception as exc:
        raise HTTPException(422, str(exc))
