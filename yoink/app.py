import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import api, config, db, ws
from .jobs import JobManager
from .scheduler import scheduler_loop
from .vault import Vault
from .ws import Broadcaster

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init(config.db_path())
    app.state.broadcaster = Broadcaster()
    app.state.vault = Vault(config.vault_path())
    app.state.jobs = JobManager(app.state.broadcaster, app.state.vault, max_concurrent=2)
    scheduler_task = asyncio.create_task(
        scheduler_loop(app.state.jobs, app.state.broadcaster)
    )
    yield
    scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await scheduler_task


def create_app() -> FastAPI:
    app = FastAPI(title="yoink", lifespan=lifespan)
    app.include_router(api.router)
    app.include_router(ws.router)
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


app = create_app()
