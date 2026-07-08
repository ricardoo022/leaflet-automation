# AGENTS

- Stack is Python only. Project metadata lives in `pyproject.toml`; package root is `src/leaflet_automation`.
- Install/run entrypoint from `pyproject.toml`: CLI command is `leaflets`, implemented by `src/leaflet_automation/cli/main.py`.
- Verified syntax check command is `python3 -m compileall "src"`. There is no tracked test, lint, formatter, or typecheck config yet.
- Main runnable flow today is discovery, not extraction: `leaflets discover-lidl` and `leaflets run-weekly-lidl` call `src/leaflet_automation/jobs/discover_leaflets.py`.
- Current persistence is SQLite only. Schema is created at runtime by `src/leaflet_automation/db/schema.py`; default DB path is `data/leaflets.db` from `src/leaflet_automation/app/config.py`.
- Runtime config uses `LEAFLETS_` environment variables via `pydantic-settings`. Verified defaults include `LEAFLETS_DATA_DIR=data`, `LEAFLETS_DATABASE_PATH=data/leaflets.db`, and `LEAFLETS_REQUEST_TIMEOUT_SECONDS=30.0`.
- Lidl code is adapter-based: shared interfaces are in `src/leaflet_automation/retailers/base.py`; Lidl-specific logic lives under `src/leaflet_automation/retailers/lidl/`.
- Discovery is currently seeded, not fully dynamic. `src/leaflet_automation/retailers/lidl/discovery.py` starts from hardcoded verified `SEED_FLYER_IDS` and expands through `relatedFlyers`.
- Do not assume product extraction works yet. `LidlAdapter.extract_products_from_page()` and the OCR/PDF/image/screenshot services are intentional `NotImplementedError` stubs.
- Candidate Lidl pages are currently filtered only by `altText`/`keyWords` keyword matching in `src/leaflet_automation/retailers/lidl/filters.py`; this is the current category gate for `Frutas & Legumes` work.
- The detailed reverse-engineering source of truth for Lidl endpoints is `docs/LIDL_LEAFLETS_API_RESEARCH.md`. Read it before changing discovery, date filtering, or API usage.
