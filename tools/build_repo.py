# tools/build_repo.py
"""Build the static Kodi repository site: zips, addons.xml and the sha256 files.

Usage:  python3 tools/build_repo.py --out site [--base-url URL] [--tags]

Layout written to --out (this is what GitHub Pages serves):
  addons.xml, addons.xml.sha256
  plugin.video.abckasefi/plugin.video.abckasefi-<ver>.zip (+ .sha256), icon.png, fanart.png
  repository.abckasefi/repository.abckasefi-<ver>.zip (+ .sha256), icon.png
  index.html            (a plain link list, so the folder also works as a Kodi "file manager" source)

With --tags every `git tag -l 'v*'` is rebuilt from `git archive`, so older zips stay online (a Pages deploy
replaces the whole site, and clients holding an older addons.xml still ask for older zips). addons.xml always
advertises the NEWEST published version, whichever of the working tree or a tag it comes from.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import repo_tags
import repo_zip
from defusedxml import ElementTree
from repo_zip import PLUGIN_ID, REPO_ID, version_key

ROOT = Path(__file__).resolve().parent.parent


def set_base_url(repo_addon_xml, base_url):
    """Point the repository add-on at the site it is published on (placeholder BASE_URL_PLACEHOLDER)."""
    return repo_addon_xml.replace("BASE_URL_PLACEHOLDER", base_url.rstrip("/"))


def collect_versions(tags):
    """({version: zip bytes}, {version: addon.xml text}); the working tree wins over a tag with the same version."""
    current = repo_zip.addon_version(ROOT / "addon.xml")
    versions = {current: repo_zip.make_zip(ROOT, PLUGIN_ID)}
    manifests = {current: (ROOT / "addon.xml").read_text(encoding="utf-8")}
    for tag in (repo_tags.git_tags(ROOT) if tags else []):
        built = repo_tags.zip_from_tag(ROOT, tag)
        if built and built[0] not in versions:
            versions[built[0]], manifests[built[0]] = built[1], built[2]
    return versions, manifests


def write_repository_addon(repo_dir, base_url):
    """repository.abckasefi: its addon.xml points at the published site. Returns (version, addon.xml text)."""
    repo_xml = set_base_url((ROOT / REPO_ID / "addon.xml").read_text(encoding="utf-8"), base_url)
    version = ElementTree.fromstring(repo_xml).attrib["version"]
    with tempfile.TemporaryDirectory() as staging:
        folder = Path(staging)
        (folder / "addon.xml").write_text(repo_xml, encoding="utf-8")
        shutil.copy2(ROOT / REPO_ID / "icon.png", folder / "icon.png")
        repo_zip.write_with_hash(repo_dir, f"{REPO_ID}-{version}.zip", repo_zip.make_zip(folder, REPO_ID))
    shutil.copy2(ROOT / REPO_ID / "icon.png", repo_dir / "icon.png")
    (repo_dir / "addon.xml").write_text(repo_xml, encoding="utf-8")
    return version, repo_xml


def build(out, base_url, tags=False):
    """Write the whole site to `out`; returns the sorted list of plugin versions published."""
    out = Path(out)
    try:
        shutil.rmtree(out)
    except FileNotFoundError:
        out.parent.mkdir(parents=True, exist_ok=True)  # first build: nothing to clear yet
    out.mkdir(parents=True)
    versions, manifests = collect_versions(tags)
    plugin_dir = out / PLUGIN_ID
    for version, data in versions.items():
        repo_zip.write_with_hash(plugin_dir, f"{PLUGIN_ID}-{version}.zip", data)
    for asset in ("icon.png", "fanart.png"):
        shutil.copy2(ROOT / asset, plugin_dir / asset)
    repo_version, repo_xml = write_repository_addon(out / REPO_ID, base_url)
    newest = max(versions, key=version_key)
    addons = repo_zip.build_addons_xml([manifests[newest], repo_xml]).encode("utf-8")
    (out / "addons.xml").write_bytes(addons)
    (out / "addons.xml.sha256").write_text(repo_zip.sha256_hex(addons) + "\n", encoding="utf-8")
    (out / "index.html").write_text(repo_zip.index_html(versions, repo_version), encoding="utf-8")
    return sorted(versions, key=version_key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="site")
    parser.add_argument("--base-url", default="https://mirecekd.github.io/plugin.video.abckasefi")
    parser.add_argument("--tags", action="store_true", help="also rebuild every v* git tag so old zips stay online")
    args = parser.parse_args(argv)
    published = build(args.out, args.base_url, tags=args.tags)
    print(f"built {args.out}: plugin versions {', '.join(published)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
