# resources/lib/detail.py
"""Full information for one title (plot, cast, director, writers), fetched on demand and shown in Kodi's info dialog.

Lists stay light (one request per page); the heavy TMDB detail is only requested when the user opens the context menu
entry "Information" of a title, which runs action=detail.
"""
import xbmc
import xbmcgui

from . import api, items
from .urls import check_tt


def _people(tag, data):
    cast = [xbmc.Actor(p["name"], p.get("role") or "", index, p.get("photo_url") or "")
            for index, p in enumerate(data.get("cast") or []) if p.get("name")]
    if cast:
        tag.setCast(cast)
    if data.get("directors"):
        tag.setDirectors(list(data["directors"]))
    if data.get("writers"):
        tag.setWriters(list(data["writers"]))


def build(data):
    """A fully filled ListItem for the info dialog from the catalog's /v1/title answer."""
    series = data.get("type") == "series"
    item = xbmcgui.ListItem(label=items.label_of(data), offscreen=True)
    tag = item.getVideoInfoTag()
    tag.setMediaType("tvshow" if series else "movie")
    items.fill_title(tag, data)
    if series:
        tag.setTvShowTitle(data.get("title") or "")
    if data.get("overview"):
        tag.setPlot(data["overview"])
    if data.get("tagline"):
        tag.setTagLine(data["tagline"])
    if data.get("runtime"):
        tag.setDuration(int(data["runtime"]) * 60)
    _people(tag, data)
    art = {key: data[src] for key, src in (("poster", "poster_url"), ("fanart", "backdrop_url")) if data.get(src)}
    if art:
        art.setdefault("thumb", art.get("poster", ""))
        item.setArt(art)
    return item


def show(handle, params):
    """RunPlugin target: open the info dialog for params['id']."""
    tt = check_tt(params.get("id"))
    data = api.Catalog().title(tt) or {}
    data.setdefault("id", tt)
    xbmcgui.Dialog().info(build(data))
