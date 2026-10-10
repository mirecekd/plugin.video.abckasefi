# tests/test_repo_pages.py
"""The published site: an index.html in every folder, links that resolve, a fixed repository zip, unchanged addons.xml."""

import re
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_repo
import repo_pages
import repo_zip

BASE = "https://example.github.io/plugin.video.abckasefi"
PLUGIN = "plugin.video.abckasefi"
REPO = "repository.abckasefi"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("pages") / "site"
    build_repo.build(out, BASE)
    return out


def _hrefs(page):
    return re.findall(r'<a href="([^"]*)"', page.read_text(encoding="utf-8"))


def test_every_folder_has_an_index_html(site):
    folders = [site, *(p for p in site.rglob("*") if p.is_dir())]
    assert {p.relative_to(site).as_posix() for p in folders} == {".", PLUGIN, REPO}
    for folder in folders:
        assert (folder / "index.html").is_file(), folder


def test_every_link_points_at_an_existing_file_or_a_folder_with_an_index(site):
    for page in site.rglob("index.html"):
        links = _hrefs(page)
        assert links
        for href in links:
            assert "://" not in href and not href.startswith("/")
            target = page.parent / href
            assert (target / "index.html").is_file() if href.endswith("/") else target.is_file(), (page, href)


def test_every_published_file_is_linked_from_its_folder_page(site):
    for page in site.rglob("index.html"):
        listed = set(_hrefs(page))
        files = {p.name for p in page.parent.iterdir() if p.is_file() and p.name != "index.html"}
        assert files <= listed, (page, files - listed)


def test_pages_follow_the_nokturno_style(site):
    text = (site / "index.html").read_text(encoding="utf-8")
    assert text.startswith('<!doctype html><meta charset="utf-8"><title>ABCKASEFI Kodi repository</title>')
    assert "<script" not in text
    assert "<h1" not in text  # only the file list, no heading
    assert _hrefs(site / "index.html") == ["addons.xml", "addons.xml.sha256", f"{PLUGIN}/", f"{REPO}/"]


def test_plugin_page_lists_the_current_zip_hash_and_artwork(site):
    version = repo_zip.addon_version(build_repo.ROOT / "addon.xml")
    zip_name = f"{PLUGIN}-{version}.zip"
    assert _hrefs(site / PLUGIN / "index.html") == [zip_name, f"{zip_name}.sha256", "icon.png", "fanart.png"]


def test_fixed_repository_zip_matches_the_versioned_one(site):
    versioned = next(p for p in (site / REPO).glob(f"{REPO}-*.zip"))
    fixed = site / REPO / f"{REPO}.zip"
    assert fixed.read_bytes() == versioned.read_bytes()
    assert (site / REPO / f"{REPO}.zip.sha256").read_text().split()[0] == repo_zip.sha256_hex(fixed.read_bytes())
    assert _hrefs(site / REPO / "index.html")[:4] == [
        fixed.name,
        f"{fixed.name}.sha256",
        versioned.name,
        f"{versioned.name}.sha256",
    ]


def test_the_plugin_has_no_zip_without_a_version(site):
    assert not (site / PLUGIN / f"{PLUGIN}.zip").exists()


def test_addons_xml_is_built_only_from_the_two_manifests(site):
    repo_xml = build_repo.set_base_url((build_repo.ROOT / REPO / "addon.xml").read_text(encoding="utf-8"), BASE)
    plugin_xml = (build_repo.ROOT / "addon.xml").read_text(encoding="utf-8")
    expected = repo_zip.build_addons_xml([plugin_xml, repo_xml]).encode("utf-8")
    assert (site / "addons.xml").read_bytes() == expected
    assert (site / "addons.xml.sha256").read_text() == repo_zip.sha256_hex(expected) + "\n"


def test_plugin_zip_contains_no_site_pages(site):
    names = zipfile.ZipFile(next((site / PLUGIN).glob("*.zip"))).namelist()
    assert not [n for n in names if n.endswith("index.html") or "repo_pages" in n]


def test_index_html_escapes_text_and_quotes():
    page = repo_pages.index_html("A & B", [('x"y.zip', "<x>")])
    assert "<title>A &amp; B</title>" in page
    assert '<a href="x&quot;y.zip">&lt;x&gt;</a>' in page
