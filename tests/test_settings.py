from datetime import date

import yt_dlp

from yoink.api.settings import is_outdated

TODAY = date(2026, 11, 11)


def test_old_ytdlp_is_flagged():
    assert is_outdated("2026.7.4", TODAY)
    assert not is_outdated("2026.10.26", TODAY)
    assert not is_outdated("2026.10.26.232815", TODAY)  # nightly builds add a 4th part
    assert not is_outdated("unknown", TODAY)


def test_settings_report_it(client, monkeypatch):
    monkeypatch.setattr(yt_dlp.version, "__version__", date.today().strftime("%Y.%m.%d"))
    assert client.get("/api/settings").json()["yt_dlp_outdated"] is False
    monkeypatch.setattr(yt_dlp.version, "__version__", "2020.1.1")
    body = client.get("/api/settings").json()
    assert (body["yt_dlp_version"], body["yt_dlp_outdated"]) == ("2020.1.1", True)
