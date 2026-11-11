"""Subscription filters: which items a subscription leaves out.

One function judges an item twice: from the playlist listing (before anything is
queued) and from yt-dlp's full details (inside the download). Both use yt-dlp's
field names. A field that is missing is never a reason to leave an item out: the
listing knows titles, links and live state, but the upload date usually only
shows up in the full details."""

import sqlite3

from .models import SubscriptionFilters

LIVE = {"is_live", "is_upcoming", "was_live", "post_live"}


def of(subscription: sqlite3.Row | None) -> SubscriptionFilters | None:
    """The filters of a subscription row; None when it has none set."""
    if subscription is None or not subscription["filters_json"]:
        return None
    filters = SubscriptionFilters.model_validate_json(subscription["filters_json"])
    return filters if filters.model_dump(exclude_defaults=True) else None


def item_key(info: dict) -> tuple[str, str] | None:
    """(extractor, video id) as the archive spells them; None if either is unknown."""
    extractor = info.get("extractor_key") or info.get("ie_key")
    return (extractor.lower(), str(info["id"])) if extractor and info.get("id") else None


def reject_reason(info: dict, filters: SubscriptionFilters) -> str | None:
    title = info.get("title")
    if filters.title and title and filters.title.lower() not in title.lower():
        return f"title does not contain “{filters.title}”"
    # YouTube lists Shorts with a /shorts/ link; nothing in the details marks them.
    links = (info.get(key) or "" for key in ("url", "original_url", "webpage_url"))
    if filters.skip_shorts and any("/shorts/" in link for link in links):
        return "is a Short"
    if filters.skip_live and (
        info.get("live_status") in LIVE or info.get("is_live") or info.get("was_live")
    ):
        return "is a live stream"
    day = info.get("upload_date")  # YYYYMMDD
    if filters.after and day and day < filters.after.strftime("%Y%m%d"):
        return f"uploaded before {filters.after.isoformat()}"
    return None
