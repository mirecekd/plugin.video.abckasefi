# tests/listing_support.py
"""Fakes and helpers shared by the listing tests: catalog items, a recording Catalog, and a router runner."""

from resources.lib import router

BASE = "plugin://plugin.video.abckasefi/"


def movie(n, year=2000):
    return {"id": f"tt{n:07d}", "type": "movie", "title": f"Movie {n}", "year": year}


def series(n):
    return {"id": f"tt{n:07d}", "type": "series", "title": f"Show {n}", "year": 2010}


class FakeCatalog:
    """Replaces api.Catalog; `calls` records (method, args), `data` maps method name -> result or exception."""

    data = {}
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    def _do(self, name, *args):
        FakeCatalog.calls.append((name,) + args)
        result = FakeCatalog.data.get(name)
        if isinstance(result, Exception):
            raise result
        return result

    def letters(self, *a):
        return self._do("letters", *a)

    def titles(self, *a):
        return self._do("titles", *a)

    def search(self, *a):
        return self._do("search", *a)

    def lists(self, *a):
        return self._do("lists", *a)

    def tmdb_list(self, kind, key, page, per_page, sort="tmdb"):
        return self._do("tmdb_list", kind, key, page, per_page, sort)

    def seasons(self, *a):
        return self._do("seasons", *a)

    def episodes(self, *a):
        return self._do("episodes", *a)

    def title(self, *a):
        return self._do("title", *a)

    def ping(self, *a):
        return self._do("ping", *a)

    def poster_url(self, tt, size="w342"):
        return f"http://cat/v1/poster/{tt}"


def run(query, handle=7):
    router.run([BASE, str(handle), query])


def labels(ui):
    return [item.getLabel() for _path, item, _folder in ui.entries()]
