# resources/lib/plot_fallback.py
"""Plot text for list items whose catalog answer has no overview: genres and IMDb rating, from fields always present."""

from . import texts
from .const import GENRE_STRINGS


def votes_short(votes):
    """Compact vote count: 850 -> '850', 1234 -> '1.2k', 2900000 -> '2.9M' (the same in every language)."""
    if votes < 1000:
        return str(votes)
    if votes < 999_950:
        return f"{votes / 1000:.1f}k"
    return f"{votes / 1_000_000:.1f}M"


def _genres_text(data):
    names = [name for name in data.get("genres") or [] if isinstance(name, str) and name]
    return ", ".join(texts.t(GENRE_STRINGS[name]) if name in GENRE_STRINGS else name for name in names)


def _rating_text(data):
    """'IMDb 8.2 (2.9M)' for a reliable rating, else ''; mirrors the condition of items.fill_title."""
    if not data.get("rating") or not data.get("rating_reliable", True):
        return ""
    text = f"IMDb {float(data['rating']):.1f}"
    votes = int(data.get("votes") or 0)
    return f"{text} ({votes_short(votes)})" if votes > 0 else text


def fallback_plot(data):
    """'Drama, Krimi | IMDb 8.2 (2.9M)'; missing parts are left out, '' when there is nothing to show."""
    return " | ".join(part for part in (_genres_text(data), _rating_text(data)) if part)
