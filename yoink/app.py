import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import api, config, db, ws
from .jobs import JobManager
from .scheduler import scheduler_loop
from .vault import Vault
from .ws import Broadcaster

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """Serve index.html for unknown non-file paths so client-side routes
    (/queue, /settings, …) work on direct load and refresh."""

    @staticmethod
    def _is_spa_route(path: str) -> bool:
        # never swallow API/WS paths or asset-looking names (with an extension)
        return not path.startswith(("api/", "ws")) and "." not in path.rsplit("/", 1)[-1]

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and self._is_spa_route(path):
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and self._is_spa_route(path):
            return await super().get_response("index.html", scope)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init(config.db_path())
    app.state.broadcaster = Broadcaster()
    app.state.vault = Vault(config.vault_path())
    max_concurrent = int(db.get_setting("max_concurrent") or 2)
    app.state.jobs = JobManager(
        app.state.broadcaster, app.state.vault, max_concurrent=max_concurrent
    )
    scheduler_task = asyncio.create_task(
        scheduler_loop(app.state.jobs, app.state.broadcaster)
    )
    yield
    scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await scheduler_task
    await app.state.jobs.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="yoink", lifespan=lifespan)
    app.include_router(api.router)
    app.include_router(ws.router)
    if FRONTEND_DIST.is_dir():
        app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


app = create_app()
