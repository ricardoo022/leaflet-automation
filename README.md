# Leaflet Automation

Python backend scaffold for discovering retailer leaflets, filtering relevant campaigns, and eventually extracting products for downstream automation.

## Current Status

The repository is partially implemented.

What works today:

- Lidl leaflet discovery through Lidl's public API and folhetos landing page
- parsing flyer payloads into internal models
- filtering current and upcoming leaflets
- explicit weekly filtering for the weekly job
- identifying candidate pages using `altText` and `keyWords`
- persisting discovered leaflets into SQLite
- persisting leaflet pages into SQLite for later extraction
- minimal product extraction from candidate pages
- OCR-assisted price matching and per-product screenshots
- CLI commands for discovery, extraction, and weekly discovery
- fixture-backed integration tests and live end-to-end tests

What is still incomplete:

- persisted leaflet page snapshots in SQLite
- PDF-based extraction fallback
- stronger product block detection beyond heuristic page slicing — the retailer-agnostic grid detector (`src/leaflet_automation/services/cards.py`, US-1.1) and OpenCV contour fallback (US-1.2 ✅ DONE, PR #3) are implemented and unit-tested but not yet wired into the adapter (wiring is US-3.1); the unified `CardDetector.detect()` orchestrator is US-1.3 (pending)
- more robust exact product and price extraction across leaflet layouts
- multi-retailer support and production hardening

## Architecture

The package is organized into a small set of layers under `src/leaflet_automation/`:

- `app/`: runtime configuration and logging
- `cli/`: Typer CLI entrypoints
- `core/`: shared models, enums, dedupe, date helpers, storage helpers
- `db/`: SQLite connection, schema, and repositories
- `jobs/`: orchestration for runnable flows
- `retailers/`: retailer abstraction and Lidl-specific behavior
- `services/`: OCR, image, PDF, screenshot, classification, and card-detection helpers

The current working path is discovery-first:

1. CLI command starts
2. logging is configured
3. the Lidl adapter calls the Lidl API
4. payloads are parsed into `Leaflet` and `LeafletPage`
5. leaflets are filtered by date and inferred program type
6. selected leaflets are upserted into SQLite
7. the CLI prints the result

## CLI

The project installs the `leaflets` command from `pyproject.toml`.

Available commands:

- `leaflets discover-lidl`
- `leaflets extract-lidl <leaflet-id>`
- `leaflets run-weekly-lidl`

Behavior today:

- `discover-lidl`: implemented
- `extract-lidl`: implemented, persists products and screenshots
- `run-weekly-lidl`: implemented and restricted to weekly leaflets

## Runtime and Persistence

- language/runtime target: Python 3.11+
- package root: `src/leaflet_automation`
- default database path: `data/leaflets.db`
- persistence backend: SQLite only
- schema is initialized at runtime by `src/leaflet_automation/db/schema.py`

Runtime settings are loaded from `LEAFLETS_` environment variables through `pydantic-settings`.

Important defaults:

- `LEAFLETS_DATA_DIR=data`
- `LEAFLETS_DATABASE_PATH=data/leaflets.db`
- `LEAFLETS_REQUEST_TIMEOUT_SECONDS=30.0`

## Lidl-Specific Notes

The current retailer implementation is Lidl-only and lives under `src/leaflet_automation/retailers/lidl/`.

Important facts about the current implementation:

- discovery seeds from the public folhetos landing page and falls back to verified `SEED_FLYER_IDS`
- additional leaflets are found through `relatedFlyers`
- candidate pages are selected using keyword matching in `altText` and `keyWords`
- product extraction is implemented heuristically and still accuracy-limited

The reverse-engineering source of truth for Lidl API behavior is:

- `docs/LIDL_LEAFLETS_API_RESEARCH.md`

Read that document before changing:

- discovery logic
- date filtering
- API usage assumptions

## Known Limitations

- extraction may re-fetch live leaflet metadata only as a fallback for older databases without persisted pages
- PDF extraction is still a stub
- product block detection is still heuristic (grid detector US-1.1 + contour fallback US-1.2 ✅ DONE exist in `services/cards.py` but are not wired into the adapter yet — wiring is US-3.1; the unified `CardDetector.detect()` orchestrator is US-1.3)
- live-network tests depend on Lidl endpoints and asset hosts being reachable

## Key Files

- `src/leaflet_automation/cli/main.py`: CLI commands
- `src/leaflet_automation/jobs/discover_leaflets.py`: main implemented discovery flow
- `src/leaflet_automation/jobs/extract_leaflet.py`: extraction orchestration scaffold
- `src/leaflet_automation/retailers/lidl/adapter.py`: Lidl adapter entrypoint
- `src/leaflet_automation/retailers/lidl/discovery.py`: seed-based leaflet discovery
- `src/leaflet_automation/retailers/lidl/parser.py`: payload-to-model parsing
- `src/leaflet_automation/retailers/lidl/filters.py`: target leaflet and candidate page filtering
- `src/leaflet_automation/db/schema.py`: SQLite schema
- `docs/LIDL_LEAFLETS_API_RESEARCH.md`: Lidl API research
- `docs/IMPLEMENTATION_BACKLOG.md`: product backlog and epics
- `docs/IMPLEMENTED_FEATURES.md`: inventory of already-implemented capabilities
- `docs/superpowers/specs/2026-07-08-generic-card-extraction-design.md`: generic product card extraction design

## Package Docs

Each first-level package under `src/leaflet_automation/` has its own `README.md` for maintainers:

- `src/leaflet_automation/app/README.md`
- `src/leaflet_automation/cli/README.md`
- `src/leaflet_automation/core/README.md`
- `src/leaflet_automation/db/README.md`
- `src/leaflet_automation/jobs/README.md`
- `src/leaflet_automation/retailers/README.md`
- `src/leaflet_automation/services/README.md`

## Verification Command

The currently verified syntax check for the repo is:

```bash
python3 -m compileall src
```
