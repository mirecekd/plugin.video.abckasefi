# resources/lib/listing_genre.py
"""Filter screens: best rated (flat lists), genre folders and the Czech/Slovak menu. Filter results open best rated first."""

from . import api, cfg, texts
from . import listing_common as common
from .const import (
    FLAT_SORTS,
    GENRE_STRINGS,
    NOISE_GENRES,
    S_BEST_RATED,
    S_GENRES,
    S_MOST_VOTES,
    S_NEWEST,
    S_NO_RESULTS,
)
from .listing_page import finish_page, folder, show_folders, sort_switch


def genre_label(name):
    """Localized genre name; a genre without a translation is shown under its IMDb name."""
    string_id = GENRE_STRINGS.get(name)
    return texts.t(string_id) if string_id else name


def _genre_entries(data):
    """Valid (IMDb name, count) pairs in the API's order (biggest first), noise genres left out."""
    found = []
    for entry in data if isinstance(data, list) else []:
        try:
            name = common.check_genre(entry.get("genre"))
            count = max(0, int(entry.get("n") or 0))
        except (ValueError, TypeError, AttributeError):
            continue
        if name and name not in NOISE_GENRES:
            found.append((name, count))
    return found


def genres(handle, params):
    """action=genres: one folder per genre, 'Komedie (1234)'; each opens the flat list of that genre."""
    kind = common.check_kind(params.get("kind"))
    scope = common.scope_of(params)
    found = _genre_entries(api.Catalog().genres(kind, "origin" in scope))
    if not found:
        common.notify(texts.t(S_NO_RESULTS))
    entries = [
        folder(f"{genre_label(name)} ({count})", action="flat", kind=kind, genre=name, page=1, **_origin(scope))
        for name, count in found
    ]
    show_folders(handle, entries)


def _origin(scope):
    return {"origin": scope["origin"]} if "origin" in scope else {}


def flat(handle, params):
    """action=flat: the whole type, or one genre and/or the Czech/Slovak set, as one paged list; best rated first."""
    kind = common.check_kind(params.get("kind"))
    scope = common.scope_of(params)
    sort = common.pick(params.get("sort"), FLAT_SORTS, FLAT_SORTS[0])
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    data = catalog.titles(kind, None, sort, page, cfg.per_page(), None, False, scope.get("genre"), "origin" in scope, True)
    where = dict({"action": "flat", "kind": kind}, **scope)
    head = []
    if page == 1:
        head.append(sort_switch(sort, FLAT_SORTS, **where))
    finish_page(handle, catalog, data, kind, page, dict(where, sort=sort), head)


def czsk(handle, params):
    """action=czsk: menu of the Czech and Slovak productions (best rated, most votes, newest, A-Z, genres)."""
    kind = common.check_kind(params.get("kind"))
    show_folders(
        handle,
        [
            folder(texts.t(S_BEST_RATED), action="flat", kind=kind, origin=1, sort="rating", page=1),
            folder(texts.t(S_MOST_VOTES), action="flat", kind=kind, origin=1, sort="votes", page=1),
            folder(texts.t(S_NEWEST), action="flat", kind=kind, origin=1, sort="year", page=1),
            folder("A-Z", action="prefix", kind=kind, origin=1),
            folder(texts.t(S_GENRES), action="genres", kind=kind, origin=1),
        ],
    )
