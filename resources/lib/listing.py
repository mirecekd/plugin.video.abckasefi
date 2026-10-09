# resources/lib/listing.py
"""Directory screens: root, kind menu, letters, titles (paged), search, TMDB lists. Each takes (handle, params)."""
import xbmcgui

from . import api, cfg, texts, urls
from . import listing_common as common
from .const import (
    S_MOVIES,
    S_NEXT_PAGE,
    S_NO_RESULTS,
    S_RECENT,
    S_SEARCH,
    S_SERIES,
    S_SETTINGS,
    S_SORT_NAME,
    S_SORT_RATING,
    S_SORT_YEAR,
    S_TMDB_LISTS,
    SORTS,
)
from .items import folder_item

SORT_LABELS = {"name": S_SORT_NAME, "rating": S_SORT_RATING, "year": S_SORT_YEAR}
KIND_LABELS = {"movie": S_MOVIES, "series": S_SERIES}
SEARCH_SORT = "popular"


def _folder(label, **params):
    return folder_item(label, urls.build_url(**params))


def _show_folders(handle, entries):
    common.show(handle, entries, "files")


def root(handle, params):
    _show_folders(handle, [
        _folder(texts.t(S_MOVIES), action="kind", kind="movie"),
        _folder(texts.t(S_SERIES), action="kind", kind="series"),
        _folder(texts.t(S_SEARCH), action="search"),
        _folder(texts.t(S_TMDB_LISTS), action="lists"),
        _folder(texts.t(S_RECENT), action="recent"),
        _folder(texts.t(S_SETTINGS), action="settings"),
    ])


def kind_menu(handle, params):
    kind = common.check_kind(params.get("kind"))
    _show_folders(handle, [
        _folder("A-Z", action="letters", kind=kind),
        _folder(texts.t(S_TMDB_LISTS), action="lists", kind=kind),
        _folder(texts.t(S_SEARCH), action="search", kind=kind),
    ])


def _letter_order(entry):
    letter = str(entry.get("letter", ""))
    return (letter == "0-9", letter)  # A-Z first, the digit bucket last


def letters(handle, params):
    kind = common.check_kind(params.get("kind"))
    data = api.Catalog().letters(kind)
    valid = [entry for entry in data or [] if common.LETTER_RE.match(str(entry.get("letter", "")))]
    _show_folders(handle, [
        _folder(f"{entry['letter']} ({entry.get('n', 0)})", action="titles", kind=kind, letter=entry["letter"], page=1)
        for entry in sorted(valid, key=_letter_order)])


def _finish_page(handle, catalog, data, kind, page, next_params, head=()):
    """Close a paged listing: head items, API items, then a 'Next page' folder when the API says there is more."""
    entries = list(head) + common.entries_for(data, catalog, kind)
    if not data.get("items") and page == 1:
        common.notify(texts.t(S_NO_RESULTS))
    if data.get("has_more"):
        entries.append(_folder(texts.t(S_NEXT_PAGE), **dict(next_params, page=page + 1)))
    common.show(handle, entries, common.content_for(data, kind), update=page > 1)


def titles(handle, params):
    kind = common.check_kind(params.get("kind"))
    letter = common.check_letter(params.get("letter"))
    sort = common.pick(params.get("sort"), SORTS, SORTS[0])
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    data = catalog.titles(kind, letter, sort, page, cfg.per_page())
    head = []
    if page == 1:
        following = SORTS[(SORTS.index(sort) + 1) % len(SORTS)]
        label = f"{texts.t(SORT_LABELS[sort])} -> {texts.t(SORT_LABELS[following])}"
        head.append(_folder(label, action="titles", kind=kind, letter=letter, sort=following, page=1))
    next_params = {"action": "titles", "kind": kind, "letter": letter, "sort": sort}
    _finish_page(handle, catalog, data, kind, page, next_params, head)


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
                entries.append(_folder(shown, action="tmdb_list", kind=each, key=key, page=1))
    _show_folders(handle, entries)


def tmdb_list(handle, params):
    kind = common.check_kind(params.get("kind"))
    key = common.check_key(params.get("key"))
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    data = catalog.tmdb_list(kind, key, page, cfg.per_page())
    _finish_page(handle, catalog, data, kind, page, {"action": "tmdb_list", "kind": kind, "key": key})
