import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="yoink", description="Local web UI for yt-dlp")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--data-dir", help="override data directory (default ~/.local/share/yoink)"
    )
    parser.add_argument(
        "--exit-when-closed",
        action="store_true",
        help="stop the server once the last browser window showing it has closed"
        " (used by the desktop launcher when it opens a normal browser tab)",
    )
    args = parser.parse_args()
    if args.data_dir:
        os.environ["YOINK_DATA_DIR"] = args.data_dir
    if args.exit_when_closed:
        os.environ["YOINK_EXIT_WHEN_CLOSED"] = "1"
    # timeout_graceful_shutdown: don't let lingering WebSocket connections hold
    # the process open after SIGTERM — the job manager gets its own shutdown
    # window via the lifespan teardown.
    uvicorn.run(
        "yoink.app:app", host="127.0.0.1", port=args.port, timeout_graceful_shutdown=5
    )


if __name__ == "__main__":
    main()
