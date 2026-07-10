import pytest

from yoink.models import DownloadOptions
from yoink.ydl.opts import OptionsError, build_ydl_opts


def pp_keys(opts: dict) -> list[str]:
    return [pp["key"] for pp in opts.get("postprocessors", [])]


def test_defaults():
    opts = build_ydl_opts(DownloadOptions())
    assert opts["quiet"] is True
    assert opts["noprogress"] is True
    assert opts["paths"]["home"].endswith("Downloads")
    assert "FFmpegExtractAudio" not in pp_keys(opts)


def test_audio_mode_mp3():
    opts = build_ydl_opts(DownloadOptions(mode="audio", audio_format="mp3"))
    assert opts["format"] == "bestaudio/best"
    extract = [pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegExtractAudio"]
    assert extract and extract[0]["preferredcodec"] == "mp3"


def test_audio_mode_best_keeps_codec():
    opts = build_ydl_opts(DownloadOptions(mode="audio"))
    extract = [pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegExtractAudio"]
    assert extract and extract[0]["preferredcodec"] == "best"


def test_max_height_and_container():
    opts = build_ydl_opts(DownloadOptions(max_height=1080, container="mkv"))
    assert opts["format"] == "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]"
    assert opts["merge_output_format"] == "mkv"


def test_output_dir_and_template():
    opts = build_ydl_opts(DownloadOptions(output_dir="/tmp/media", output_template="%(id)s.%(ext)s"))
    assert opts["paths"]["home"] == "/tmp/media"
    assert opts["outtmpl"]["default"] == "%(id)s.%(ext)s"


def test_playlist_controls():
    opts = build_ydl_opts(DownloadOptions(no_playlist=True, playlist_items="1-5,8"))
    assert opts["noplaylist"] is True
    assert opts["playlist_items"] == "1-5,8"


def test_subtitles():
    opts = build_ydl_opts(
        DownloadOptions(
            write_subtitles=True, write_auto_subs=True,
            subtitle_langs="en,de", embed_subtitles=True,
        )
    )
    assert opts["writesubtitles"] is True
    assert opts["writeautomaticsub"] is True
    assert opts["subtitleslangs"] == ["en", "de"]
    assert "FFmpegEmbedSubtitle" in pp_keys(opts)


def test_metadata_and_thumbnail():
    opts = build_ydl_opts(DownloadOptions(embed_metadata=True, embed_thumbnail=True))
    keys = pp_keys(opts)
    assert "FFmpegMetadata" in keys
    assert "EmbedThumbnail" in keys
    assert opts["writethumbnail"] is True  # implied by --embed-thumbnail


def test_sponsorblock():
    opts = build_ydl_opts(DownloadOptions(sponsorblock_remove=["sponsor", "intro"]))
    sb = [pp for pp in opts["postprocessors"] if pp["key"] == "SponsorBlock"]
    assert sb and {"sponsor", "intro"} <= set(sb[0]["categories"])
    assert "ModifyChapters" in pp_keys(opts)


def test_network():
    opts = build_ydl_opts(
        DownloadOptions(proxy="socks5://127.0.0.1:9050", rate_limit="2M",
                        retries=3, concurrent_fragments=4)
    )
    assert opts["proxy"] == "socks5://127.0.0.1:9050"
    assert opts["ratelimit"] == 2 * 1024 * 1024
    assert opts["retries"] == 3
    assert opts["concurrent_fragment_downloads"] == 4


def test_cookies_from_browser():
    opts = build_ydl_opts(DownloadOptions(cookies_from_browser="firefox"))
    assert opts["cookiesfrombrowser"][0] == "firefox"


def test_extra_args_override_everything():
    opts = build_ydl_opts(DownloadOptions(max_height=1080, extra_args="-f worst"))
    assert opts["format"] == "worst"


def test_invalid_extra_args_raise_options_error():
    with pytest.raises(OptionsError):
        build_ydl_opts(DownloadOptions(extra_args="--no-such-flag"))
    with pytest.raises(OptionsError):
        build_ydl_opts(DownloadOptions(rate_limit="not-a-rate"))


def test_options_roundtrip_json():
    original = DownloadOptions(mode="audio", audio_format="opus", playlist_items="3-7")
    restored = DownloadOptions.model_validate_json(original.model_dump_json())
    assert restored == original
