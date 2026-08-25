-- Run with: sqlite3 -header -column exports/catalogue.sqlite < examples/query.sql
SELECT full_name, category_label_en
FROM repository_current
WHERE scope_status = 'core'
  AND primary_category = 'musical_instrument_acoustics'
ORDER BY full_name COLLATE NOCASE
LIMIT 5;
