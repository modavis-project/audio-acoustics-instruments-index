#!/usr/bin/env python3
"""Build all public representations from canonical JSONL records."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any

from common import ROOT, load_json, load_jsonl, sha256, write_json, write_text, yaml_string

GENERATED_FILES = [
    ROOT / "assets/category-overview.svg",
    ROOT / "exports/repositories.csv",
    ROOT / "exports/repositories.json",
    ROOT / "exports/catalogue.sqlite",
    ROOT / "exports/SHA256SUMS",
    ROOT / "datapackage.json",
    ROOT / "ro-crate-metadata.json",
    ROOT / "release-manifest.json",
    ROOT / "llms.txt",
    ROOT / "ro-crate-preview.html",
]


def clean() -> None:
    for path in GENERATED_FILES:
        path.unlink(missing_ok=True)
    for path in (ROOT / "knowledge/repositories", ROOT / "knowledge/taxonomy"):
        if path.exists():
            shutil.rmtree(path)
    for path in (ROOT / "knowledge/index.md", ROOT / "knowledge/methodology.md"):
        path.unlink(missing_ok=True)


def combined_records(
    records: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    categories: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {snapshot["catalogue_id"]: snapshot for snapshot in snapshots}
    output: list[dict[str, Any]] = []
    for record in records:
        snapshot = by_id.get(record["catalogue_id"], {})
        category = categories[record["primary_category"]]
        output.append(
            {
                **record,
                "current_full_name": snapshot.get("name_with_owner"),
                "current_url": snapshot.get("url"),
                "description": snapshot.get("description"),
                "category_label_en": category["label_en"],
                "category_label_de": category["label_de"],
                "github_repository_id": snapshot.get("repository_id"),
                "github_status": snapshot.get("status"),
                "homepage_url": snapshot.get("homepage_url"),
                "is_archived": snapshot.get("is_archived"),
                "is_disabled": snapshot.get("is_disabled"),
                "is_fork": snapshot.get("is_fork"),
                "default_branch": snapshot.get("default_branch"),
                "primary_language": snapshot.get("primary_language"),
                "license_spdx": snapshot.get("license_spdx"),
                "topics": snapshot.get("topics", []),
                "stargazers_count": snapshot.get("stargazers_count"),
                "forks_count": snapshot.get("forks_count"),
                "open_issues_count": snapshot.get("open_issues_count"),
                "created_at": snapshot.get("created_at"),
                "pushed_at": snapshot.get("pushed_at"),
                "updated_at": snapshot.get("updated_at"),
                "github_metadata_captured_at": snapshot.get("captured_at"),
            }
        )
    return output


def build_json_and_csv(records: list[dict[str, Any]]) -> None:
    exports = ROOT / "exports"
    exports.mkdir(exist_ok=True)
    write_json(exports / "repositories.json", records)

    fields = [
        "catalogue_id",
        "full_name",
        "current_full_name",
        "html_url",
        "current_url",
        "description",
        "description_de",
        "primary_category",
        "category_label_en",
        "category_label_de",
        "scope_status",
        "record_status",
        "redirects_to",
        "github_repository_id",
        "github_status",
        "homepage_url",
        "is_archived",
        "is_disabled",
        "is_fork",
        "default_branch",
        "primary_language",
        "license_spdx",
        "topics",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "created_at",
        "pushed_at",
        "updated_at",
        "snapshot_date",
        "github_metadata_captured_at",
    ]
    with (exports / "repositories.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["topics"] = json.dumps(record["topics"], ensure_ascii=False, separators=(",", ":"))
            writer.writerow(row)


def build_sqlite(
    project: dict[str, Any],
    records: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
) -> None:
    path = ROOT / "exports/catalogue.sqlite"
    path.unlink(missing_ok=True)
    database = sqlite3.connect(path)
    try:
        database.executescript((ROOT / "schema/sqlite.sql").read_text(encoding="utf-8"))
        database.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            sorted(
                {
                    "title": project["title"],
                    "version": project["version"],
                    "snapshot_date": project["snapshot_date"],
                    "license": project["license"],
                    "creator": project["creator"]["name"],
                    "project": project["project"],
                }.items()
            ),
        )
        database.executemany(
            "INSERT INTO categories VALUES (?, ?, ?, ?, ?)",
            [
                (
                    item["id"],
                    item["label_en"],
                    item["label_de"],
                    item["broader"],
                    item["definition_en"],
                )
                for item in sorted(categories, key=lambda value: value["id"])
            ],
        )
        database.executemany(
            "INSERT INTO repositories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    item["catalogue_id"],
                    item["full_name"],
                    item["owner"],
                    item["name"],
                    item["html_url"],
                    item["description_de"],
                    item["primary_category"],
                    item["scope_status"],
                    item["snapshot_date"],
                    item["record_status"],
                    item["redirects_to"],
                )
                for item in records
            ],
        )
        database.executemany(
            """
            INSERT INTO github_snapshots VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                (
                    item["catalogue_id"],
                    item["repository_id"],
                    item["node_id"],
                    item["status"],
                    item["queried_full_name"],
                    item["name_with_owner"],
                    item["url"],
                    item["homepage_url"],
                    item["description"],
                    item["is_archived"],
                    item["is_disabled"],
                    item["is_fork"],
                    item["default_branch"],
                    item["primary_language"],
                    item["license_spdx"],
                    item["stargazers_count"],
                    item["forks_count"],
                    item["open_issues_count"],
                    item["created_at"],
                    item["pushed_at"],
                    item["updated_at"],
                    item["captured_at"],
                )
                for item in snapshots
            ],
        )
        topic_rows = sorted(
            (item["catalogue_id"], topic) for item in snapshots for topic in item.get("topics", [])
        )
        database.executemany("INSERT INTO topics VALUES (?, ?)", topic_rows)
        database.executemany(
            "INSERT INTO repository_aliases VALUES (?, ?, ?, ?)",
            [
                (
                    item["catalogue_id"],
                    item["alias_full_name"],
                    item["alias_url"],
                    item["current_full_name"],
                )
                for item in aliases
            ],
        )
        snapshot_by_id = {item["catalogue_id"]: item for item in snapshots}
        category_by_id = {item["id"]: item for item in categories}
        search_rows = []
        for item in records:
            snapshot = snapshot_by_id[item["catalogue_id"]]
            current_name = snapshot.get("name_with_owner") or item["full_name"]
            search_rows.append(
                (
                    item["catalogue_id"],
                    current_name,
                    snapshot.get("description") or "",
                    item["description_de"],
                    category_by_id[item["primary_category"]]["label_en"],
                    " ".join(snapshot.get("topics", [])),
                )
            )
        database.executemany("INSERT INTO repository_search VALUES (?, ?, ?, ?, ?, ?)", search_rows)
        database.commit()
        database.execute("VACUUM")
    finally:
        database.close()


