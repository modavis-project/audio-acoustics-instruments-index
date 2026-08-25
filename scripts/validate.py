#!/usr/bin/env python3
"""Validate canonical data and all generated release representations."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from common import ROOT, load_json, load_jsonl, sha256


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


def validate_with_jsonschema(validator: Validator, path: Path, schema_path: Path) -> None:
    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError:
        validator.warnings.append("jsonschema is not installed; structural checks were used")
        return
    schema = load_json(schema_path)
    checker = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for index, item in enumerate(load_jsonl(path), 1):
        for error in checker.iter_errors(item):
            location = ".".join(str(part) for part in error.absolute_path)
            validator.errors.append(f"{path}:{index}:{location}: {error.message}")


def validate_canonical(validator: Validator) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    records = load_jsonl(ROOT / "data/repositories.jsonl")
    vocabulary = load_json(ROOT / "data/vocabularies/categories.json")
    scopes = load_json(ROOT / "data/vocabularies/scope-statuses.json")
    category_ids = {item["id"] for item in vocabulary["concepts"]}
    scope_ids = {item["id"] for item in scopes["concepts"]}
    required = {
        "catalogue_id",
        "full_name",
        "owner",
        "name",
        "html_url",
        "description_de",
        "primary_category",
        "scope_status",
        "snapshot_date",
        "record_status",
        "redirects_to",
    }
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    seen_urls: set[str] = set()
    expected_ids = [f"GHIAO-{index:04d}" for index in range(1, len(records) + 1)]

    validator.check(len(records) == 403, f"expected 403 canonical records, found {len(records)}")
    for index, record in enumerate(records, 1):
        prefix = f"data/repositories.jsonl:{index}"
        keys = set(record)
        validator.check(keys == required, f"{prefix}: unexpected key set {sorted(keys ^ required)}")
        catalogue_id = record.get("catalogue_id", "")
        validator.check(
            bool(re.fullmatch(r"GHIAO-\d{4}", catalogue_id)), f"{prefix}: invalid catalogue_id"
        )
        validator.check(
            catalogue_id not in seen_ids, f"{prefix}: duplicate catalogue_id {catalogue_id}"
        )
        seen_ids.add(catalogue_id)
        full_name = record.get("full_name", "")
        validator.check(
            full_name == f"{record.get('owner')}/{record.get('name')}",
            f"{prefix}: inconsistent full_name",
        )
        validator.check(
            full_name.casefold() not in seen_names, f"{prefix}: duplicate full_name {full_name}"
        )
        seen_names.add(full_name.casefold())
        expected_url = f"https://github.com/{full_name}"
        validator.check(
            record.get("html_url") == expected_url, f"{prefix}: html_url does not match full_name"
        )
        validator.check(expected_url.casefold() not in seen_urls, f"{prefix}: duplicate html_url")
        seen_urls.add(expected_url.casefold())
        validator.check(
            record.get("primary_category") in category_ids, f"{prefix}: unknown category"
        )
        validator.check(record.get("scope_status") in scope_ids, f"{prefix}: unknown scope_status")
        validator.check(
            record.get("record_status") in {"active", "merged"}, f"{prefix}: unknown record_status"
        )
        if record.get("record_status") == "merged":
            validator.check(
                bool(record.get("redirects_to")), f"{prefix}: merged record lacks redirect"
            )
        else:
            validator.check(
                record.get("redirects_to") is None, f"{prefix}: active record has redirect"
            )
        validator.check(
            len(record.get("description_de", "")) >= 20, f"{prefix}: description_de too short"
        )
        try:
            date.fromisoformat(record.get("snapshot_date", ""))
        except ValueError:
            validator.errors.append(f"{prefix}: invalid snapshot_date")

    validator.check(
        [item["catalogue_id"] for item in records] == expected_ids,
        "catalogue IDs are not sequential and ordered",
    )
    scope_counts = Counter(item["scope_status"] for item in records)
    validator.check(
        scope_counts == {"core": 353, "adjacent": 50},
        f"unexpected scope counts: {dict(scope_counts)}",
    )
    validator.check(len(category_ids) == 15, f"expected 15 categories, found {len(category_ids)}")
    record_ids = {item["catalogue_id"] for item in records}
    for record in records:
        if record.get("redirects_to"):
            validator.check(
                record["redirects_to"] in record_ids,
                f"{record['catalogue_id']}: redirect target missing",
            )
            validator.check(
                record["redirects_to"] != record["catalogue_id"],
                f"{record['catalogue_id']}: self redirect",
            )
    validator.check(
        Counter(item["record_status"] for item in records) == {"active": 402, "merged": 1},
        "unexpected record lifecycle counts",
    )
    validator.check(
        all(
            any(item["primary_category"] == category for item in records)
            for category in category_ids
        ),
        "one or more categories are unused",
    )
    return records, category_ids, scope_ids


def validate_snapshots(validator: Validator, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots = load_jsonl(ROOT / "data/github-snapshot.jsonl")
    by_id = {item["catalogue_id"]: item for item in snapshots}
    validator.check(
        len(snapshots) == len(records), "GitHub snapshot count does not match canonical records"
    )
    validator.check(len(by_id) == len(snapshots), "duplicate catalogue_id in GitHub snapshot")
    validator.check(
        set(by_id) == {item["catalogue_id"] for item in records},
        "GitHub snapshot IDs do not match canonical IDs",
    )
    repository_ids: set[int] = set()
    capture_times = {item["captured_at"] for item in snapshots}
    validator.check(len(capture_times) == 1, "GitHub metadata snapshot has multiple capture times")
    for item in snapshots:
        prefix = f"data/github-snapshot.jsonl:{item.get('catalogue_id')}"
        validator.check(
            item.get("status") in {"available", "unavailable", "merged", "error"},
            f"{prefix}: invalid status",
        )
        try:
            datetime.fromisoformat(item["captured_at"])
        except (KeyError, ValueError):
            validator.errors.append(f"{prefix}: invalid captured_at")
        if item.get("status") == "available":
            repository_id = item.get("repository_id")
            validator.check(
                isinstance(repository_id, int), f"{prefix}: available record lacks repository_id"
            )
            if isinstance(repository_id, int):
                validator.check(
                    repository_id not in repository_ids, f"{prefix}: duplicate repository_id"
                )
                repository_ids.add(repository_id)
            validator.check(
                bool(item.get("name_with_owner")), f"{prefix}: available record lacks name"
            )
            validator.check(bool(item.get("url")), f"{prefix}: available record lacks URL")
        canonical = next(
            record for record in records if record["catalogue_id"] == item["catalogue_id"]
        )
        validator.check(
            (item.get("status") == "merged") == (canonical.get("record_status") == "merged"),
            f"{prefix}: snapshot and canonical lifecycle disagree",
        )
        validator.check(
            item.get("topics") == sorted(set(item.get("topics", [])), key=str.casefold),
            f"{prefix}: topics are not unique and sorted",
        )
    validator.check(
        not any(item.get("status") == "error" for item in snapshots),
        "GitHub snapshot contains fetch errors",
    )
    return snapshots


def validate_aliases(validator: Validator, records: list[dict[str, Any]]) -> None:
    aliases = load_jsonl(ROOT / "data/repository-aliases.jsonl")
    by_id = {item["catalogue_id"]: item for item in records}
    seen: set[str] = set()
    for item in aliases:
        prefix = f"data/repository-aliases.jsonl:{item.get('catalogue_id')}"
        validator.check(item.get("catalogue_id") in by_id, f"{prefix}: unknown catalogue_id")
        if item.get("catalogue_id") in by_id:
            validator.check(
                item.get("current_full_name") == by_id[item["catalogue_id"]]["full_name"],
                f"{prefix}: current_full_name does not match canonical record",
            )
        alias = item.get("alias_full_name", "").casefold()
        validator.check(alias not in seen, f"{prefix}: duplicate alias")
        seen.add(alias)
        validator.check(
            item.get("alias_url") == f"https://github.com/{item.get('alias_full_name')}",
            f"{prefix}: alias URL mismatch",
        )


def validate_exports(validator: Validator, records: list[dict[str, Any]]) -> None:
    exported_json = load_json(ROOT / "exports/repositories.json")
    validator.check(len(exported_json) == len(records), "JSON export count mismatch")
    with (ROOT / "exports/repositories.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    validator.check(len(rows) == len(records), "CSV export count mismatch")
    validator.check(
        [row["catalogue_id"] for row in rows] == [item["catalogue_id"] for item in records],
        "CSV order or IDs mismatch",
    )
    for row in rows:
        try:
            topics = json.loads(row["topics"])
            validator.check(
                isinstance(topics, list), f"CSV {row['catalogue_id']}: topics is not a JSON array"
            )
        except json.JSONDecodeError:
            validator.errors.append(f"CSV {row['catalogue_id']}: invalid topics JSON")

    database = sqlite3.connect(ROOT / "exports/catalogue.sqlite")
    try:
        validator.check(
            database.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "SQLite integrity_check failed",
        )
        validator.check(
            not database.execute("PRAGMA foreign_key_check").fetchall(),
            "SQLite foreign_key_check failed",
        )
        validator.check(
            database.execute("SELECT count(*) FROM repositories").fetchone()[0] == len(records),
            "SQLite record count mismatch",
        )
        validator.check(
            database.execute("SELECT count(*) FROM repository_search").fetchone()[0]
            == len(records),
            "SQLite FTS count mismatch",
        )
        validator.check(
            database.execute("SELECT count(*) FROM repository_aliases").fetchone()[0]
            == len(load_jsonl(ROOT / "data/repository-aliases.jsonl")),
            "SQLite alias count mismatch",
        )
        validator.check(
            database.execute("PRAGMA user_version").fetchone()[0] == 10000,
            "SQLite user_version mismatch",
        )
    finally:
        database.close()


def validate_datapackage(validator: Validator) -> None:
    package = load_json(ROOT / "datapackage.json")
    validator.check(package.get("profile") == "data-package", "invalid Data Package profile")
    for resource in package.get("resources", []):
        path = ROOT / resource["path"]
        validator.check(path.is_file(), f"Data Package resource missing: {resource['path']}")
        validator.check(
            resource.get("bytes") == path.stat().st_size,
            f"Data Package byte count mismatch: {resource['path']}",
        )
        validator.check(
            resource.get("hash") == f"sha256:{sha256(path)}",
            f"Data Package hash mismatch: {resource['path']}",
        )


def validate_ro_crate(validator: Validator) -> None:
    crate = load_json(ROOT / "ro-crate-metadata.json")
    validator.check(
        crate.get("@context") == "https://w3id.org/ro/crate/1.3/context",
        "RO-Crate context is not 1.3",
    )
    graph = crate.get("@graph", [])
    by_id = {item.get("@id"): item for item in graph}
    descriptor = by_id.get("ro-crate-metadata.json", {})
    root = by_id.get("./", {})
    validator.check(
        descriptor.get("about") == {"@id": "./"}, "RO-Crate descriptor does not reference root"
    )
    validator.check(
        descriptor.get("conformsTo") == {"@id": "https://w3id.org/ro/crate/1.3"},
        "RO-Crate conformance mismatch",
    )
    validator.check(root.get("@type") == "Dataset", "RO-Crate root is not a Dataset")
    project = load_json(ROOT / "metadata/project.json")
    expected_published_date = project.get("release_date") or project["prepared_date"]
    validator.check(
        root.get("datePublished") == expected_published_date,
        "RO-Crate datePublished does not match the release or candidate preparation date",
    )
    expected_status = "Published" if project.get("release_date") else "Release candidate"
    validator.check(
        root.get("creativeWorkStatus") == expected_status,
        "RO-Crate creativeWorkStatus disagrees with project release status",
    )
    validator.check(
        root.get("identifier") == (project.get("doi") or project["repository_url"]),
        "RO-Crate identifier disagrees with project metadata",
    )
    try:
        date.fromisoformat(root.get("datePublished", ""))
    except ValueError:
        validator.errors.append("RO-Crate root has no valid datePublished")
    for reference in root.get("hasPart", []):
        entity_id = reference.get("@id")
        validator.check(entity_id in by_id, f"RO-Crate hasPart entity missing: {entity_id}")
        validator.check((ROOT / entity_id).is_file(), f"RO-Crate payload missing: {entity_id}")


def validate_preview(validator: Validator, records: list[dict[str, Any]]) -> None:
    path = ROOT / "ro-crate-preview.html"
    text = path.read_text(encoding="utf-8")
    project = load_json(ROOT / "metadata/project.json")
    expected_status = (
        f"Version {project['version']}" if project.get("release_date") else "Release candidate"
    )
    validator.check(text.startswith("<!doctype html>"), "HTML preview lacks a doctype")
    validator.check(
        str(len(records)) in text and expected_status in text,
        "HTML preview lacks catalogue statistics or release status",
    )
    pages_url = project.get("pages_url", "").rstrip("/")
    validator.check(
        pages_url.startswith("https://"),
        "project metadata lacks an HTTPS GitHub Pages URL",
    )
    for target in (
        f'{pages_url}/',
        f'{pages_url}/knowledge/',
        f'{pages_url}/docs/querying.html',
    ):
        validator.check(f'href="{target}"' in text, f"HTML preview lacks Pages link: {target}")
    validator.check(
        not any(target.endswith(".md") for target in re.findall(r'href="([^"]+)"', text)),
        "HTML preview contains a Markdown source link instead of a rendered Pages route",
    )
    for target in re.findall(r'href="([^"]+)"', text):
        if target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target.split("#", 1)[0]).resolve()
        validator.check(
            resolved.exists() and resolved.is_relative_to(ROOT),
            f"broken or out-of-tree HTML preview link: {target}",
        )


def validate_okf(validator: Validator, records: list[dict[str, Any]]) -> None:
    knowledge = ROOT / "knowledge"
    repository_docs = list((knowledge / "repositories").glob("*/*.md"))
    repository_docs = [path for path in repository_docs if path.name != "index.md"]
    validator.check(len(repository_docs) == len(records), "OKF repository document count mismatch")
    for path in knowledge.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if path.name in {"index.md", "log.md"}:
            if path == knowledge / "index.md":
                validator.check(
                    text.startswith('---\nokf_version: "0.2"\n---\n'),
                    "OKF root does not declare version 0.2",
                )
            continue
        validator.check(text.startswith("---\n"), f"OKF concept lacks frontmatter: {path}")
        closing = text.find("\n---\n", 4)
        validator.check(closing > 0, f"OKF concept has unterminated frontmatter: {path}")
        frontmatter = text[4:closing] if closing > 0 else ""
        validator.check(
            bool(re.search(r"(?m)^type:\s*\S", frontmatter)), f"OKF concept lacks type: {path}"
        )


def validate_markdown_links(validator: Validator) -> None:
    """Check repository-relative Markdown links without dereferencing web URLs."""
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    excluded_parts = {".git", ".venv", "release", "build", "__pycache__"}
    for path in ROOT.rglob("*.md"):
        if any(part in excluded_parts for part in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            resolved = (path.parent / target_path).resolve()
            validator.check(
                resolved.exists() and resolved.is_relative_to(ROOT),
                f"broken or out-of-tree Markdown link in {path.relative_to(ROOT)}: {target}",
            )


def validate_manifest(validator: Validator) -> None:
    manifest = load_json(ROOT / "release-manifest.json")
    project = load_json(ROOT / "metadata/project.json")
    validator.check(manifest.get("doi") == project.get("doi"), "manifest DOI mismatch")
    validator.check(
        manifest.get("release_date") == project.get("release_date"),
        "manifest release date mismatch",
    )
    for item in manifest.get("files", []):
        path = ROOT / item["path"]
        validator.check(path.is_file(), f"manifest file missing: {item['path']}")
        validator.check(
            item["bytes"] == path.stat().st_size, f"manifest byte count mismatch: {item['path']}"
        )
        validator.check(item["sha256"] == sha256(path), f"manifest hash mismatch: {item['path']}")


def validate_public_tree(validator: Validator) -> None:
    excluded = {".git", ".venv", "release", "__pycache__"}
    forbidden_top_level = {"handoff", "imports", "provenance", "sources"}
    validator.check(
        not any((ROOT / name).exists() for name in forbidden_top_level),
        "public tree contains a handoff-only top-level directory",
    )
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in {".sqlite", ".zip", ".png", ".pdf"}:
            continue
        try:
            text = path.read_text(encoding="utf-8").casefold()
        except UnicodeDecodeError:
            continue
        local_home_marker = "/" + "users/"
        validator.check(local_home_marker not in text, f"local absolute path in public file {path}")


def validate_citation(validator: Validator) -> None:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    project = load_json(ROOT / "metadata/project.json")
    required_snippets = [
        "cff-version: 1.2.0",
        "type: dataset",
        "given-names: Dominik",
        "family-names: Ukolov",
        "Digital Humanities (Image/Object), Friedrich-Schiller-University Jena",
        "version: 1.0.0",
    ]
    for snippet in required_snippets:
        validator.check(snippet in text, f"CITATION.cff missing: {snippet}")
    if project.get("doi"):
        validator.check(f"doi: {project['doi']}" in text, "CITATION.cff DOI mismatch")
    else:
        validator.check("doi:" not in text, "CITATION.cff has a DOI before project metadata")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        validator.warnings.append(
            "PyYAML is not installed; CITATION.cff received textual checks only"
        )
    else:
        citation = yaml.safe_load(text)
        validator.check(isinstance(citation, dict), "CITATION.cff is not a YAML mapping")


def main() -> int:
    validator = Validator()
    required_files = [
        "README.md",
        "assets/category-overview.svg",
        "CITATION.cff",
        "LICENSE",
        "data/repositories.jsonl",
        "data/github-snapshot.jsonl",
        "data/repository-aliases.jsonl",
        "exports/repositories.csv",
        "exports/repositories.json",
        "exports/catalogue.sqlite",
        "datapackage.json",
        "ro-crate-metadata.json",
        "ro-crate-preview.html",
        "release-manifest.json",
        "knowledge/index.md",
        "llms.txt",
        "docs/reuse.md",
        "examples/query.sql",
        "examples/query.py",
        "examples/query.jq",
    ]
    for item in required_files:
        validator.check((ROOT / item).is_file(), f"required file missing: {item}")
    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    records, _, _ = validate_canonical(validator)
    snapshots = validate_snapshots(validator, records)
    validate_aliases(validator, records)
    validate_with_jsonschema(
        validator, ROOT / "data/repositories.jsonl", ROOT / "schema/repository.schema.json"
    )
    validate_with_jsonschema(
        validator, ROOT / "data/github-snapshot.jsonl", ROOT / "schema/github-snapshot.schema.json"
    )
    validate_with_jsonschema(
        validator,
        ROOT / "data/repository-aliases.jsonl",
        ROOT / "schema/repository-alias.schema.json",
    )
    validate_exports(validator, records)
    validate_datapackage(validator)
    validate_ro_crate(validator)
    validate_preview(validator, records)
    validate_okf(validator, records)
    validate_markdown_links(validator)
    validate_manifest(validator)
    validate_public_tree(validator)
    validate_citation(validator)

    for warning in dict.fromkeys(validator.warnings):
        print(f"WARNING: {warning}")
    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    status_counts = Counter(item["status"] for item in snapshots)
    print(
        f"Validated {len(records)} records, {len(load_json(ROOT / 'data/vocabularies/categories.json')['concepts'])} categories, "
        f"and all generated formats. GitHub status: {dict(status_counts)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
