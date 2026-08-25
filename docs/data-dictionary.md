# Data dictionary

## Canonical repository records

`data/repositories.jsonl` contains one UTF-8 JSON object per line, ordered by
`catalogue_id`.

| Field | Type | Meaning |
|---|---|---|
| `catalogue_id` | string | Permanent catalogue identifier (`GHIAO-NNNN`) |
| `full_name` | string | Owner and repository name at the catalogue snapshot |
| `owner` | string | Repository owner at the catalogue snapshot |
| `name` | string | Repository name at the catalogue snapshot |
| `html_url` | URI | Public repository URL |
| `description_de` | string | Curator-authored German summary |
| `primary_category` | vocabulary ID | Principal subject category |
| `scope_status` | `core` or `adjacent` | Relationship to catalogue scope |
| `snapshot_date` | ISO date | Date of the curated catalogue snapshot |
| `record_status` | `active` or `merged` | Lifecycle state of the stable catalogue record |
| `redirects_to` | catalogue ID or null | Surviving catalogue record when a record has merged |

## GitHub metadata snapshot

`data/github-snapshot.jsonl` contains public, time-dependent facts obtained from
GitHub. It is joined to curated records by `catalogue_id`. `repository_id` is the
immutable GitHub database identifier; `name_with_owner` and `url` represent the
name and canonical URL resolved during the metadata capture.

Descriptions in this snapshot are repository-authored GitHub descriptions, not
curator-authored summaries. Licence identifiers are GitHub's detected SPDX
classification and are not independent legal verification. Counts and timestamps
must always be interpreted with `captured_at`.

## Repository aliases

`data/repository-aliases.jsonl` preserves former public GitHub owner/name pairs
when GitHub resolves them to a different current repository identity. Aliases
maintain stable discovery and explain why older links or citations may differ from
the current canonical name. They are not alternate catalogue records.

## Generated exports

Generated exports join stable curated fields with the latest public GitHub
snapshot. Empty values remain empty rather than being inferred. Array-valued CSV
fields are encoded as JSON arrays, not with an undocumented separator.
