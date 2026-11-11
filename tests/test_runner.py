"""Runs the real yt-dlp against this machine only (no internet needed)."""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from yoink import db
from yoink.models import DownloadOptions
from yoink.ydl.opts import build_ydl_opts
from yoink.ydl.runner import run_download_job


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    db.init(tmp_path / "test.db")


def run(url, tmp_path):
    opts = build_ydl_opts(DownloadOptions(output_dir=str(tmp_path / "out"), retries=0))
    job_id = db.create_job(url, "{}")
    return run_download_job(job_id, url, opts, threading.Event(), lambda event: None)


@pytest.fixture
def file_url(tmp_path):
    (tmp_path / "www").mkdir()
    (tmp_path / "www" / "clip.mp4").write_bytes(b"\0" * 2048)
    handler = partial(SimpleHTTPRequestHandler, directory=str(tmp_path / "www"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/clip.mp4"
    server.shutdown()


def test_dead_url_is_an_error(tmp_path):
    result = run("http://127.0.0.1:1/x.mp4", tmp_path)
    assert result.status == "error"
    assert result.error and not result.error.startswith("ERROR")
    assert result.files == []


def test_download_then_archive_skip(tmp_path, file_url):
    first = run(file_url, tmp_path)
    assert (first.status, first.error, first.skipped) == ("finished", None, 0)
    assert len(first.files) == 1
    assert (first.filesize, first.thumbnail) == (2048, None)
    assert first.site.startswith("127.0.0.1")  # the domain; real sites give "youtube.com"

    second = run(file_url, tmp_path)  # now in the archive
    assert (second.status, second.error, second.files) == ("finished", None, [])
    assert second.skipped == 1
