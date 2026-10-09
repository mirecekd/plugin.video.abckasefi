# resources/lib/listing.py
"""Directory screens: root, kind menu, letters, titles (paged), search, TMDB lists. Each takes (handle, params)."""

import xbmcgui

from . import api, cfg, listing_prefix, texts
from . import listing_common as common
from .const import (
    LIST_SORTS,
    S_MOVIES,
    S_NO_RESULTS,
    S_RECENT,
    S_SEARCH,
    S_SERIES,
    S_SETTINGS,
    S_TMDB_LISTS,
    SORTS,
)
from .listing_page import finish_page, folder, show_folders, sort_switch

KIND_LABELS = {"movie": S_MOVIES, "series": S_SERIES}
SEARCH_SORT = "popular"


def root(handle, params):
    show_folders(
        handle,
        [
            folder(texts.t(S_MOVIES), action="kind", kind="movie"),
            folder(texts.t(S_SERIES), action="kind", kind="series"),
            folder(texts.t(S_SEARCH), action="search"),
            folder(texts.t(S_TMDB_LISTS), action="lists"),
            folder(texts.t(S_RECENT), action="recent"),
            folder(texts.t(S_SETTINGS), action="settings"),
        ],
    )


def kind_menu(handle, params):
    kind = common.check_kind(params.get("kind"))
    show_folders(
        handle,
        [
            folder(texts.t(S_RECENT), action="recent", kind=kind),
            folder("A-Z", action="letters", kind=kind),
            folder(texts.t(S_TMDB_LISTS), action="lists", kind=kind),
            folder(texts.t(S_SEARCH), action="search", kind=kind),
        ],
    )


def _letter_order(entry):
    letter = str(entry.get("letter", ""))
    return (letter == "0-9", letter)  # A-Z first, the digit bucket last


def _letter_folder(kind, entry):
    """A letter opens the prefix drill-down; the digit bucket opens it restricted to digits."""
    label = f"{entry['letter']} ({entry.get('n', 0)})"
    if entry["letter"] == "0-9":
        return folder(label, action="prefix", kind=kind, prefix="", digits=1)
    return folder(label, action="prefix", kind=kind, prefix=entry["letter"].lower())


def letters(handle, params):
    kind = common.check_kind(params.get("kind"))
    data = api.Catalog().letters(kind)
    valid = [entry for entry in data or [] if common.LETTER_RE.match(str(entry.get("letter", "")))]
    show_folders(handle, [_letter_folder(kind, entry) for entry in sorted(valid, key=_letter_order)])


def titles(handle, params):
    if params.get("prefix"):
        listing_prefix.titles_screen(handle, params)
        return
    kind = common.check_kind(params.get("kind"))
    letter = common.check_letter(params.get("letter"))
    sort = common.pick(params.get("sort"), SORTS, SORTS[0])
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    data = catalog.titles(kind, letter, sort, page, cfg.per_page())
    head = []
    if page == 1:
        head.append(sort_switch(sort, SORTS, action="titles", kind=kind, letter=letter))
    next_params = {"action": "titles", "kind": kind, "letter": letter, "sort": sort}
    finish_page(handle, catalog, data, kind, page, next_params, head)


def search(handle, params):
    """Ask for a query and list the matches (one page, most popular first). `kind` is optional: without it both."""
    kind = common.check_kind(params["kind"]) if params.get("kind") else None
    query = xbmcgui.Dialog().input(texts.t(S_SEARCH)).strip()
    if not query:
        common.close_failed(handle)
        return
    catalog = api.Catalog()
    data = catalog.search(query, kind, SEARCH_SORT, cfg.per_page())
    if not data.get("items"):
        common.notify(texts.t(S_NO_RESULTS))
    common.show(handle, common.entries_for(data, catalog, kind), common.content_for(data, kind))


def lists(handle, params):
    """TMDB lists as folders; `kind` limits them to movies or series, otherwise both kinds are listed."""
    kind = common.check_kind(params["kind"]) if params.get("kind") else None
    data = api.Catalog().lists() or {}
    entries = []
    for each in (kind,) if kind else ("movie", "series"):
        for key, label in (data.get(each) or {}).items():
            if common.KEY_RE.match(str(key)):
                shown = label if kind else f"{texts.t(KIND_LABELS[each])}: {label}"
                entries.append(folder(shown, action="tmdb_list", kind=each, key=key, page=1))
    show_folders(handle, entries)


def tmdb_list(handle, params):
    kind = common.check_kind(params.get("kind"))
    key = common.check_key(params.get("key"))
    sort = common.pick(params.get("sort"), LIST_SORTS, LIST_SORTS[0])
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    data = catalog.tmdb_list(kind, key, page, cfg.per_page(), sort)
    head = []
    if page == 1:
        head.append(sort_switch(sort, LIST_SORTS, action="tmdb_list", kind=kind, key=key))
    next_params = {"action": "tmdb_list", "kind": kind, "key": key, "sort": sort}
    finish_page(handle, catalog, data, kind, page, next_params, head)
