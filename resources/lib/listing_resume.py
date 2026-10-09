# resources/lib/listing_resume.py
"""Resume screen of one series: continue the last watched episode, the next episode, and all seasons."""

import math

import xbmcgui

from . import api, items, recent, texts, totals, urls
from . import listing_common as common
from .const import (
    S_ALL_SEASONS,
    S_LESS_THAN_MINUTE,
    S_MINUTES,
    S_RESUME_CONTINUE,
    S_RESUME_NEXT,
)
from .log import log

SETUP_ERRORS = (api.NOT_CONFIGURED, api.BAD_URL, api.AUTH, api.CERT)


def episode_code(season, episode):
    return f"S{season:02d}E{episode:02d}"


def minutes_label(seconds):
    """Resume time in whole minutes rounded up; under a minute it is "<1 min"."""
    if seconds < 60:
        return texts.t(S_LESS_THAN_MINUTE)
    return texts.tf(S_MINUTES, math.ceil(seconds / 60))


def next_episode(counts, season, episode):
    """(season, episode) after the given one, or None at the end of the series.

    Same season while it has more episodes, else the first episode of the next season. Season 0 (specials) is skipped
    when moving on to another season. `counts` is {season: episode_count}.
    """
    if season not in counts or episode < counts[season]:
        return season, episode + 1  # an unknown season size must not skip the rest of the season
    later = sorted(number for number, count in counts.items() if number > max(season, 0) and count > 0)
    return (later[0], 1) if later else None


def season_counts(tt, catalog):
    """{season: episode_count} from the plugin's cache, else from the catalog (and then cached); None when unknown.

    A catalog failure that is not a setup problem is logged and means "unknown", so the screen still opens.
    """
    known = totals.load().get(tt)
    if known:
        return known
    try:
        data = catalog.seasons(tt) or {}
    except api.ApiError as exc:
        if exc.kind in SETUP_ERRORS:
            raise  # a setup problem: let the router explain it
        log(f"resume: no season data for {tt} ({exc.kind})")
        return None
    counts = {int(e["season"]): int(e.get("episodes") or 0) for e in data.get("seasons") or []}
    if counts:
        totals.save(tt, counts)
    return counts or None


def _playable(tt, season, episode, label, catalog):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    tag = item.getVideoInfoTag()
    tag.setMediaType("episode")
    tag.setSeason(season)
    tag.setEpisode(episode)
    poster = catalog.poster_url(tt)
    if poster:
        item.setArt({"poster": poster, "thumb": poster, "icon": poster})
    item.setProperty("IsPlayable", "true")
    return urls.nokturno_episode_url(tt, season, episode), item, False


def resume_screen(handle, params):
    tt = urls.check_tt(params.get("id"))
    catalog = api.Catalog()
    entries = []
    last = recent.last_episode(tt)
    if last is not None:
        season, episode, state = last
        if state.resume_seconds > 0:
            label = texts.tf(S_RESUME_CONTINUE, episode_code(season, episode), minutes_label(state.resume_seconds))
            entries.append(_playable(tt, season, episode, label, catalog))
        counts = season_counts(tt, catalog)
        following = next_episode(counts, season, episode) if counts else None
        if following:
            label = texts.tf(S_RESUME_NEXT, episode_code(*following))
            entries.append(_playable(tt, following[0], following[1], label, catalog))
    entries.append(items.folder_item(texts.t(S_ALL_SEASONS), urls.build_url(action="seasons", id=tt)))
    common.show(handle, entries, "episodes")
