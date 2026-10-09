# tests/test_build_repo.py
"""The repository builder: layout Kodi expects, hashes that match, reproducible zips, old versions kept."""

import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from defusedxml import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_repo
import repo_zip

BASE = "https://example.github.io/plugin.video.abckasefi"
PLUGIN = "plugin.video.abckasefi"


def _node(parent, tag):
    """Child element `tag` of `parent`; fails the test with a clear message when it is missing."""
    found = parent.find(tag)
    assert found is not None, f"<{tag}> missing"
    return found


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "site"
    build_repo.build(out, BASE)
    return out


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_addons_xml_lists_plugin_and_repository_with_a_matching_sha256(site):
    root = ElementTree.parse(site / "addons.xml").getroot()
    assert [a.attrib["id"] for a in root.findall("addon")] == [PLUGIN, "repository.abckasefi"]
    assert (site / "addons.xml.sha256").read_text().split()[0] == _sha(site / "addons.xml")


def test_every_zip_has_a_sha256_file_that_matches(site):
    zips = list(site.rglob("*.zip"))
    assert len(zips) == 3  # plugin, repository with a version, repository under the fixed name
    for z in zips:
        assert Path(str(z) + ".sha256").read_text().split()[0] == _sha(z)


def test_plugin_zip_has_the_addon_folder_at_its_root_and_nothing_private(site):
    names = zipfile.ZipFile(next((site / PLUGIN).glob("*.zip"))).namelist()
    assert all(n.startswith(f"{PLUGIN}/") for n in names)
    for required in (
        "addon.xml",
        "default.py",
        "icon.png",
        "fanart.png",
        "resources/lib/router.py",
        "resources/settings.xml",
        "resources/lib/totals.py",
        "LICENSE",
    ):
        assert f"{PLUGIN}/{required}" in names, required
    banned = (
        "/.git",
        ".venv",
        "__pycache__",
        "/tests/",
        "/tools/",
        "/design/",
        "SPEC.md",
        ".pyc",
        "repository.abckasefi",
        ".github",
    )
    assert not [n for n in names if any(b in n for b in banned)]


def test_zip_version_matches_addon_xml_and_file_name(site):
    zip_path = next((site / PLUGIN).glob("*.zip"))
    version = repo_zip.addon_version(build_repo.ROOT / "addon.xml")
    assert zip_path.name == f"{PLUGIN}-{version}.zip"
    inner = zipfile.ZipFile(zip_path).read(f"{PLUGIN}/addon.xml")
    assert ElementTree.fromstring(inner).attrib["version"] == version


def test_repository_addon_points_at_the_published_site_with_sha256_and_zip(site):
    xml = (site / "repository.abckasefi" / "addon.xml").read_text()
    assert "BASE_URL_PLACEHOLDER" not in xml and BASE in xml
    node = _node(ElementTree.fromstring(xml), ".//dir")
    assert _node(node, "info").text == f"{BASE}/addons.xml"
    checksum = _node(node, "checksum")
    assert checksum.attrib["verify"] == "sha256" and checksum.text == f"{BASE}/addons.xml.sha256"
    datadir = _node(node, "datadir")
    assert datadir.attrib["zip"] == "true" and datadir.text == f"{BASE}/"
    assert (
        "repository.abckasefi/addon.xml"
        in zipfile.ZipFile(site / "repository.abckasefi" / "repository.abckasefi.zip").namelist()
    )


def test_icon_and_fanart_sit_where_kodi_looks_for_them(site):
    # Kodi fetches <datadir>/<id>/<asset path>; a missing icon shows a 404 on install
    assert (site / PLUGIN / "icon.png").exists() and (site / PLUGIN / "fanart.png").exists()
    assert (site / "repository.abckasefi" / "icon.png").exists()


def test_zips_are_reproducible(tmp_path):
    one, two = tmp_path / "a", tmp_path / "b"
    build_repo.build(one, BASE)
    build_repo.build(two, BASE)
    for z in one.rglob("*.zip"):
        assert z.read_bytes() == (two / z.relative_to(one)).read_bytes()


