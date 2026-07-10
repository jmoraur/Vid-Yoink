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
