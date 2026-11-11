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


def test_channel_tabs_are_opened_for_subscription_checks():
    """A channel address lists tabs (playlists); a check needs the videos in them."""
    tab = {"_type": "playlist", "title": "Chan - Shorts", "entries": [
        {"id": "s1", "ie_key": "Youtube", "url": "https://www.youtube.com/shorts/s1"}, None]}
    live = {"_type": "playlist", "title": "Chan - Live", "entries": [
        {"id": "l1", "ie_key": "Youtube", "url": "u", "live_status": "was_live"}]}
    info = {"_type": "playlist", "title": "Chan", "entries": [tab, live]}
    assert [e.id for e in _to_result(info, set()).entries] == [None, None]  # preview: the tabs
    videos = _to_result(info, {"youtube l1"}, flatten=True).entries
    assert [(e.id, e.live_status, e.already_downloaded) for e in videos] == [
        ("s1", None, False), ("l1", "was_live", True)]


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
