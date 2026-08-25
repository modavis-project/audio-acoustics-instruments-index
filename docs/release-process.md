# Release process

## Version policy

- Major: incompatible schema or identifier-policy change.
- Minor: new records, categories, or backward-compatible fields.
- Patch: corrected metadata or documentation with no incompatible schema change.

Every release also carries a catalogue `snapshot_date`. Version and snapshot are
distinct: the version identifies the published dataset; the date identifies the
curated observation represented by its records.

## Pre-release

1. Refresh public GitHub metadata and review redirects or unavailable records.
2. Run `uv sync --frozen --extra validation`, followed by `make build`, `make validate`,
   and `make release-check` with the checked-in Python version.
3. Review `CHANGELOG.md`, `CITATION.cff`, category counts, and generated indexes.
4. Create a Zenodo Dataset draft and reserve its DOI.
5. Set `doi` and `release_date` in `metadata/project.json`; add the DOI and release date to
   `CITATION.cff` and the README. Rebuilding updates RO-Crate automatically.
6. Repeat the release check from a clean worktree.

The manual Zenodo deposit is intentional: it permits a version DOI to be
reserved and embedded before the Git tag is created. Do not also enable Zenodo's
automatic GitHub-release archive for the same version, because that would create
a second deposit rather than a mirror of the reviewed dataset release.

## Publication

1. Create an annotated `vX.Y.Z` Git tag at the checked commit.
2. Build the release archive from that tag.
3. Upload the archive and convenient individual exports to the Zenodo draft.
4. Publish Zenodo and the matching GitHub release.
5. Verify hashes and links on both services.

Never reuse a tag or alter published files. Corrections become a new version.
