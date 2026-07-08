# Data

- `raw/` — raw ingested source data (git-ignored; do not commit).
- `private/` — any private/confidential inputs (git-ignored; do not commit).

`fli.db` is the current inspectable SQLite corpus for the data-first spike.
Its `raw_items` table is evidence, not the final modeled schema. The final
database artifact policy is still open; do not design around packaging until
the registry/extraction schema is clearer.
