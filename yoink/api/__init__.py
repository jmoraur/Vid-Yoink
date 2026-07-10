from fastapi import APIRouter

from . import downloads

router = APIRouter(prefix="/api")
router.include_router(downloads.router)
