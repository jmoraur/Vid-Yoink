from yoink.ydl import probe
from yoink.ydl.probe import _to_result


def test_playlist_conversion_with_archive_check():
    info = {
        "_type": "playlist",
        "title": "My List",
        "playlist_count": 3,
        "entries": [
            {"id": "aaa", "title": "One", "duration": 60, "ie_key": "Youtube", "url": "u1"},
            {"id": "bbb", "title": "Two", "duration": 61, "ie_key": "Youtube", "url": "u2"},
            None,  # unavailable entry
        ],
    }
    result = _to_result(info, archive_keys={"youtube bbb"})
    assert result.kind == "playlist"
    assert result.count == 3
    assert [e.already_downloaded for e in result.entries] == [False, True]


def test_video_conversion_heights():
    info = {
        "title": "Vid",
        "duration": 10,
        "formats": [
            {"height": 1080, "vcodec": "vp9"},
            {"height": 720, "vcodec": "avc1"},
            {"height": 1080, "vcodec": "vp09"},
            {"height": None, "vcodec": "none"},  # audio-only
        ],
    }
    result = _to_result(info, archive_keys=set())
    assert result.kind == "video"
    assert result.heights == [1080, 720]


def test_entry_limit_is_passed_to_ytdlp(monkeypatch):
    seen = []

    class FakeYDL:
        def __init__(self, params):
            seen.append(params["playlistend"])

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def extract_info(self, url, download):
            return {"title": "x"}

    monkeypatch.setattr(probe, "YoutubeDL", FakeYDL)
    probe.probe_url("https://x", set())
    probe.probe_url("https://x", set(), probe.CHECK_LIMIT)
    assert seen == [probe.PREVIEW_LIMIT, probe.CHECK_LIMIT] == [500, 5000]
