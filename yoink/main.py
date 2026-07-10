import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="yoink", description="Local web UI for yt-dlp")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--data-dir", help="override data directory (default ~/.local/share/yoink)"
    )
    args = parser.parse_args()
    if args.data_dir:
        os.environ["YOINK_DATA_DIR"] = args.data_dir
    uvicorn.run("yoink.app:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
