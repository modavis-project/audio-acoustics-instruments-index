# Reusing the catalogue

This release is designed for browsing, analysis, teaching, agent workflows, and reproducible research. The following practices preserve its meaning and make derived work easier to verify.

## Reuse checklist

1. Cite the version-specific DOI, `https://doi.org/10.5281/zenodo.22099291`, rather than only the moving GitHub branch.
2. Retain `catalogue_id` in derived tables. It is the stable identity for a record even when a GitHub repository is renamed or merged.
3. Record any filters, exclusions, recategorisation, or enrichment applied to the dataset.
4. Treat `scope_status` as a thematic boundary, not a quality score. Inclusion is not an endorsement.
5. Distinguish curated fields from time-dependent GitHub metadata. Use `snapshot_date` and `github_metadata_captured_at` when reporting currentness.
6. Attribute the catalogue under CC BY 4.0. The listed repositories and their contents retain their own licences.

## Choosing a representation

- Use `data/repositories.jsonl` as the authoritative curated source.
- Use `exports/catalogue.sqlite` for filtering, joins, counts, and full-text search.
- Use `exports/repositories.csv` for spreadsheets and `exports/repositories.json` for JSON-array workflows.
- Use `knowledge/index.md` for progressive human or LLM browsing. It applies Open Knowledge Format (OKF) 0.2.
- Use `llms.txt` as the compact entry point for an agent, then follow only the links needed for the task.
- Use `ro-crate-metadata.json` and `datapackage.json` for research-object and data-package metadata.

## LLM and agent use

Provide `llms.txt` first and let the agent traverse the OKF 0.2 hierarchy by subject. Ask it to preserve `catalogue_id` in outputs, identify the dataset version, and separate catalogue assertions from dated GitHub facts. Do not treat missing or old forge metadata as evidence that a project is inactive without checking the repository directly.

## Derived datasets

A useful derived dataset should document its source release, selection rule, transformation code, row count, and licence. If classifications are changed, use a new field or clearly record the transformation instead of silently replacing the original category. The release manifest and checksums can be used to verify unchanged source files.
