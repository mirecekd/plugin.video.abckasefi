# tools/repo_pages.py
"""Plain index.html link lists for every published folder, so the whole site works as a Kodi file-manager source."""

import html
from pathlib import Path

from repo_zip import PLUGIN_ID, REPO_ID, version_key

SITE_TITLE = "ABCKASEFI Kodi repository"


def index_html(title, links):
    """A minimal page in the style of the Nokturno repository: a list of relative links (href, text)."""
    items = "\n".join(
        f'<li><a href="{html.escape(href, quote=True)}">{html.escape(text)}</a></li>' for href, text in links
    )
    safe_title = html.escape(title)
    return f'<!doctype html><meta charset="utf-8"><title>{safe_title}</title>\n<h1>{safe_title}</h1>\n<ul>\n{items}\n</ul>\n'


def _with_hash(name):
    return [(name, name), (f"{name}.sha256", f"{name}.sha256")]


def write_pages(out, plugin_versions, repo_version):
    """Write index.html into the site root and into each of its two add-on folders."""
    out = Path(out)
    root_links = _with_hash("addons.xml") + [(f"{PLUGIN_ID}/", f"{PLUGIN_ID}/"), (f"{REPO_ID}/", f"{REPO_ID}/")]
    plugin_links = []
    for version in sorted(plugin_versions, key=version_key, reverse=True):
        plugin_links += _with_hash(f"{PLUGIN_ID}-{version}.zip")
    plugin_links += [("icon.png", "icon.png"), ("fanart.png", "fanart.png")]
    repo_links = (
        _with_hash(f"{REPO_ID}.zip")
        + _with_hash(f"{REPO_ID}-{repo_version}.zip")
        + [("addon.xml", "addon.xml"), ("icon.png", "icon.png")]
    )
    for folder, links in ((out, root_links), (out / PLUGIN_ID, plugin_links), (out / REPO_ID, repo_links)):
        (folder / "index.html").write_text(index_html(SITE_TITLE, links), encoding="utf-8")
