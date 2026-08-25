# Repository architecture

## Name

The formal dataset title is **Audio, Acoustics, and Musical Instruments
Repository Index**. It is descriptive enough for scholarly citation while
remaining independent of any particular hosting service. The repository slug is
`audio-acoustics-instruments-index`: short, lowercase, stable, and aligned with
the principal discovery terms.

`MODAVIS` appears in project and creator context rather than in the title. This
keeps the dataset discoverable on its own while preserving its relationship to
the PhD thesis project.

## Representation layers

The repository uses one curated source of truth and several deterministic views:

```text
data/repositories.jsonl + controlled vocabularies + public GitHub snapshot
                              |
                              v
        CSV / JSON / SQLite / Data Package / RO-Crate / OKF bundle
```

- Canonical JSONL keeps reviewable records small and line-oriented.
- The public GitHub snapshot isolates volatile forge facts from curator decisions.
- SQLite supports relational joins and FTS5 search without a server.
- CSV and JSON support common analysis environments.
- Frictionless metadata describes the tabular exchange representation.
- RO-Crate describes the release as a research object.
- OKF Markdown and `llms.txt` provide progressive disclosure for people and agents.

Generated files are committed so that a reader, archival service, or language
model does not need to run code before browsing the release. The build remains
deterministic so every generated view can be checked against the canonical data.
The lock file and `.python-version` also pin the SQLite library used by the
release build; other SQLite releases can encode the same logical database into
different bytes.
Before publication, RO-Crate identifies the local preparation as a release
candidate and uses its preparation date to meet the RO-Crate 1.3 date
requirement. The reserved DOI and actual release date replace candidate metadata
during the final publication step.

## Public-data boundary

The release contains the curated catalogue and public, dated repository facts.
Temporary compilation inputs, review worksheets, acquisition notes, and local
handoff artifacts are deliberately outside the public repository. They are not
required to interpret or reproduce the published representations from the
canonical release data.

## Identifier and lifecycle policy

`GHIAO-NNNN` identifiers are permanent. A repository rename is represented by a
public alias. If two catalogue records resolve to the same surviving repository,
one identifier is retained as a merged record with an explicit redirect rather
than silently removed. This protects citations and downstream joins.

## Preservation model

GitHub is the collaborative source repository. Each approved version is also
deposited manually as a Zenodo Dataset so a version DOI can be reserved and
embedded in the release metadata before publication. The exact tagged commit,
release archive, checksums, and Zenodo files must agree.
