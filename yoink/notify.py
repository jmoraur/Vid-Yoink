"""Desktop notifications through notify-send (libnotify). Best effort: no tool, no
desktop session or a switched-off setting all mean silence, never an error."""

from html import escape
from shutil import which
from subprocess import DEVNULL, Popen

from . import db


def job_done(job_id: int) -> None:
    """Tell the desktop that a download finished or failed. Cancelled jobs stay
    quiet: the user did that themselves."""
    exe = which("notify-send")
    row = db.get_job(job_id)
    if not exe or row is None or db.get_setting("notifications") == "0":
        return
    if row["status"] == "error":
        summary = "Download failed"
    elif row["status"] != "finished":
        return
    elif not row["files_json"]:
        summary = "Already downloaded"
    else:
        summary = "Download finished, some items failed" if row["error"] else "Download finished"
    # The body may be shown as markup, so a title like "<b> & co" must be escaped;
    # "--" keeps a title that starts with a dash from being read as an option.
    body = escape(row["title"] or row["url"], quote=False)
    try:
        Popen([exe, "-a", "Yoink", "-i", "yoink", "--", summary, body],
              stdout=DEVNULL, stderr=DEVNULL)
    except OSError:
        pass
