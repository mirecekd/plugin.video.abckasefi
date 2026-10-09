# resources/lib/listing_prefix.py
"""Prefix drill-down screens: A -> AR -> ARM folders until a prefix has few enough titles to list them."""

import re

from . import api, cfg, texts
from . import listing_common as common
from .const import S_EXACT_FOLDER, S_NO_RESULTS, S_OTHER_FOLDER, SORTS
from .listing_page import finish_page, folder, show_folders, sort_switch

PREFIX_RE = re.compile(r"^[a-z0-9]{0,10}$")
MAX_DEPTH = 8  # a prefix this long lists its titles however many there are
DIGITS = "0123456789"


def check_prefix(value):
    """Lower-cased prefix of at most 10 characters a-z0-9 (empty allowed); anything else is a bad input."""
    text = (value or "").lower()
    if not PREFIX_RE.match(text):
        raise ValueError(f"bad prefix: {value!r}")
    return text


def _count(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _children(data, parent, digits_only):
    """Valid (prefix, n) pairs of an API answer that extend `parent` by one character, in the API's order."""
    found = []
    for child in data.get("children") or []:
        try:
            prefix = check_prefix(child.get("prefix"))
        except (ValueError, AttributeError):
            continue
        if len(prefix) != len(parent) + 1 or not prefix.startswith(parent):
            continue
        if not (digits_only and prefix[0] not in DIGITS):
            found.append((prefix, _count(child.get("n"))))
    return found


def _descend(catalog, kind, prefix, limit, digits):
    """Follow levels that offer a single choice; returns (prefix, exact, children, list_titles)."""
    while True:
        data = catalog.prefixes(kind, prefix) or {}
        digit_level = digits and not prefix
        children = _children(data, prefix, digit_level)
        exact = _count(data.get("exact")) if (prefix or digit_level) else 0
        if prefix and (_count(data.get("total")) <= limit or not children or len(prefix) >= MAX_DEPTH):
            return prefix, exact, children, True
        if len(children) == 1 and exact == 0:
            prefix = children[0][0]
            continue
        return prefix, exact, children, False


def _titles_page(handle, catalog, kind, prefix, exact, sort, page, action):
    data = catalog.titles(kind, None, sort, page, cfg.per_page(), prefix, exact)
    scope = {"action": action, "kind": kind, "prefix": prefix}
    if exact:
        scope["exact"] = 1
    head = [sort_switch(sort, SORTS, **scope)] if page == 1 else []
    finish_page(handle, catalog, data, kind, page, dict(scope, sort=sort), head)


def _folders(handle, kind, prefix, exact, children):
    entries = []
    if exact and prefix:
        label = texts.tf(S_EXACT_FOLDER, prefix.upper(), exact)
        entries.append(folder(label, action="titles", kind=kind, prefix=prefix, exact=1, page=1))
    elif exact:  # titles without any latin letter or digit; only the old digit bucket lists them
        entries.append(folder(texts.tf(S_OTHER_FOLDER, exact), action="titles", kind=kind, letter="0-9", page=1))
    for child, count in children:
        entries.append(folder(f"{child.upper()} ({count})", action="prefix", kind=kind, prefix=child))
    if not entries:
        common.notify(texts.t(S_NO_RESULTS))
    show_folders(handle, entries)


def prefix_screen(handle, params):
    """action=prefix: folders for the next characters, or the paged titles once the prefix is specific enough."""
    kind = common.check_kind(params.get("kind"))
    prefix = check_prefix(params.get("prefix"))
    sort = common.pick(params.get("sort"), SORTS, SORTS[0])
    page = common.page_number(params.get("page"))
    digits = params.get("digits") == "1"
    catalog = api.Catalog()
    prefix, exact, children, list_titles = _descend(catalog, kind, prefix, cfg.per_page(), digits)
    if list_titles:
        _titles_page(handle, catalog, kind, prefix, False, sort, page, "prefix")
    else:
        _folders(handle, kind, prefix, exact, children)


def titles_screen(handle, params):
    """action=titles with a prefix (the 'exact' folder, or a plain prefix listing): paged titles only."""
    kind = common.check_kind(params.get("kind"))
    prefix = check_prefix(params.get("prefix"))
    if not prefix:
        raise ValueError("empty prefix")
    sort = common.pick(params.get("sort"), SORTS, SORTS[0])
    page = common.page_number(params.get("page"))
    catalog = api.Catalog()
    _titles_page(handle, catalog, kind, prefix, params.get("exact") == "1", sort, page, "titles")
