# tests/test_art.py
"""List item art: a direct https://image.tmdb.org/ `poster_url` wins, anything else falls back to the catalog URL."""

import pytest

from resources.lib import art, items
from tests.listing_support import FakeCatalog, movie, run, series

TMDB = "https://image.tmdb.org/t/p/w342/abc.jpg"
CATALOG_URL = "http://cat/v1/poster/tt0000001"
BUILDERS = [(movie, items.movie_item), (series, items.series_item)]


@pytest.mark.parametrize(("make", "build"), BUILDERS)
def test_valid_poster_url_is_used(ui, make, build):
    built = build(dict(make(1), poster_url=TMDB), FakeCatalog())
    assert built[1].art == {"poster": TMDB, "thumb": TMDB, "icon": TMDB}


@pytest.mark.parametrize(("make", "build"), BUILDERS)
def test_valid_poster_url_is_used_without_catalog(ui, make, build):
    built = build(dict(make(1), poster_url=TMDB), None)
    assert built[1].art["poster"] == TMDB


@pytest.mark.parametrize(("make", "build"), BUILDERS)
@pytest.mark.parametrize(
    "poster_url",
    [
        "",
        None,
        "http://image.tmdb.org/t/p/w342/abc.jpg",
        "https://evil.example/t/p/w342/abc.jpg",
        "https://image.tmdb.org.evil.example/abc.jpg",
        "https://image.tmdb.org/t/p/w342/a bc.jpg",
        "https://image.tmdb.org/t/p/w342/abc.jpg\n",
        " https://image.tmdb.org/t/p/w342/abc.jpg",
        "https://image.tmdb.org/t/p/w342/a\x00bc.jpg",
        42,
        ["https://image.tmdb.org/t/p/w342/abc.jpg"],
    ],
)
def test_invalid_poster_url_falls_back_to_catalog(ui, make, build, poster_url):
    built = build(dict(make(1), poster_url=poster_url), FakeCatalog())
    assert built[1].art == {"poster": CATALOG_URL, "thumb": CATALOG_URL, "icon": CATALOG_URL}


@pytest.mark.parametrize(("make", "build"), BUILDERS)
def test_missing_poster_url_falls_back_to_catalog(ui, make, build):
    assert build(make(1), FakeCatalog())[1].art["poster"] == CATALOG_URL


@pytest.mark.parametrize(("make", "build"), BUILDERS)
@pytest.mark.parametrize("poster_url", [None, "", "http://image.tmdb.org/x.jpg"])
def test_no_catalog_and_no_valid_poster_url_sets_no_art(ui, make, build, poster_url):
    built = build(dict(make(1), poster_url=poster_url), None)
    assert not hasattr(built[1], "art")


def test_titles_list_uses_poster_url(ui, cat):
    cat.data["titles"] = {
        "has_more": False,
        "items": [dict(movie(1), poster_url=TMDB), dict(movie(2), poster_url="http://x/y.jpg")],
    }
    run("?action=titles&kind=movie&letter=K&page=2")
    first, second = (item for _p, item, _f in ui.entries())
    assert first.art["poster"] == TMDB
    assert second.art["poster"] == "http://cat/v1/poster/tt0000002"


def test_tmdb_poster_url_helper():
    assert art.tmdb_poster_url({"poster_url": TMDB}) == TMDB
    assert art.tmdb_poster_url({}) == ""
