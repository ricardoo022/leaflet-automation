# Implemented Features Inventory

Date: 2026-07-08
Scope: existing capabilities of `leaflet-automation` as they stand today. Each entry points at the file where the behavior lives, so it doubles as a navigation aid. This complements `docs/IMPLEMENTATION_BACKLOG.md` (the roadmap of remaining work) and `docs/superpowers/specs/2026-07-08-generic-card-extraction-design.md` (the next extraction fix).

## 1. CLI

| Feature | Where | Notes |
|---|---|---|
| `leaflets discover-lidl` | `src/leaflet_automation/cli/main.py:18` | Lists each discovered target leaflet |
| `leaflets extract-lidl <leaflet-id>` | `src/leaflet_automation/cli/main.py:27` | Runs real extraction + persistence; prints summary |
| `leaflets run-weekly-lidl` | `src/leaflet_automation/cli/main.py:48` | Convenience wrapper over weekly discovery |
| Logging configuration | `src/leaflet_automation/app/logging.py:4` | INFO level, applied at CLI entry |
| Entrypoint `leaflets` | `pyproject.toml:16` → `cli/main.py:app` | Packaged via `typer` |

## 2. Discovery (Lidl)

| Feature | Where | Notes |
|---|---|---|
| Public API client | `src/leaflet_automation/retailers/lidl/api.py:11` (`LidlLeafletApi`) | httpx, configurable UA/timeout, fixture support |
| `get_flyer(id)` | `api.py:21` | Fetches one flyer JSON; uses fixture if `LEAFLETS_LIDL_FIXTURE_DIR` set |
| `get_flyer_fallback()` | `api.py:34` | `flyer-fallback` endpoint (Schwarz regional) |
| Landing-page ID discovery | `api.py:47` (`get_flyer_overview_ids`) | Scrapes `data-track-id`/`id="flyer-..."` from listing HTML |
| `download_binary()` | `api.py:54` | Saves page images, creates parent dirs |
| Seed-based discovery | `src/leaflet_automation/retailers/lidl/discovery.py:21` | `SEED_FLYER_IDS` + BFS over `relatedFlyers`; seeding via `_initial_flyer_ids()` |
| Landing-page + seed fallback | `discovery.py:44` (`_initial_flyer_ids`) | Uses overview IDs; falls back to hardcoded seeds on failure |
| Discovery orchestration | `src/leaflet_automation/jobs/discover_leaflets.py:12` (`run_lidl_discovery`) | Adapter → filter → persist; optional `allowed_program_types` |
| Weekly discovery job | `src/leaflet_automation/jobs/run_weekly.py:7` (`run_weekly_lidl`) | Restricts to `ProgramType.WEEKLY` |

## 3. Parsing & Filtering (Lidl)

| Feature | Where | Notes |
|---|---|---|
| `parse_leaflet(payload)` | `src/leaflet_automation/retailers/lidl/parser.py:146` | Builds `Leaflet` + `LeafletPage` from Schwarz flyer JSON |
| Name extraction from alt text | `parser.py:105` (`extract_product_names_from_alt_text`) | Marker-aware ("destacando", "incluindo", ...), de-dupes |
| Name extraction from keywords | `parser.py:121` (`extract_product_names_from_keywords`) | Parses `NºXX` patterns with back-window context |
| ISO date parsing | `retailers/lidl/api.py:65` (`parse_iso_date`) | `YYYY-MM-DD` slicing |
| Target leaflet filtering | `retailers/lidl/filters.py:20` (`filter_target_leaflets`) | Date window via `is_upcoming_or_current` |
| Program-type inference | `filters.py:9` (`infer_program_type`) | WEEKLY / WEEKEND / SPECIAL / UNKNOWN by name |
| Candidate-page filter | `filters.py:29` (`is_candidate_page`) | Keyword substring match on `altText` + `keyWords` |
| Category keyword map | `retailers/lidl/keywords.py` (`CATEGORY_KEYWORDS`) | Consumed by classifier + filters |

## 4. Extraction (Lidl) — **implemented but accuracy-limited**

> See the design spec for known bugs in this area (equal-strip slicing, exclusive keyword gating). Everything here works end-to-end, but the per-product framing and identification have confirmed gaps being addressed by the new card-extraction work.

| Feature | Where | Notes |
|---|---|---|
| Page-level name list via alt text | `adapter.py:54` (`extract_product_names_from_alt_text`) inside `extract_products_from_page` | Primary identity source |
| Keyword fallback for names | `adapter.py:76` | Runs only when alt-text yields nothing (known limitation) |
| Product classification | `services/classifier.py:11` (`ProductClassifier`) | Returns a category by keyword overlap |
| Produce-context fallback category | `adapter.py:47` | If page is frutas/legumes, unnamed-but-classified names still get a category |
| OCR text extraction | `services/ocr.py:25` (`OcrService`) | RapidOCR via `rapidocr_onnxruntime`; returns `OcrLine`s with bboxes |
| OCR line geometry | `services/ocr.py:8` (`OcrLine`) | `left/top/right/bottom`, `center_x/center_y` |
| Product label matching | `adapter.py:136` (`_match_product_label`) | Token-overlap scoring against OCR lines |
| Price line matching | `adapter.py:161` (`_match_price_line`) | Regex `\d+[.,]\d{2}` + proximity to label line |
| Price attachment | `adapter.py:123` (`_attach_prices`) | Normalizes `.` → `,` decimal, sets `price_text`/`price_value` |
| Product-block detection | `services/images.py:10` (`detect_product_blocks`) | Heuristic: equal vertical strips (known limitation) |
| OCR image pre-processing | `services/images.py:7` (`preprocess_for_ocr`) | Pass-through stub returning the same path |
| Screenshot per product | `services/screenshots.py:7` (`ScreenshotService.crop`) | PIL crop to disk |
| Screenshot path helper | `core/storage.py:20` (`product_screenshot_path`) | `<retailer>/<leaflet_id>/products/page-NN-<name>.png` |
| Page image download | `adapter.py:111` (`_attach_screenshots`) | Downloads zoom/preview image via `download_binary` |

