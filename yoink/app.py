import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse
from starlette.websockets import WebSocketClose

from . import api, config, db, ws
from .jobs import JobManager
from .scheduler import scheduler_loop
from .vault import Vault
from .ws import Broadcaster

FRONTEND_DIST = Path(__file__).resolve().parent / "static"


LOCAL_HOSTS = {"127.0.0.1", "localhost"}


class LocalOnly:
    """Refuse requests that do not come from this app's own pages.

    The server has no login, so listening on 127.0.0.1 alone is not enough: any
    web page open in the user's browser can send requests to it. Two checks:
    Host must name this machine (stops DNS rebinding, where a foreign domain is
    pointed at 127.0.0.1), and Origin, when the browser sends one, must too
    (stops other sites' scripts and forms, and their WebSocket connections).
    Any port is fine, so the Vite dev server keeps working."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            allowed = urlsplit("//" + headers.get("host", "")).hostname in LOCAL_HOSTS and (
                origin is None or urlsplit(origin).hostname in LOCAL_HOSTS
            )
            if not allowed:
                if scope["type"] == "http":
                    response = PlainTextResponse("forbidden: not a local request", 403)
                else:
                    response = WebSocketClose(1008)  # before accept = handshake refused
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


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
    app.add_middleware(LocalOnly)
    app.include_router(api.router)
    app.include_router(ws.router)
    if FRONTEND_DIST.is_dir():
        app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


app = create_app()
