#!/usr/bin/env python3
"""Print core musical-instrument-acoustics records from the SQLite export."""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

with sqlite3.connect(ROOT / "exports/catalogue.sqlite") as connection:
    rows = connection.execute(
        """
        SELECT catalogue_id, full_name, category_label_en
        FROM repository_current
        WHERE scope_status = 'core'
          AND primary_category = 'musical_instrument_acoustics'
        ORDER BY full_name COLLATE NOCASE
        """
    )
    for catalogue_id, full_name, category in rows:
        print(f"{catalogue_id}\t{full_name}\t{category}")
