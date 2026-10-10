# resources/lib/listing_series.py
"""Series drill-down screens: seasons of a series and episodes of a season, with Kodi's watched state."""

from . import api, items, texts, totals, watched
from . import listing_common as common
from .const import S_NO_EPISODES, S_NO_RESULTS, S_SEASON_N, S_SPECIALS
from .urls import check_tt

EPISODE_LABEL_MASK = "%H. %T"  # Kodi masks: %H episode number, %T title -> "18. Name"


def season_label(season, name):
    """The catalog's season name, or a localized 'Season N' / 'Specials' when it has none."""
    if name:
        return str(name)
    return texts.t(S_SPECIALS) if season == 0 else texts.tf(S_SEASON_N, season)


def seasons(handle, params):
    tt = check_tt(params.get("id"))
    catalog = api.Catalog()
    data = catalog.seasons(tt) or {}
    if data.get("note"):
        common.notify(str(data["note"]))
    state = watched.load()
    entries = []
    for entry in data.get("seasons") or []:
        number, count = int(entry["season"]), int(entry.get("episodes") or 0)
        progress = watched.season_progress(state, tt, number, count)
        entries.append(items.season_item(tt, number, season_label(number, entry.get("name")), count, catalog, progress))
    if data.get("seasons"):  # remember the sizes so title lists can mark a fully watched series
        totals.save(tt, {int(e["season"]): int(e.get("episodes") or 0) for e in data["seasons"]})
    if not entries and not data.get("note"):
        common.notify(texts.t(S_NO_RESULTS))
    common.show(handle, entries, "seasons")


def episodes(handle, params):
    tt = check_tt(params.get("id"))
    season = int(params.get("season", ""))
    catalog = api.Catalog()
    data = catalog.episodes(tt, season) or {}
    series_title = (catalog.title(tt) or {}).get("title", "")
    entries = [
        items.episode_item(tt, season, entry, series_title, catalog)
        for entry in sorted(data.get("episodes") or [], key=lambda e: int(e["episode"]))
    ]
    if not entries:
        common.notify(texts.t(S_NO_EPISODES))
    common.show(handle, entries, "episodes", label_mask=EPISODE_LABEL_MASK)