def md_escape(value: Any) -> str:
    if value is None or value == "":
        return "Not reported"
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_knowledge(
    project: dict[str, Any],
    records: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> None:
    knowledge = ROOT / "knowledge"
    for generated in (knowledge / "repositories", knowledge / "taxonomy"):
        if generated.exists():
            shutil.rmtree(generated)
    (knowledge / "repositories").mkdir(parents=True, exist_ok=True)
    (knowledge / "taxonomy").mkdir(parents=True, exist_ok=True)

    snapshot_by_id = {item["catalogue_id"]: item for item in snapshots}
    record_by_id = {item["catalogue_id"]: item for item in records}
    records_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_category[record["primary_category"]].append(record)

    root_lines = [
        "---",
        'okf_version: "0.2"',
        "---",
        f"# {project['title']}",
        "",
        f"Version {project['version']}; curated snapshot {project['snapshot_date']}.",
        "",
        "This progressive knowledge bundle is generated from the canonical catalogue.",
        "",
        "## Start here",
        "",
        "* [Methodology](methodology.md) - purpose, scope, and interpretation.",
        "* [Repository index](repositories/) - browse repositories by subject category.",
        "* [Taxonomy](taxonomy/) - category definitions and classification guidance.",
        "",
        "## Categories",
        "",
    ]
    for category in sorted(categories, key=lambda item: item["label_en"].casefold()):
        count = len(records_by_category[category["id"]])
        root_lines.append(
            f"* [{category['label_en']}](repositories/{category['id']}/) - {count} repositories."
        )
    write_text(knowledge / "index.md", "\n".join(root_lines))

    write_text(
        knowledge / "methodology.md",
        "\n".join(
            [
                "---",
                "type: Methodology",
                'title: "Catalogue methodology"',
                'description: "How repository scope, classification, freshness, and inclusion should be interpreted."',
                f"resource: {yaml_string(project['repository_url'] + '/blob/main/docs/scope.md')}",
                'tags: ["methodology", "scope", "classification"]',
                "status: stable",
                "---",
                "# Purpose",
                "",
                "The catalogue supports discovery across acoustics, audio, musical instruments, organology, and related technical fields.",
                "",
                "# Interpretation",
                "",
                "Each repository has one curator-assigned primary category and a `core` or `adjacent` scope status. These are discovery aids, not quality ratings. Public GitHub facts are captured separately from curated descriptions and may change after the recorded capture time.",
                "",
                "# Detailed policy",
                "",
                "See the repository's [scope policy](../docs/scope.md) and [classification guide](../docs/classification-guide.md).",
            ]
        ),
    )

    taxonomy_index = ["# Subject taxonomy", ""]
    for category in sorted(categories, key=lambda item: item["label_en"].casefold()):
        taxonomy_index.append(
            f"* [{category['label_en']}]({category['id']}.md) - {category['definition_en']}"
        )
        write_text(
            knowledge / "taxonomy" / f"{category['id']}.md",
            "\n".join(
                [
                    "---",
                    "type: Subject Category",
                    f"title: {yaml_string(category['label_en'])}",
                    f"description: {yaml_string(category['definition_en'])}",
                    f'tags: [{yaml_string(category["broader"])}, "taxonomy"]',
                    "status: stable",
                    f"category_id: {yaml_string(category['id'])}",
                    "---",
                    f"# {category['label_en']}",
                    "",
                    category["definition_en"],
                    "",
                    f"**German label:** {category['label_de']}",
                    "",
                    f"Browse the [{len(records_by_category[category['id']])} classified repositories](../repositories/{category['id']}/).",
                ]
            ),
        )
    write_text(knowledge / "taxonomy/index.md", "\n".join(taxonomy_index))

    repository_index = ["# Repositories by subject", ""]
    for category in sorted(categories, key=lambda item: item["label_en"].casefold()):
        repository_index.append(
            f"* [{category['label_en']}]({category['id']}/) - {len(records_by_category[category['id']])} repositories."
        )
        category_dir = knowledge / "repositories" / category["id"]
        category_dir.mkdir(parents=True, exist_ok=True)
        category_lines = [f"# {category['label_en']}", "", category["definition_en"], ""]
        for record in sorted(
            records_by_category[category["id"]], key=lambda item: item["full_name"].casefold()
        ):
            snapshot = snapshot_by_id[record["catalogue_id"]]
            current_name = snapshot.get("name_with_owner") or record["full_name"]
            description = (snapshot.get("description") or record["description_de"]).strip()
            category_lines.append(
                f"* [{current_name}]({record['catalogue_id']}.md) - {description}"
            )
            tags = [record["primary_category"], record["scope_status"], *snapshot.get("topics", [])]
            tags = list(dict.fromkeys(tags))[:20]
            repository_url = snapshot.get("url") or record["html_url"]
            generated_at = f"{record['snapshot_date']}T00:00:00Z"
            lifecycle_status = "deprecated" if record["record_status"] == "merged" else "stable"
            frontmatter = [
                "---",
                "type: Source Code Repository",
                f"title: {yaml_string(current_name)}",
                f"description: {yaml_string(description)}",
                f"resource: {yaml_string(repository_url)}",
                f"tags: {json.dumps(tags, ensure_ascii=False)}",
                f"status: {lifecycle_status}",
                f"generated: {{ by: process:catalogue-build, at: {generated_at} }}",
            ]
            if snapshot.get("status") == "available":
                frontmatter.append(
                    f"verified: {{ by: process:github-metadata-refresh, at: {snapshot['captured_at']} }}"
                )
            frontmatter.extend(
                [
                    f"catalogue_id: {record['catalogue_id']}",
                    f"primary_category: {record['primary_category']}",
                    f"scope_status: {record['scope_status']}",
                    f"record_status: {record['record_status']}",
                    "---",
                ]
            )
            body = [
                *frontmatter,
                f"# {current_name}",
                "",
                "## Summary",
                "",
                description,
                "",
                "## Kuratierte Zusammenfassung (Deutsch)",
                "",
                record["description_de"],
                "",
                "## Classification",
                "",
                f"- Subject: [{category['label_en']}](../../taxonomy/{category['id']}.md)",
                f"- Scope: `{record['scope_status']}`",
                f"- Catalogue ID: `{record['catalogue_id']}`",
                f"- Record status: `{record['record_status']}`",
                "",
                "## Repository metadata",
                "",
                "| Field | Value |",
                "|---|---|",
                f"| Repository | [{md_escape(current_name)}]({repository_url}) |",
                f"| GitHub repository ID | {md_escape(snapshot.get('repository_id'))} |",
                f"| Status | {md_escape(snapshot.get('status'))} |",
                f"| Archived | {md_escape(snapshot.get('is_archived'))} |",
                f"| Fork | {md_escape(snapshot.get('is_fork'))} |",
                f"| Primary language | {md_escape(snapshot.get('primary_language'))} |",
                f"| Detected licence | {md_escape(snapshot.get('license_spdx'))} |",
                f"| Metadata captured | {md_escape(snapshot.get('captured_at'))} |",
                "",
                "Repository metadata is a dated public snapshot and may differ from the current GitHub page.",
            ]
            if record["redirects_to"]:
                successor = record_by_id[record["redirects_to"]]
                body.extend(
                    [
                        "",
                        "## Successor record",
                        "",
                        f"This stable identifier has merged into [{record['redirects_to']}](../{successor['primary_category']}/{record['redirects_to']}.md).",
                    ]
                )
            write_text(category_dir / f"{record['catalogue_id']}.md", "\n".join(body))
        write_text(category_dir / "index.md", "\n".join(category_lines))
    write_text(knowledge / "repositories/index.md", "\n".join(repository_index))


def file_resource(path: Path, root: Path = ROOT) -> dict[str, Any]:
    media_types = {
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".csv": "text/csv",
        ".sqlite": "application/vnd.sqlite3",
        ".md": "text/markdown",
        ".cff": "text/yaml",
    }
    relative = path.relative_to(root).as_posix()
    return {
        "@id": relative,
        "@type": "File",
        "name": path.name,
        "encodingFormat": media_types.get(path.suffix, "application/octet-stream"),
        "contentSize": str(path.stat().st_size),
    }


def build_datapackage(project: dict[str, Any]) -> None:
    csv_path = ROOT / "exports/repositories.csv"
    package = {
        "profile": "data-package",
        "name": "audio-acoustics-instruments-index",
        "title": project["title"],
        "description": "A curated index of repositories related to acoustics, audio, and musical instruments.",
        "version": project["version"],
        "id": f"https://doi.org/{project['doi']}"
        if project.get("doi")
        else project["repository_url"],
        "homepage": project["repository_url"],
        "licenses": [
            {
                "name": "CC-BY-4.0",
                "path": "https://creativecommons.org/licenses/by/4.0/",
                "title": "Creative Commons Attribution 4.0 International",
            }
        ],
        "contributors": [
            {
                "title": project["creator"]["name"],
                "role": "author",
                "organization": project["creator"]["affiliation"],
            }
        ],
        "resources": [
            {
                "profile": "tabular-data-resource",
                "name": "repositories",
                "path": "exports/repositories.csv",
                "format": "csv",
                "mediatype": "text/csv",
                "encoding": "utf-8",
                "bytes": csv_path.stat().st_size,
                "hash": f"sha256:{sha256(csv_path)}",
                "schema": {
                    "primaryKey": "catalogue_id",
                    "fields": [
                        {
                            "name": "catalogue_id",
                            "type": "string",
                            "constraints": {"required": True, "unique": True},
                        },
                        {
                            "name": "full_name",
                            "type": "string",
                            "constraints": {"required": True, "unique": True},
                        },
                        {"name": "current_full_name", "type": "string"},
                        {"name": "html_url", "type": "string", "format": "uri"},
                        {"name": "current_url", "type": "string", "format": "uri"},
                        {"name": "description", "type": "string"},
                        {"name": "description_de", "type": "string"},
                        {"name": "primary_category", "type": "string"},
                        {"name": "category_label_en", "type": "string"},
                        {"name": "category_label_de", "type": "string"},
                        {
                            "name": "scope_status",
                            "type": "string",
                            "constraints": {"enum": ["core", "adjacent"]},
                        },
                        {
                            "name": "record_status",
                            "type": "string",
                            "constraints": {"enum": ["active", "merged"]},
                        },
                        {"name": "redirects_to", "type": "string"},
                        {"name": "github_repository_id", "type": "integer"},
                        {"name": "github_status", "type": "string"},
                        {"name": "homepage_url", "type": "string", "format": "uri"},
                        {"name": "is_archived", "type": "boolean"},
                        {"name": "is_disabled", "type": "boolean"},
                        {"name": "is_fork", "type": "boolean"},
                        {"name": "default_branch", "type": "string"},
                        {"name": "primary_language", "type": "string"},
                        {"name": "license_spdx", "type": "string"},
                        {"name": "topics", "type": "string"},
                        {"name": "stargazers_count", "type": "integer"},
                        {"name": "forks_count", "type": "integer"},
                        {"name": "open_issues_count", "type": "integer"},
                        {"name": "created_at", "type": "datetime"},
                        {"name": "pushed_at", "type": "datetime"},
                        {"name": "updated_at", "type": "datetime"},
                        {"name": "snapshot_date", "type": "date"},
                        {"name": "github_metadata_captured_at", "type": "datetime"},
                    ],
                },
            },
        ],
    }
    write_json(ROOT / "datapackage.json", package)


def build_ro_crate(project: dict[str, Any], payload_files: list[Path]) -> None:
    person_id = "#dominik-ukolov"
    organisation_id = "#fsu-jena-dh-image-object"
    project_id = "#modavis"
    parts = [{"@id": path.relative_to(ROOT).as_posix()} for path in payload_files]
    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.3"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": project["title"],
            "description": "A curated, versioned index of source-code repositories related to acoustics, audio, musical instruments, organology, virtual instruments, and adjacent fields.",
            "version": project["version"],
            "dateCreated": project["snapshot_date"],
            "datePublished": project.get("release_date") or project["prepared_date"],
            "creativeWorkStatus": "Published"
            if project.get("release_date")
            else "Release candidate",
            "identifier": project.get("doi") or project["repository_url"],
            "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
            "author": {"@id": person_id},
            "creator": {"@id": person_id},
            "publisher": {"@id": organisation_id},
            "isPartOf": {"@id": project_id},
            "mainEntity": {"@id": "data/repositories.jsonl"},
            "keywords": project["keywords"],
            "url": project["repository_url"],
            "hasPart": parts,
        },
        {
            "@id": person_id,
            "@type": "Person",
            "name": project["creator"]["name"],
            "givenName": project["creator"]["given_names"],
            "familyName": project["creator"]["family_names"],
            "affiliation": {"@id": organisation_id},
        },
        {
            "@id": organisation_id,
            "@type": "Organization",
            "name": project["creator"]["affiliation"],
        },
        {
            "@id": project_id,
            "@type": "ResearchProject",
            "name": "MODAVIS",
            "description": "PhD thesis project of which this repository index forms a part.",
        },
        {
            "@id": "https://creativecommons.org/licenses/by/4.0/",
            "@type": "CreativeWork",
            "name": "Creative Commons Attribution 4.0 International",
        },
    ]
    graph.extend(file_resource(path) for path in payload_files)
    write_json(
        ROOT / "ro-crate-metadata.json",
        {"@context": "https://w3id.org/ro/crate/1.3/context", "@graph": graph},
    )


