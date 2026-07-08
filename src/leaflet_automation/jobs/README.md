# `jobs`

## Purpose

This package contains thin orchestration flows for runnable business operations.

Jobs connect the CLI to adapters, configuration, and persistence.

## What Currently Works

- Lidl discovery runs end-to-end
- schema initialization is part of the discovery flow
- selected leaflets are stored in SQLite
- extraction runs end-to-end and persists products
- a weekly wrapper job exists and filters weekly leaflets only

## Important Files

- `discover_leaflets.py`
  - main implemented business flow today
  - creates the adapter and database connection
  - initializes schema
  - discovers leaflets
  - filters target leaflets
  - persists selected leaflets

- `run_weekly.py`
  - small wrapper around the discovery job
  - returns the number of weekly leaflets only

- `extract_leaflet.py`
  - extraction orchestration flow
  - loops through candidate pages
  - deduplicates and persists products

## How It Fits Into The Flow

The intended pattern is:

1. CLI command calls a job
2. the job coordinates adapters and repositories
3. lower-level logic does the actual API, parsing, or persistence work

## Maintainer Notes

- `discover_leaflets.py` is the most complete file in the repository from an orchestration perspective.
- `extract_leaflet.py` still re-fetches live leaflet metadata because pages are not persisted in SQLite yet.
- There is no run-tracking, scheduling, retry policy, or job state persistence yet.
