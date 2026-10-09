# resources/lib/listing_page.py
"""Pieces shared by the paged listing screens: folder entries, the sort switcher and closing a page."""

from . import listing_common as common
from . import texts, urls
from .const import (
    S_NEXT_PAGE,
    S_NO_RESULTS,
    S_SORT_NAME,
    S_SORT_RATING,
    S_SORT_TMDB,
    S_SORT_VOTES,
    S_SORT_YEAR,
)
from .items import folder_item

SORT_LABELS = {
    "name": S_SORT_NAME,
    "rating": S_SORT_RATING,
    "votes": S_SORT_VOTES,
    "year": S_SORT_YEAR,
    "tmdb": S_SORT_TMDB,
}


def folder(label, **params):
    return folder_item(label, urls.build_url(**params))


def show_folders(handle, entries):
    common.show(handle, entries, "files")


def sort_switch(sort, order, **params):
    """Folder that shows the current ordering and the next one in `order`, and opens the listing sorted by it."""
    following = order[(order.index(sort) + 1) % len(order)]
    label = f"{texts.t(SORT_LABELS[sort])} -> {texts.t(SORT_LABELS[following])}"
    return folder(label, **dict(params, sort=following, page=1))


def finish_page(handle, catalog, data, kind, page, next_params, head=()):
    """Close a paged listing: head items, API items, then a 'Next page' folder when the API says there is more."""
    entries = list(head) + common.entries_for(data, catalog, kind)
    if not data.get("items") and page == 1:
        common.notify(texts.t(S_NO_RESULTS))
    if data.get("has_more"):
        entries.append(folder(texts.t(S_NEXT_PAGE), **dict(next_params, page=page + 1)))
    common.show(handle, entries, common.content_for(data, kind), update=page > 1)
