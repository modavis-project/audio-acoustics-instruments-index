#!/usr/bin/env python3
"""Refresh public GitHub facts without modifying curated catalogue fields."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from common import ROOT, load_jsonl, write_jsonl

API_VERSION = "2022-11-28"


def github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    result = subprocess.run(
        ["gh", "auth", "token"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def empty_snapshot(record: dict[str, Any], status: str, captured_at: str) -> dict[str, Any]:
    return {
        "catalogue_id": record["catalogue_id"],
        "queried_full_name": record["full_name"],
        "status": status,
        "repository_id": None,
        "node_id": None,
        "name_with_owner": None,
        "url": None,
        "homepage_url": None,
        "description": None,
        "is_archived": None,
        "is_disabled": None,
        "is_fork": None,
        "default_branch": None,
        "primary_language": None,
        "license_spdx": None,
        "topics": [],
        "stargazers_count": None,
        "forks_count": None,
        "open_issues_count": None,
        "created_at": None,
        "pushed_at": None,
        "updated_at": None,
        "captured_at": captured_at,
    }


def fetch(record: dict[str, Any], token: str, captured_at: str) -> dict[str, Any]:
    owner, name = record["full_name"].split("/", 1)
    encoded_path = f"{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(name, safe='')}"
    url = f"https://api.github.com/repos/{encoded_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "audio-acoustics-instruments-index",
        "X-GitHub-Api-Version": API_VERSION,
    }
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            snapshot = empty_snapshot(record, "available", captured_at)
            snapshot.update(
                {
                    "repository_id": data.get("id"),
                    "node_id": data.get("node_id"),
                    "name_with_owner": data.get("full_name"),
                    "url": data.get("html_url"),
                    "homepage_url": data.get("homepage") or None,
                    "description": data.get("description") or None,
                    "is_archived": data.get("archived"),
                    "is_disabled": data.get("disabled"),
                    "is_fork": data.get("fork"),
                    "default_branch": data.get("default_branch"),
                    "primary_language": data.get("language"),
                    "license_spdx": (data.get("license") or {}).get("spdx_id"),
                    "topics": sorted(set(data.get("topics") or []), key=str.casefold),
                    "stargazers_count": data.get("stargazers_count"),
                    "forks_count": data.get("forks_count"),
                    "open_issues_count": data.get("open_issues_count"),
                    "created_at": data.get("created_at"),
                    "pushed_at": data.get("pushed_at"),
                    "updated_at": data.get("updated_at"),
                }
            )
            return snapshot
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return empty_snapshot(record, "unavailable", captured_at)
            if exc.code in {403, 429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            return empty_snapshot(record, "error", captured_at)
        except (TimeoutError, urllib.error.URLError):
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            return empty_snapshot(record, "error", captured_at)
    return empty_snapshot(record, "error", captured_at)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    records = load_jsonl(ROOT / "data/repositories.jsonl")
    token = github_token()
    captured_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshots: list[dict[str, Any]] = []

    snapshots.extend(
        empty_snapshot(record, "merged", captured_at)
        for record in records
        if record.get("record_status") == "merged"
    )
    active_records = [record for record in records if record.get("record_status") != "merged"]

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(fetch, record, token, captured_at): record for record in active_records
        }
        for index, future in enumerate(as_completed(futures), 1):
            snapshots.append(future.result())
            if index % 50 == 0 or index == len(active_records):
                print(f"Fetched {index}/{len(active_records)} active repositories", file=sys.stderr)

    snapshots.sort(key=lambda item: item["catalogue_id"])
    write_jsonl(ROOT / "data/github-snapshot.jsonl", snapshots)
    counts = {
        status: sum(item["status"] == status for item in snapshots)
        for status in ("available", "unavailable", "merged", "error")
    }
    print(json.dumps({"captured_at": captured_at, "counts": counts}, indent=2))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
