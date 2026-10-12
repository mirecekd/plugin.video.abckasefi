# tests/test_api_filters.py
"""Catalog.titles/prefixes/genres: the genre, origin and flat filters are sent only when set."""

from resources.lib import api


def test_catalog_filters_are_sent_only_when_set(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "fetch", lambda base, token, path, params=None, **kw: calls.append((path, params)) or {})
    cat = api.Catalog("http://h:8090", "tok", "cs")
    cat.titles("series", None, "rating", 1, 50, genre="Sci-Fi", origin=True, flat=True)
    cat.titles("series", None, "rating", 1, 50, flat=True)
    cat.titles("series", "A", "name", 1, 50, genre="", origin=False, flat=False)
    cat.genres("movie")
    cat.genres("series", origin=True)
    cat.prefixes("series", "", genre="Crime", origin=True)
    cat.prefixes("series", "ar")
    base = {"type": "series", "letter": None, "sort": "rating", "page": 1, "per_page": 50, "lang": "cs"}
    assert calls[0] == ("/v1/titles", dict(base, genre="Sci-Fi", origin="czsk", flat=1))
    assert calls[1] == ("/v1/titles", dict(base, flat=1))
    assert calls[2] == ("/v1/titles", dict(base, letter="A", sort="name"))
    assert calls[3] == ("/v1/genres", {"type": "movie"})
    assert calls[4] == ("/v1/genres", {"type": "series", "origin": "czsk"})
    assert calls[5] == ("/v1/prefixes", {"type": "series", "prefix": "", "genre": "Crime", "origin": "czsk"})
    assert calls[6] == ("/v1/prefixes", {"type": "series", "prefix": "ar"})