def build_llms(project: dict[str, Any], count: int) -> None:
    base = project["repository_url"] + "/blob/main"
    content = f"""# {project["title"]}

> A curated MODAVIS PhD-project dataset of {count} repositories related to acoustics, audio, musical instruments, organology, synthesis, and adjacent fields.

Version: {project["version"]}
Catalogue snapshot: {project["snapshot_date"]}
Version DOI: https://doi.org/{project["doi"]}
Creator: {project["creator"]["name"]} — {project["creator"]["affiliation"]}
Licence: CC BY 4.0 for data and documentation; MIT for build code.

## Start here

- [README]({base}/README.md): Scope, formats, build, citation, and licence.
- [Knowledge bundle]({base}/knowledge/index.md): Progressive OKF 0.2 browser.
- [Canonical JSONL]({base}/data/repositories.jsonl): Authoritative curated records.
- [Data dictionary]({base}/docs/data-dictionary.md): Field semantics.
- [Classification guide]({base}/docs/classification-guide.md): Subject and scope rules.
- [Query guide]({base}/docs/querying.md): SQLite, full-text, jq, and Python examples.
- [Citation metadata]({base}/CITATION.cff): Dataset citation.

## Machine-readable metadata

- [Frictionless Data Package]({base}/datapackage.json)
- [RO-Crate 1.3 metadata]({base}/ro-crate-metadata.json)
- [Repository JSON Schema]({base}/schema/repository.schema.json)
- [GitHub snapshot JSON Schema]({base}/schema/github-snapshot.schema.json)
- [Subject vocabulary]({base}/data/vocabularies/categories.json)

Curated records and dated GitHub metadata are separate. Classification expresses scope, not quality or endorsement. Listed repositories retain their own licences.
"""
    write_text(ROOT / "llms.txt", content)


