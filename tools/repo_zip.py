# tools/repo_zip.py
"""Zip and hash helpers for build_repo.py: reproducible add-on zips and their sha256 sidecar files."""

import hashlib
import io
import re
import zipfile
from pathlib import Path

from defusedxml import ElementTree

PLUGIN_ID = "plugin.video.abckasefi"
REPO_ID = "repository.abckasefi"
EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "tools",
    "tests",
    "site",
    "typings",
    "design",
    REPO_ID,
}
EXCLUDE_FILES = {".gitignore", "pyproject.toml", "pyrightconfig.json", "SPEC.md", ".DS_Store"}
EXCLUDE_SUFFIXES = (".pyc", ".zip")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # reproducible zips: same input, same bytes, same sha256


def version_key(version):
    """Sort key for dotted versions: '0.10.0' > '0.9.0'."""
    return [int(x) for x in re.findall(r"\d+", version)]


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def addon_version(addon_xml_path):
    # parses only this repository's own addon.xml files, never remote or user input
    return ElementTree.parse(addon_xml_path).getroot().attrib["version"]


def wanted(relative):
    parts = relative.parts
    if any(part in EXCLUDE_DIRS for part in parts[:-1]) or parts[0] in EXCLUDE_DIRS:
        return False
    return relative.name not in EXCLUDE_FILES and not relative.name.endswith(EXCLUDE_SUFFIXES)


def make_zip(source_dir, addon_id):
    """Zip `source_dir` with a top-level folder named exactly `addon_id` (what Kodi requires). Returns bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(source_dir).rglob("*")):
            relative = path.relative_to(source_dir)
            if path.is_dir() or not wanted(relative):
                continue
            info = zipfile.ZipInfo(f"{addon_id}/{relative.as_posix()}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def write_with_hash(directory, name, data):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(data)
    (directory / f"{name}.sha256").write_text(sha256_hex(data) + "\n", encoding="utf-8")


def strip_declaration(xml_text):
    return re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", xml_text)


def build_addons_xml(manifests):
    """addons.xml from addon.xml TEXTS (plugin first, repository second)."""
    body = "\n".join(strip_declaration(text).strip() for text in manifests)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n{body}\n</addons>\n'
