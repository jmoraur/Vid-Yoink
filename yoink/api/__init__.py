from fastapi import APIRouter

from . import archive, downloads, presets, probe

router = APIRouter(prefix="/api")
router.include_router(downloads.router)
router.include_router(probe.router)
router.include_router(presets.router)
router.include_router(archive.router)