## 5. Orchestration & Persistence

| Feature | Where | Notes |
|---|---|---|
| Extraction orchestration | `src/leaflet_automation/jobs/extract_leaflet.py:32` (`run_lidl_extraction`) | Lookup → candidate pages → extract → dedupe → persist |
| Leaflet lookup by ID | `db/repositories/leaflets.py:11` (`LeafletRepository.get_by_id`) | Returns `Leaflet|null` with pages |
| Stale-DB page refresh | `extract_leaflet.py:43` | Re-fetches the flyer if pages were not persisted |
| Leaflet upsert | `db/repositories/leaflets.py:39` (`upsert_many`) | `INSERT ... ON CONFLICT(id) DO UPDATE`, rewires pages |
| Page persistence | `db/repositories/leaflets.py:89` | `leaflet_pages` table |
| Product repository | `db/repositories/products.py:6` (`ProductRepository`) | `insert_many`, `delete_by_leaflet_id` |
| Pre-extraction clearing | `products.py:10` (`delete_by_leaflet_id`) | Idempotent re-extraction per leaflet |
| Deduplication | `core/dedupe.py` | `dedupe_leaflets`, `dedupe_products` (key by leaflet/page/name/price) |
| SQLite schema bootstrap | `db/schema.py:4` (`initialize_schema`) | Auto-creates `leaflets`, `products`, `leaflet_pages` |
| SQLite connection | `db/sqlite.py:5` (`connect`) | `row_factory=Row`, parent-dir creation |
| Storage helpers | `core/storage.py` | `leaflet_directory`, `leaflet_page_image_path`, `product_screenshot_path`, `ensure_directory` |

## 6. Domain Models

| Feature | Where | Notes |
|---|---|---|
| `Leaflet` / `LeafletPage` | `core/models.py:20` | Pydantic; includes PDF URLs, thumbnails, local image path |
| `ExtractedProduct` | `core/models.py:40` | retailer, leaflet_id, page, program_type, category, name, price_text/value, promo start/end, screenshot_path, raw_text, confidence |
| `RunRecord` | `core/models.py:56` | Status tracking scaffold |
| `ProgramType` / `RunStatus` | `core/enums.py` | `WEEKLY/WEEKEND/SPECIAL/UNKNOWN` and run statuses |

## 7. Configuration

| Feature | Where | Notes |
|---|---|---|
| Pydantic-settings config | `src/leaflet_automation/app/config.py` | `LEAFLETS_*` env vars |
| Verified defaults | `AGENTS.md` | `LEAFLETS_DATA_DIR=data`, `LEAFLETS_DATABASE_PATH=data/leaflets.db`, `LEAFLETS_REQUEST_TIMEOUT_SECONDS=30.0` |

## 8. Testing

| Feature | Where | Notes |
|---|---|---|
| Lidl parsing + extraction tests | `tests/test_lidl_extraction_integration.py` | Uses fixtures under `tests/fixtures/` |
| Live end-to-end test | `tests/test_lidl_live_e2e.py` | Network-dependent |
| Fixtures | `tests/fixtures/` | Offline payload snapshots |

## 9. Known Limitations (implemented behaviors, not missing features)

- Product-block detection is **heuristic equal-strip slicing** → screenshots span multiple adjacent products (the bug being fixed by the new card-extraction spec).
- Keyword fallback for names is **gated exclusively by alt-text having any names** → undercounted products.
- PDF extraction is a stub (`services/pdf.py`) — not implemented.
- Test setup and runner config are not declared in `pyproject.toml`.
- `opencv-python` and `numpy` are installed in the venv but not declared in `pyproject.toml` dependencies.

## 10. Tooling / Project

| Feature | Where |
|---|---|
| Package metadata | `pyproject.toml` |
| Declared deps | `httpx`, `Pillow`, `pydantic`, `pydantic-settings`, `rapidocr-onnxruntime`, `typer` |
| CLI script | `leaflets` → `leaflet_automation.cli.main:app` |
| Per-package readme | `src/leaflet_automation/<pkg>/README.md` (one per subsystem) |
| Top-level README | `README.md` (architecture, limitations, key files) |
| API research source of truth | `docs/LIDL_LEAFLETS_API_RESEARCH.md` |
| Product backlog | `docs/IMPLEMENTATION_BACKLOG.md` |
| Extraction fix design | `docs/superpowers/specs/2026-07-08-generic-card-extraction-design.md` |