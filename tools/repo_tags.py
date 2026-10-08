# tools/repo_tags.py
"""Rebuild older plugin releases from git tags (`git archive`), so a Pages deploy keeps their zips online."""
import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import repo_zip

TAG_RE = re.compile(r"v\d+(\.\d+)*")


def _git(root, *args):
    """Run git (resolved to its full path) in `root` with fixed arguments; never raises, check .returncode."""
    exe = shutil.which("git")
    if exe is None:
        return subprocess.CompletedProcess(args, 127, b"", b"git not found")
    return subprocess.run([exe, *args], cwd=root, capture_output=True, check=False)  # noqa: S603 - fixed args


def git_tags(root):
    out = _git(root, "tag", "-l", "v*")
    return [t for t in out.stdout.decode("utf-8", "replace").split() if TAG_RE.fullmatch(t)]


def _extract(archive, work):
    if sys.version_info >= (3, 12):
        archive.extractall(work, filter="data")
    else:  # older Pythons have no extraction filter; the tarball comes from our own `git archive`
        archive.extractall(work)  # noqa: S202


def zip_from_tag(root, tag):
    """(version, zip bytes, addon.xml text) of the plugin as it was at `tag`; None if the tag is not buildable."""
    if not TAG_RE.fullmatch(tag):
        return None
    tar = _git(root, "archive", "--format=tar", tag)
    if tar.returncode != 0:
        return None
    with tempfile.TemporaryDirectory(prefix=f"abckasefi-{tag}-") as scratch:  # removed for us, errors included
        work = Path(scratch)
        with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as archive:
            _extract(archive, work)
        manifest = work / "addon.xml"
        if not manifest.exists():
            return None
        return (repo_zip.addon_version(manifest), repo_zip.make_zip(work, repo_zip.PLUGIN_ID),
                manifest.read_text(encoding="utf-8"))