def test_make_zip_excludes_by_name_not_by_accident():
    assert not repo_zip.wanted(Path("tests/test_urls_cfg.py"))
    assert not repo_zip.wanted(Path("resources/lib/__pycache__/x.pyc"))
    assert repo_zip.wanted(Path("resources/lib/router.py"))
    assert repo_zip.wanted(Path("resources/language/resource.language.cs_cz/strings.po"))


def test_versions_sort_numerically_not_alphabetically():
    assert max(["0.9.0", "0.10.0", "0.2.0"], key=repo_zip.version_key) == "0.10.0"


# ---- --tags: older releases stay online and the index always advertises the NEWEST version ------------------
def _make_repo(tmp_path, working_version, tagged_versions):
    """A throwaway git repo shaped like the plugin, one commit+tag per tagged version, then the working tree."""
    repo = tmp_path / "r"
    (repo / "repository.abckasefi").mkdir(parents=True)
    root = build_repo.ROOT
    template = (root / "addon.xml").read_text()
    for name in ("icon.png", "fanart.png"):
        (repo / name).write_bytes((root / name).read_bytes())
    for name in ("addon.xml", "icon.png"):
        (repo / "repository.abckasefi" / name).write_bytes((root / "repository.abckasefi" / name).read_bytes())
    (repo / "default.py").write_text("# default.py\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    def write_manifest(version):
        # the real manifest changes version with every release: replace whatever the add-on tag carries
        (repo / "addon.xml").write_text(
            re.sub(r'(<addon id="plugin\.video\.abckasefi"[^>]*version=")[^"]*', rf"\g<1>{version}", template, count=1)
        )

    for version in tagged_versions:
        write_manifest(version)
        for cmd in (
            ["add", "-A"],
            ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", version],
            ["tag", f"v{version}"],
        ):
            subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)
    write_manifest(working_version)
    return repo


def _build_in(repo, out, monkeypatch):
    monkeypatch.setattr(build_repo, "ROOT", repo)
    return build_repo.build(out, BASE, tags=True)


def _advertised(out):
    root = ElementTree.parse(out / "addons.xml").getroot()
    return next(a.attrib["version"] for a in root.findall("addon") if a.attrib["id"] == PLUGIN)


def test_old_versions_are_rebuilt_from_git_tags(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, "0.2.0", ["0.1.0"])
    published = _build_in(repo, tmp_path / "out", monkeypatch)
    assert published == ["0.1.0", "0.2.0"]
    names = sorted(p.name for p in (tmp_path / "out" / PLUGIN).glob("*.zip"))
    assert names == [f"{PLUGIN}-0.1.0.zip", f"{PLUGIN}-0.2.0.zip"]
    assert _advertised(tmp_path / "out") == "0.2.0"


def test_index_advertises_the_newest_tag_when_the_working_tree_is_older(tmp_path, monkeypatch):
    # regression: the index was always read from the working tree, so a v0.2.0 tag was published but 0.1.0 advertised
    repo = _make_repo(tmp_path, "0.1.0", ["0.2.0"])
    out = tmp_path / "out"
    assert _build_in(repo, out, monkeypatch) == ["0.1.0", "0.2.0"]
    assert _advertised(out) == "0.2.0"
    inner = zipfile.ZipFile(out / PLUGIN / f"{PLUGIN}-0.2.0.zip").read(f"{PLUGIN}/addon.xml")
    assert ElementTree.fromstring(inner).attrib["version"] == "0.2.0"


def test_index_advertises_the_working_tree_when_it_is_newer_than_every_tag(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, "0.3.0", ["0.1.0", "0.2.0"])
    out = tmp_path / "out"
    assert _build_in(repo, out, monkeypatch) == ["0.1.0", "0.2.0", "0.3.0"]
    assert _advertised(out) == "0.3.0"


def test_a_tag_with_the_working_tree_version_is_not_duplicated(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, "0.1.0", ["0.1.0"])
    assert _build_in(repo, tmp_path / "out", monkeypatch) == ["0.1.0"]
    assert len(list((tmp_path / "out" / PLUGIN).glob("*.zip"))) == 1


def test_ten_is_newer_than_nine_in_the_index(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, "0.9.0", ["0.10.0"])
    out = tmp_path / "out"
    _build_in(repo, out, monkeypatch)
    assert _advertised(out) == "0.10.0"
