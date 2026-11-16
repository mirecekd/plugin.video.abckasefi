# resources/lib/art.py
"""Poster URL taken from catalog list items: only direct TMDB image URLs are accepted."""

import re

_TMDB_IMAGE_URL = re.compile(r"https://image\.tmdb\.org/[\x21-\x7e]+")


def tmdb_poster_url(data):
    """`poster_url` of a list item dict when it is a plain https://image.tmdb.org/ URL, else ""."""
    url = data.get("poster_url")
    if isinstance(url, str) and _TMDB_IMAGE_URL.fullmatch(url):
        return url
    return ""
