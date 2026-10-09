# resources/lib/listing_recent.py
"""Recently watched screen: movies and the last episode per series, taken from Kodi's own database."""
from concurrent.futures import ThreadPoolExecutor

import xbmcgui

from . import api, items, recent, texts, urls
from . import listing_common as common
from .const import S_NO_RESULTS
from .log import log

WORKERS = 6


def _title(catalog, tt):
    """Catalog data for one id; a title the catalog cannot give is shown by its id instead of failing the page."""
    try:
        return catalog.title(tt) or {}
    except api.ApiError as exc:
        if exc.kind in (api.NOT_CONFIGURED, api.BAD_URL, api.AUTH, api.CERT):
            raise  # a setup problem hits every row: let the router explain it once
        log(f"recent: no catalog data for {tt} ({exc.kind})")
        return {}


def _episode_entry(tt, season, number, data, catalog):
    title = data.get("title") or tt
    item = xbmcgui.ListItem(label=f"{title} S{season:02d}E{number:02d}", offscreen=True)
    tag = item.getVideoInfoTag()
    tag.setMediaType("episode")
    tag.setTvShowTitle(title)
    tag.setSeason(season)
    tag.setEpisode(number)
    url = catalog.poster_url(tt)
    if url:
        item.setArt({"poster": url, "thumb": url, "icon": url})
    item.setProperty("IsPlayable", "true")
    return urls.nokturno_episode_url(tt, season, number), item, False


def recently_watched(handle, params):
    catalog = api.Catalog()
    found = recent.recent()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        details = list(pool.map(lambda entry: _title(catalog, entry[1]), found))
    entries = []
    for entry, data in zip(found, details, strict=True):
        if entry[0] == "movie":
            entries.append(items.movie_item(dict(data, id=entry[1]), catalog))
        else:
            entries.append(_episode_entry(entry[1], entry[2], entry[3], data, catalog))
    if not entries:
        common.notify(texts.t(S_NO_RESULTS))
    common.show(handle, entries, "videos")
