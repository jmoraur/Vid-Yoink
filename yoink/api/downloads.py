from fastapi import APIRouter, HTTPException, Request

from .. import db
from ..jobs import JobManager
from ..models import DownloadRequest, JobOut

router = APIRouter()


def _manager(request: Request) -> JobManager:
    return request.app.state.jobs


def _job_out(row, manager: JobManager) -> JobOut:
    return JobOut.from_row(row, progress=manager.live_progress.get(row["id"]))


@router.post("/downloads", status_code=201)
async def create_download(req: DownloadRequest, request: Request) -> JobOut:
    manager = _manager(request)
    job_id = db.create_job(req.url, req.options.model_dump_json())
    manager.enqueue(job_id)
    return _job_out(db.get_job(job_id), manager)


@router.get("/downloads")
async def list_downloads(
    request: Request, status: str | None = None, limit: int = 100, offset: int = 0
) -> list[JobOut]:
    manager = _manager(request)
    return [_job_out(row, manager) for row in db.list_jobs(status, limit, offset)]


@router.get("/downloads/{job_id}")
async def get_download(job_id: int, request: Request) -> JobOut:
    row = db.get_job(job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    return _job_out(row, _manager(request))


@router.post("/downloads/{job_id}/cancel")
async def cancel_download(job_id: int, request: Request) -> dict:
    if not _manager(request).cancel(job_id):
        raise HTTPException(409, "job is not queued or running")
    return {"ok": True}
