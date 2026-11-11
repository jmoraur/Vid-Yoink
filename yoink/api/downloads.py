import os
import subprocess

from fastapi import APIRouter, HTTPException, Request

from .. import db
from ..jobs import JobManager
from ..models import DownloadRequest, JobOut
from ..ydl.opts import OptionsError, build_ydl_opts

router = APIRouter()

DONE = {"finished", "error", "cancelled"}


def _manager(request: Request) -> JobManager:
    return request.app.state.jobs


def _job_out(row, manager: JobManager) -> JobOut:
    return JobOut.from_row(row, progress=manager.live_progress.get(row["id"]))


@router.post("/downloads", status_code=201)
async def create_download(req: DownloadRequest, request: Request) -> JobOut:
    try:
        build_ydl_opts(req.options)  # reject bad options (e.g. invalid extra_args) up front
    except OptionsError as exc:
        raise HTTPException(422, str(exc))
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


def _retry(job_id: int, manager: JobManager) -> None:
    """Same row, back in the queue. A second row per attempt would only be clutter."""
    db.requeue_job(job_id)
    manager.enqueue(job_id)


@router.post("/downloads/retry-failed")
async def retry_failed(request: Request) -> dict:
    failed = db.list_jobs("error", limit=10_000)
    for row in failed:
        _retry(row["id"], _manager(request))
    return {"retried": len(failed)}


@router.post("/downloads/{job_id}/retry")
async def retry_download(job_id: int, request: Request) -> JobOut:
    row = db.get_job(job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    if row["status"] not in DONE:
        raise HTTPException(409, "job is still queued or running")
    manager = _manager(request)
    _retry(job_id, manager)
    return _job_out(db.get_job(job_id), manager)


@router.post("/downloads/{job_id}/open-folder")
async def open_folder(job_id: int) -> dict:
    """Show the job's folder in the desktop's file manager. The path is the one this
    app stored when the download finished; nothing from the request is used."""
    row = db.get_job(job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    files = JobOut.from_row(row).files
    folder = os.path.dirname(files[0]) if files else ""
    if not os.path.isdir(folder):
        raise HTTPException(409, "the folder for this download no longer exists")
    subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"ok": True}


@router.delete("/downloads")
async def clear_downloads(status: str | None = None) -> dict:
    """Remove finished/failed/cancelled jobs from the list (never waiting or running
    ones). Files on disk and the archive are not touched."""
    if status is not None and status not in DONE:
        raise HTTPException(422, f"status must be one of {sorted(DONE)}")
    return {"deleted": db.delete_jobs({status} if status else DONE)}


@router.delete("/downloads/{job_id}")
async def delete_download(job_id: int) -> dict:
    row = db.get_job(job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    if row["status"] not in DONE:
        raise HTTPException(409, "cancel the job before deleting it")
    db.delete_job(job_id)
    return {"ok": True}
