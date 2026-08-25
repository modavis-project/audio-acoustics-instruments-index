# Contributing

Contributions may propose a new repository, correct factual metadata, improve a
description, or challenge a classification. Inclusion is based on documented
scope, not popularity or endorsement.

## Before proposing a record

Read `docs/scope.md` and `docs/classification-guide.md`. A proposal should give:

- the canonical repository URL;
- a concise explanation of its direct acoustics, audio, or musical-instrument relevance;
- a proposed primary category and `core` or `adjacent` scope;
- an English or German summary written independently of promotional language;
- any important relationship to an existing record, such as a fork or successor.

## Editing data

Edit only `data/repositories.jsonl`, the controlled vocabulary, schemas, or
documentation. Do not hand-edit generated files in `exports/` or `knowledge/`.
Run:

```sh
uv sync --frozen --extra validation
make build
make validate
```

Catalogue IDs are permanent. Never reuse or renumber an existing ID. A removed
or unavailable project should be retained as a tombstone in a future schema
rather than silently deleted.

Automated metadata refreshes may update only `data/github-snapshot.jsonl`.
Curated summaries and classifications always require human review.

## Review expectations

Changes must be evidence-based, narrowly scoped, and reproducible. Descriptions
should state what a project provides without making unverifiable quality claims.
Conflicts of interest should be disclosed in the pull request.
