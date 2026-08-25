# Querying the catalogue

## SQLite

List all core virtual-instrument and synthesis records:

```sh
sqlite3 -header -column exports/catalogue.sqlite '
  SELECT catalogue_id, full_name, description
  FROM repository_current
  WHERE scope_status = "core"
    AND primary_category = "virtual_instruments_and_synthesis"
  ORDER BY full_name COLLATE NOCASE;
'
```

Full-text search:

```sh
sqlite3 -header -column exports/catalogue.sqlite '
  SELECT catalogue_id, full_name, description
  FROM repository_search
  WHERE repository_search MATCH "room acoustics";
'
```

Category counts:

```sh
sqlite3 -header -column exports/catalogue.sqlite '
  SELECT c.label_en, count(*) AS repositories
  FROM repositories AS r
  JOIN categories AS c ON c.category_id = r.primary_category
  GROUP BY c.category_id
  ORDER BY repositories DESC;
'
```

## JSONL with jq

```sh
jq -c 'select(.scope_status == "adjacent")' data/repositories.jsonl
```

## Python

```python
import json
from pathlib import Path

records = [
    json.loads(line)
    for line in Path("data/repositories.jsonl").read_text(encoding="utf-8").splitlines()
]
print(len(records))
```

## Spreadsheet software

Open `exports/repositories.csv` as UTF-8 comma-separated data. `topics` is a JSON
array within one cell, preserving commas and other punctuation unambiguously.
