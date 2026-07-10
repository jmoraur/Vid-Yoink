from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import api, config, db, ws
from .jobs import JobManager
from .ws import Broadcaster

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init(config.db_path())
    app.state.broadcaster = Broadcaster()
    app.state.jobs = JobManager(app.state.broadcaster, max_concurrent=2)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="yoink", lifespan=lifespan)
    app.include_router(api.router)
    app.include_router(ws.router)
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


app = create_app()
