#!/usr/bin/env python3
"""Create and inspect a deterministic local release-candidate archive."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

from common import ROOT, load_json, sha256, write_text

EXCLUDED_PARTS = {".git", ".venv", "release", "build", "__pycache__"}


def public_files() -> list[Path]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    files = [ROOT / item.decode("utf-8") for item in tracked if item]
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    project = load_json(ROOT / "metadata/project.json")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != project["version"]:
        print("ERROR: VERSION and metadata/project.json disagree", file=sys.stderr)
        return 1
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f"version: {version}" not in citation:
        print("ERROR: CITATION.cff version disagrees", file=sys.stderr)
        return 1
    doi = project.get("doi")
    release_date = project.get("release_date")
    if not doi or not release_date:
        print("ERROR: DOI and release date must be set before tagging", file=sys.stderr)
        return 1
    if f"doi: {doi}" not in citation or f"date-released: {release_date}" not in citation:
        print("ERROR: CITATION.cff DOI or release date disagrees", file=sys.stderr)
        return 1

    tags = subprocess.run(
        ["git", "tag", "--list", f"v{version}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if tags:
        print(
            f"ERROR: v{version} already exists; this preparation must remain untagged",
            file=sys.stderr,
        )
        return 1

    release_dir = ROOT / "release"
    release_dir.mkdir(exist_ok=True)
    slug = "audio-acoustics-instruments-index"
    archive = release_dir / f"{slug}-v{version}.zip"
    archive.unlink(missing_ok=True)
    snapshot = date.fromisoformat(project["snapshot_date"])
    zip_timestamp = (max(snapshot.year, 1980), snapshot.month, snapshot.day, 0, 0, 0)
    prefix = f"{slug}-v{version}"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in public_files():
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{prefix}/{relative}", date_time=zip_timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.parent.name == "scripts" else 0o644) << 16
            handle.writestr(
                info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )

    digest = sha256(archive)
    write_text(release_dir / "SHA256SUMS", f"{digest}  {archive.name}")
    with zipfile.ZipFile(archive) as handle:
        bad = handle.testzip()
        if bad is not None:
            print(f"ERROR: corrupt archive entry: {bad}", file=sys.stderr)
            return 1
        names = handle.namelist()
        forbidden = [
            name for name in names if any(part in EXCLUDED_PARTS for part in Path(name).parts)
        ]
        if forbidden:
            print(f"ERROR: excluded paths in release archive: {forbidden}", file=sys.stderr)
            return 1

    print(f"Release candidate: {archive}")
    print(f"SHA-256: {digest}")
    print(f"Files: {len(names)}")
    print(f"DOI: {doi}")
    print(f"Release date: {release_date}")
    print("Tag check: no release tag exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