def build_preview(
    project: dict[str, Any], records: list[dict[str, Any]], categories: list[dict[str, Any]]
) -> None:
    counts = Counter(item["primary_category"] for item in records)
    scope_counts = Counter(item["scope_status"] for item in records)
    pages_url = project["pages_url"].rstrip("/")
    category_cards = "\n".join(
        f"""<li><a href="{escape(pages_url)}/knowledge/repositories/{escape(item["id"])}/"><span>{escape(item["label_en"])}</span><strong>{counts[item["id"]]}</strong></a></li>"""
        for item in sorted(categories, key=lambda value: value["label_en"].casefold())
    )
    release_status = (
        f"Version {project['version']}" if project.get("release_date") else "Release candidate"
    )
    if project.get("doi"):
        release_note = (
            f"<strong>Versioned release.</strong> Cite this exact dataset version using "
            f'<a href="https://doi.org/{escape(project["doi"])}">{escape(project["doi"])}</a>.'
        )
    else:
        release_note = (
            f"<strong>Publication hold.</strong> Version {escape(project['version'])} is a "
            "local release candidate; its version DOI remains unset."
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(project["title"])}</title>
  <style>
    :root {{ color-scheme: light; --ink:#172126; --muted:#5b676d; --paper:#f4f0e8; --panel:#fffdf8; --line:#d8d0c2; --accent:#0f6674; --accent2:#b6542d; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); background:var(--paper); font:16px/1.55 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width:1120px; margin:auto; padding:64px 28px 80px; }} a {{ color:var(--accent); }}
    header {{ padding:44px; border:1px solid var(--line); background:var(--panel); box-shadow:10px 10px 0 #dfd5c4; }}
    .eyebrow {{ margin:0 0 14px; color:var(--accent2); font-weight:750; letter-spacing:.08em; text-transform:uppercase; font-size:.78rem; }}
    h1 {{ max-width:900px; margin:0; font-family:ui-serif,Georgia,serif; font-size:clamp(2.4rem,6vw,5.3rem); line-height:.98; letter-spacing:-.04em; }}
    .lede {{ max-width:760px; margin:28px 0 0; color:var(--muted); font-size:1.15rem; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:28px; }} .button {{ padding:10px 15px; border:1px solid var(--ink); color:var(--ink); text-decoration:none; font-weight:700; background:white; }} .button.primary {{ color:white; background:var(--accent); border-color:var(--accent); }}
    .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1px; margin:54px 0; background:var(--line); border:1px solid var(--line); }} .stat {{ padding:24px; background:var(--panel); }} .stat strong {{ display:block; font-family:ui-serif,Georgia,serif; font-size:2.1rem; }} .stat span {{ color:var(--muted); }}
    h2 {{ margin:56px 0 18px; font:700 2rem/1.1 ui-serif,Georgia,serif; }} .formats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }} .card {{ padding:22px; border:1px solid var(--line); background:var(--panel); }} .card h3 {{ margin:0 0 8px; }} .card p {{ margin:0 0 16px; color:var(--muted); }}
    .categories {{ display:grid; grid-template-columns:repeat(2,1fr); gap:0 24px; padding:0; list-style:none; border-top:1px solid var(--line); }} .categories a {{ display:flex; justify-content:space-between; gap:16px; padding:12px 2px; border-bottom:1px solid var(--line); color:var(--ink); text-decoration:none; }} .categories strong {{ color:var(--accent2); }}
    .note {{ margin-top:48px; padding:20px 24px; border-left:5px solid var(--accent2); background:#fff7e8; }} footer {{ margin-top:60px; color:var(--muted); font-size:.92rem; }} code {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }}
    @media (max-width:760px) {{ main {{ padding:28px 16px 56px; }} header {{ padding:28px 22px; box-shadow:6px 6px 0 #dfd5c4; }} .stats,.formats,.categories {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">MODAVIS PhD thesis project · {escape(release_status)}</p>
    <h1>{escape(project["title"])}</h1>
    <p class="lede">A curated and versioned map of source-code repositories across acoustics, audio, musical instruments, organology, synthesis, spatial sound, and related research fields.</p>
    <nav class="actions" aria-label="Primary resources">
      <a class="button primary" href="{escape(pages_url)}/knowledge/">Browse the knowledge bundle</a>
      <a class="button" href="{escape(pages_url)}/">Read the documentation</a>
      <a class="button" href="exports/catalogue.sqlite">Get SQLite</a>
    </nav>
  </header>

  <section class="stats" aria-label="Catalogue statistics">
    <div class="stat"><strong>{len(records)}</strong><span>stable records</span></div>
    <div class="stat"><strong>{len(categories)}</strong><span>subject classes</span></div>
    <div class="stat"><strong>{scope_counts["core"]}</strong><span>core records</span></div>
    <div class="stat"><strong>{scope_counts["adjacent"]}</strong><span>adjacent records</span></div>
  </section>

  <h2>Choose a representation</h2>
  <section class="formats">
    <article class="card"><h3>For reading</h3><p>Progressive Markdown indexes and one compact, typed page per repository.</p><a href="{escape(pages_url)}/knowledge/">OKF 0.2 bundle →</a></article>
    <article class="card"><h3>For analysis</h3><p>Portable tabular and structured exports for scripts, notebooks, and spreadsheets.</p><a href="exports/repositories.csv">CSV</a> · <a href="exports/repositories.json">JSON</a></article>
    <article class="card"><h3>For querying</h3><p>A normalized SQLite database with an FTS5 full-text search index.</p><a href="{escape(pages_url)}/docs/querying.html">Query examples →</a></article>
    <article class="card"><h3>For agents</h3><p>A compact discovery entry point plus typed and linked knowledge documents.</p><a href="llms.txt">llms.txt →</a></article>
    <article class="card"><h3>For interchange</h3><p>A validated Frictionless table package with explicit field constraints.</p><a href="datapackage.json">Data Package →</a></article>
    <article class="card"><h3>For preservation</h3><p>RO-Crate 1.3 research-object metadata and deterministic release checksums.</p><a href="ro-crate-metadata.json">RO-Crate →</a></article>
  </section>

  <h2>Subject classes</h2>
  <ul class="categories">{category_cards}</ul>

  <aside class="note">{release_note}</aside>
  <footer>Dominik Ukolov · Digital Humanities (Image/Object), Friedrich-Schiller-University Jena · Catalogue snapshot {escape(project["snapshot_date"])} · Data and documentation licensed CC BY 4.0.</footer>
</main>
</body>
</html>"""
    write_text(ROOT / "ro-crate-preview.html", html)


def build_category_overview(
    project: dict[str, Any],
    records: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> None:
    """Build an accessible, GitHub-renderable overview of category sizes."""
    counts = Counter(record["primary_category"] for record in records)
    ordered = sorted(
        categories,
        key=lambda category: (-counts[category["id"]], category["label_en"].casefold()),
    )
    width = 1000
    top = 118
    row_height = 34
    height = top + len(ordered) * row_height + 52
    label_x = 34
    bar_x = 455
    max_bar_width = 430
    maximum = max(counts.values())
    rows = []
    for index, category in enumerate(ordered):
        count = counts[category["id"]]
        y = top + index * row_height
        bar_width = round(max_bar_width * count / maximum)
        rows.append(
            f'  <text class="label" x="{label_x}" y="{y + 20}">'
            f'{escape(category["label_en"])}</text>\n'
            f'  <rect class="bar" x="{bar_x}" y="{y + 4}" width="{bar_width}" '
            f'height="22" rx="4"><title>{escape(category["label_en"])}: '
            f'{count} repositories</title></rect>\n'
            f'  <text class="count" x="{bar_x + bar_width + 12}" y="{y + 20}">'
            f"{count}</text>"
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
  <title id="title">Repositories by subject category</title>
  <desc id="description">Horizontal bar chart showing the distribution of {len(records)} repositories across {len(categories)} subject categories.</desc>
  <style>
    .background {{ fill: #f7f4ed; }}
    .heading {{ fill: #172126; font: 700 25px ui-sans-serif, system-ui, sans-serif; }}
    .subheading {{ fill: #5b676d; font: 15px ui-sans-serif, system-ui, sans-serif; }}
    .label {{ fill: #263238; font: 14px ui-sans-serif, system-ui, sans-serif; }}
    .bar {{ fill: #0f6674; }}
    .count {{ fill: #172126; font: 700 14px ui-monospace, monospace; }}
  </style>
  <rect class="background" width="100%" height="100%" rx="10"/>
  <text class="heading" x="34" y="42">Repositories by subject category</text>
  <text class="subheading" x="34" y="70">{len(records)} records · {len(categories)} documented categories · catalogue snapshot {escape(project["snapshot_date"])}</text>
{chr(10).join(rows)}
</svg>
'''
    path = ROOT / "assets/category-overview.svg"
    path.parent.mkdir(exist_ok=True)
    write_text(path, svg)


def build_manifests(project: dict[str, Any], payload_files: list[Path]) -> None:
    exports = [
        ROOT / "exports/repositories.csv",
        ROOT / "exports/repositories.json",
        ROOT / "exports/catalogue.sqlite",
    ]
    checksum_lines = [f"{sha256(path)}  {path.name}" for path in exports]
    write_text(ROOT / "exports/SHA256SUMS", "\n".join(checksum_lines))

    files = []
    for path in sorted(payload_files, key=lambda item: item.relative_to(ROOT).as_posix()):
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_json(
        ROOT / "release-manifest.json",
        {
            "title": project["title"],
            "version": project["version"],
            "snapshot_date": project["snapshot_date"],
            "prepared_date": project["prepared_date"],
            "release_date": project.get("release_date"),
            "doi": project.get("doi"),
            "manifest_scope": "Core research payload; the release archive has a separate whole-archive checksum.",
            "record_count": len(load_jsonl(ROOT / "data/repositories.jsonl")),
            "files": files,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    if args.clean:
        clean()
        return 0

    project = load_json(ROOT / "metadata/project.json")
    records = load_jsonl(ROOT / "data/repositories.jsonl")
    snapshots = load_jsonl(ROOT / "data/github-snapshot.jsonl")
    aliases = load_jsonl(ROOT / "data/repository-aliases.jsonl")
    vocabulary = load_json(ROOT / "data/vocabularies/categories.json")
    categories_list = vocabulary["concepts"]
    categories = {item["id"]: item for item in categories_list}
    joined = combined_records(records, snapshots, categories)

    build_json_and_csv(joined)
    build_sqlite(project, records, snapshots, categories_list, aliases)
    build_knowledge(project, records, snapshots, categories_list)
    build_datapackage(project)
    build_category_overview(project, records, categories_list)

    crate_payload = [
        ROOT / "README.md",
        ROOT / "docs/reuse.md",
        ROOT / "examples/query.sql",
        ROOT / "examples/query.py",
        ROOT / "examples/query.jq",
        ROOT / "assets/category-overview.svg",
        ROOT / "CITATION.cff",
        ROOT / "LICENSE",
        ROOT / "data/repositories.jsonl",
        ROOT / "data/github-snapshot.jsonl",
        ROOT / "data/repository-aliases.jsonl",
        ROOT / "data/vocabularies/categories.json",
        ROOT / "data/vocabularies/scope-statuses.json",
        ROOT / "schema/repository.schema.json",
        ROOT / "schema/github-snapshot.schema.json",
        ROOT / "schema/repository-alias.schema.json",
        ROOT / "exports/repositories.csv",
        ROOT / "exports/repositories.json",
        ROOT / "exports/catalogue.sqlite",
        ROOT / "knowledge/index.md",
        ROOT / "datapackage.json",
    ]
    build_ro_crate(project, crate_payload)
    build_llms(project, len(records))
    build_preview(project, records, categories_list)
    manifest_payload = [
        *crate_payload,
        ROOT / "ro-crate-metadata.json",
        ROOT / "ro-crate-preview.html",
        ROOT / "llms.txt",
    ]
    build_manifests(project, manifest_payload)

    counts = Counter(record["scope_status"] for record in records)
    print(
        f"Built {len(records)} records ({counts['core']} core, {counts['adjacent']} adjacent), "
        f"{len(categories)} categories, SQLite, OKF, RO-Crate, and Data Package exports."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
