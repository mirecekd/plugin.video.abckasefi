# resources/lib/items.py
"""Kodi ListItem builders for API dicts. Movies and episodes are PLAYABLE items whose path is the Nokturno URL.

Rules that make Kodi's own watched feature work (see SPEC.md):
- path is built only by urls.py, so it is byte-identical on every listing;
- IsPlayable=true, isFolder=False;
- NO setPlaycount on movie/episode tags - the value stored in Kodi's database must win.
"""
import xbmcgui

from . import urls
from .const import S_SPECIALS, S_WATCHED_EPS

MOVIE, SERIES = "movie", "series"


def _tag(item, mediatype):
    tag = item.getVideoInfoTag()
    tag.setMediaType(mediatype)
    return tag


def _fill_title(tag, data):
    tag.setTitle(data.get("title") or "")
    if data.get("original") and data["original"] != data.get("title"):
        tag.setOriginalTitle(data["original"])
    if data.get("year"):
        tag.setYear(int(data["year"]))
    if data.get("genres"):
        tag.setGenres(list(data["genres"]))
    if data.get("rating") and data.get("rating_reliable", True):
        tag.setRating(float(data["rating"]), int(data.get("votes") or 0), "imdb", True)
    if data.get("id"):
        tag.setUniqueIDs({"imdb": data["id"]}, "imdb")
        tag.setIMDBNumber(data["id"])


def _label(data):
    title = data.get("title") or data.get("id") or "?"
    return f"{title} ({data['year']})" if data.get("year") else title


def _art(item, catalog, tt):
    url = catalog.poster_url(tt) if catalog else ""
    if url:
        item.setArt({"poster": url, "thumb": url, "icon": url})


def movie_item(data, catalog):
    """(path, ListItem, isFolder) for a playable movie."""
    item = xbmcgui.ListItem(label=_label(data), offscreen=True)
    _fill_title(_tag(item, MOVIE), data)
    _art(item, catalog, data["id"])
    item.setProperty("IsPlayable", "true")
    return urls.nokturno_movie_url(data["id"]), item, False


def series_item(data, catalog, watched=None):
    """(path, ListItem, isFolder) for a series folder; `watched` = (watched_episodes, total) or None."""
    item = xbmcgui.ListItem(label=_label(data), offscreen=True)
    tag = _tag(item, "tvshow")
    _fill_title(tag, data)
    tag.setTvShowTitle(data.get("title") or "")
    _art(item, catalog, data["id"])
    apply_progress(item, tag, watched)
    return urls.build_url(action="seasons", id=data["id"]), item, True


def season_item(tt, season, name, count, catalog, watched=None):
    label = name or (S_SPECIALS if season == 0 else "")
    item = xbmcgui.ListItem(label=str(label), offscreen=True)
    tag = _tag(item, "season")
    tag.setSeason(int(season))
    tag.setTitle(str(label))
    if count:
        item.setProperty("TotalEpisodes", str(count))
    apply_progress(item, tag, watched)
    return urls.build_url(action="episodes", id=tt, season=season), item, True


def episode_item(tt, season, data, series_title, catalog):
    number = int(data["episode"])
    label = f"{number}. {data.get('name') or ''}".strip()
    item = xbmcgui.ListItem(label=label, offscreen=True)
    tag = _tag(item, "episode")
    tag.setTitle(data.get("name") or label)
    tag.setTvShowTitle(series_title or "")
    tag.setSeason(int(season))
    tag.setEpisode(number)
    if data.get("overview"):
        tag.setPlot(data["overview"])
    if data.get("air_date"):
        tag.setFirstAired(data["air_date"])
    if data.get("runtime"):
        tag.setDuration(int(data["runtime"]) * 60)
    if data.get("still_url"):
        item.setArt({"thumb": data["still_url"], "icon": data["still_url"]})
    item.setProperty("IsPlayable", "true")
    return urls.nokturno_episode_url(tt, season, number), item, False


def folder_item(label, url, icon="DefaultFolder.png"):
    item = xbmcgui.ListItem(label=str(label), offscreen=True)
    item.setArt({"icon": icon})
    return url, item, True


def apply_progress(item, tag, watched):
    """Folders: Kodi never totals plugin folders, so mark them watched ourselves when every episode is."""
    if not watched:
        return
    done, total = watched
    item.setProperty("WatchedEpisodes", str(done))
    item.setProperty("TotalEpisodes", str(total))
    if total and done >= total:
        tag.setPlaycount(1)
    else:
        tag.setPlaycount(0)
    item.setProperty("UnWatchedEpisodes", str(max(0, total - done)))


def progress_label(done, total, template):
    """'3/10' style suffix; `template` is the localized S_WATCHED_EPS string with two {} placeholders."""
    return template.format(done, total)


PROGRESS_STRING_ID = S_WATCHED_EPS
