# `db`

## Purpose

This package contains the SQLite persistence layer:

- connection setup
- schema creation
- repository classes

It is the only persistence backend currently implemented in the repository.

## What Currently Works

- opens SQLite connections
- creates the database parent directory if needed
- initializes schema at runtime
- upserts discovered leaflets
- can insert extracted product rows if product objects are provided

## Important Files

- `sqlite.py`
  - opens a SQLite connection
  - sets `sqlite3.Row`

- `schema.py`
  - creates the `leaflets` table
  - creates the `products` table

- `repositories/leaflets.py`
  - provides `LeafletRepository`
  - currently supports `upsert_many()` only

- `repositories/products.py`
  - provides `ProductRepository`
  - currently supports `insert_many()` only

## How It Fits Into The Flow

Current implemented path:

1. a job opens the database
2. schema is initialized
3. selected leaflets are persisted

Future intended path:

1. load a leaflet for extraction
2. extract products
3. dedupe products
4. persist extracted product rows

## Maintainer Notes

- The schema is initialized at runtime, which is fine for bootstrap but is not a migration system.
- The `leaflets` table stores leaflet-level metadata only. It does not store page records.
- That missing page persistence is a major gap for any extraction flow that starts from a persisted leaflet ID.
- Repository support is currently write-oriented. Read methods are mostly missing.
- The `products` table has no uniqueness constraints yet, so repeated extraction runs can duplicate rows.
