# tests/test_detail.py
"""On-demand information dialog: plot, cast, director and writers from /v1/title, opened from the context menu."""
import xbmc
import xbmcgui

from resources.lib import detail
from tests.conftest import FakeListItem
from tests.listing_support import BASE, movie, run, series

FULL = {
    "id": "tt0000001", "type": "movie", "title": "Pelisky", "year": 1999, "overview": "Popis filmu", "tagline": "Hlaska",
    "runtime": 118, "poster_url": "https://i/p.jpg", "backdrop_url": "https://i/b.jpg",
    "directors": ["Jan Hrebejk"], "writers": ["Petr Jarchovsky"],
    "cast": [{"name": "Jiri Kodet", "role": "Sebesta", "photo_url": "https://i/k.jpg"}, {"name": "Bez Role"}]}


class FakeActor:
    def __init__(self, name="", role="", order=-1, thumbnail=""):
        self.name, self.role, self.order, self.thumbnail = name, role, order, thumbnail


def test_build_fills_plot_cast_and_crew(monkeypatch):
    monkeypatch.setattr(xbmc, "Actor", FakeActor)
    monkeypatch.setattr(xbmcgui, "ListItem", FakeListItem)
    tag = detail.build(FULL).getVideoInfoTag().calls
    assert tag["setPlot"] == ("Popis filmu",) and tag["setTagLine"] == ("Hlaska",) and tag["setDuration"] == (7080,)
    assert tag["setDirectors"] == (["Jan Hrebejk"],) and tag["setWriters"] == (["Petr Jarchovsky"],)
    actors = tag["setCast"][0]
    assert [(a.name, a.role, a.order, a.thumbnail) for a in actors] == [
        ("Jiri Kodet", "Sebesta", 0, "https://i/k.jpg"), ("Bez Role", "", 1, "")]


def test_build_series_and_sparse_data(monkeypatch):
    monkeypatch.setattr(xbmcgui, "ListItem", FakeListItem)
    item = detail.build({"id": "tt0000009", "type": "series", "title": "Show"})
    calls = item.getVideoInfoTag().calls
    assert calls["setMediaType"] == ("tvshow",) and calls["setTvShowTitle"] == ("Show",)
    assert "setPlot" not in calls and "setCast" not in calls


def test_detail_action_opens_the_info_dialog(ui, cat, monkeypatch):
    shown = []
    monkeypatch.setattr(xbmcgui.Dialog, "info", lambda self, item: shown.append(item), raising=False)
    monkeypatch.setattr(xbmc, "Actor", FakeActor)
    cat.data["title"] = dict(FULL)
    run("?action=detail&id=tt0000001")
    assert len(shown) == 1 and shown[0].getLabel() == "Pelisky (1999)" and cat.calls == [("title", "tt0000001")]


def test_detail_action_rejects_a_malformed_id(ui, cat):
    run("?action=detail&id=bad")
    assert cat.calls == [] and any(d[0] == "notification" for d in ui.dialogs)


def test_movies_and_series_carry_the_information_context_entry(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=titles&kind=movie&letter=K")
    cat.data["titles"] = {"has_more": False, "items": [series(2)]}
    run("?action=titles&kind=series&letter=S")
    menus = [entry[1].context for entry in ui.entries() if hasattr(entry[1], "context")]
    assert menus == [[("Information", f"RunPlugin({BASE}?action=detail&id=tt0000001)")],
                     [("Information", f"RunPlugin({BASE}?action=detail&id=tt0000002)")]]
