import shutil

from fastapi import APIRouter
from pydantic import BaseModel

import yt_dlp

from .. import config, db

router = APIRouter()


class SettingsIn(BaseModel):
    default_output_dir: str | None = None
    max_concurrent: int | None = None


@router.get("/settings")
async def get_settings() -> dict:
    return {
        "default_output_dir": db.get_setting("default_output_dir")
        or str(config.default_download_dir()),
        "max_concurrent": int(db.get_setting("max_concurrent") or 2),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "yt_dlp_version": yt_dlp.version.__version__,
    }


@router.put("/settings")
async def put_settings(body: SettingsIn) -> dict:
    if body.default_output_dir is not None:
        db.set_setting("default_output_dir", body.default_output_dir)
    if body.max_concurrent is not None:
        db.set_setting("max_concurrent", str(max(1, min(body.max_concurrent, 10))))
    return await get_settings()
