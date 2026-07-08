# `app`

## Purpose

This package holds application-wide runtime concerns:

- configuration
- environment-variable loading
- logging setup

It is intentionally small and sits near the top of the dependency tree.

## What Currently Works

- runtime settings are loaded with `pydantic-settings`
- settings use the `LEAFLETS_` environment prefix
- logging can be configured from the CLI entrypoint
- the Lidl API client reads timeout and user-agent settings from here

## Important Files

- `config.py`
  - defines the `Settings` model
  - loads configuration from environment variables
  - exposes a module-level `settings` object

- `logging.py`
  - configures process-wide logging
  - used by the CLI callback before running commands

## Default Settings

Key defaults in `config.py`:

- `data_dir = data`
- `database_path = data/leaflets.db`
- `retailer = lidl`
- `request_timeout_seconds = 30.0`
- a browser-like default `User-Agent`

## How It Fits Into The Flow

Typical usage path:

1. CLI starts
2. `configure_logging()` is called
3. downstream modules import `settings`
4. API and DB flows use configuration values from this package

## Maintainer Notes

- `settings` is created at import time, so environment variables must be ready before module import.
- The package is generic in shape, but the actual application is currently Lidl-only.
- `data_dir` exists for broader storage use, but most implemented code currently depends more directly on `database_path`.
- There is no multi-environment config strategy yet beyond the default Pydantic settings behavior.
