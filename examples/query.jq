# Run with: jq -r -f examples/query.jq data/repositories.jsonl
select(
  .scope_status == "core"
  and .primary_category == "musical_instrument_acoustics"
)
| [.catalogue_id, .full_name]
| @tsv
