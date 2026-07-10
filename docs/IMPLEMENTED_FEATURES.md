# Implemented Features Inventory

Date: 2026-07-08

This document explains, in plain language, everything the `leaflet-automation` project already does today. For each capability it says **what** it does, **how** it works in simple terms, and **where** in the code it lives (file and line, so you can jump to it). It is meant both as a learning guide for someone new to the codebase and as a map of what is already in place before the next extraction improvements land.

It complements two other documents under `docs/`: `IMPLEMENTATION_BACKLOG.md` (the roadmap of remaining work) and `superpowers/specs/2026-07-08-generic-card-extraction-design.md` (the planned fix for the extraction accuracy problems described in section 4 below).

---

## 1. The Command Line Interface (CLI)

The project is driven entirely from the terminal through a small CLI built with the `typer` library. The CLI is the only way an operator interacts with the system today; there is no web UI and no scheduled background runner wired up yet.

You run it as `leaflets <command>` because `pyproject.toml:16` registers the `leaflets` entrypoint that points at the Typer app defined in `src/leaflet_automation/cli/main.py:10`.

**`leaflets discover-lidl`** — `src/leaflet_automation/cli/main.py:18`. This is the discovery command. When you run it, it asks the Lidl adapter to find all current Lidl leaflets, filters them down to the ones that are running right now (target leaflets), prints one line per leaflet to the terminal (its ID, program type, name, title, and URL), and saves them into the local SQLite database so later commands can use them.

**`leaflets extract-lidl <leaflet-id>`** — `src/leaflet_automation/cli/main.py:27`. This is the extraction command. You give it the ID of a leaflet that was previously discovered. It loads that leaflet from the database, finds the candidate pages (the ones that look like fruit & veg offers), extracts products from each of those pages, saves the resulting products to the database, and prints a one-line summary: how many candidate pages it looked at, how many raw products it extracted, and how many unique products it actually persisted. If the ID does not exist, it prints a clear error and exits with code 1 instead of crashing.

**`leaflets run-weekly-lidl`** — `src/leaflet_automation/cli/main.py:48`. A convenience shorthand that runs discovery but only keeps leaflets classified as the `WEEKLY` program type. It prints how many weekly leaflets it found.

**Logging** — `src/leaflet_automation/app/logging.py:4` (`configure_logging`). Every CLI command goes through a Typer callback that configures logging at INFO level, so you get readable timestamps and log lines while a command runs.

---

## 2. How Lidl Leaflets Are Discovered

Discovery is the process of asking Lidl "what leaflets do you currently have?" and saving the answer. The Lidl-specific logic lives under `src/leaflet_automation/retailers/lidl/`.

### 2.1 Talking to Lidl's API

`LidlLeafletApi` in `src/leaflet_automation/retailers/lidl/api.py:11` is the HTTP client. It uses the `httpx` library and reads its base URL, user agent, and timeout from the project's settings (see section 7). It can talk to two Lidl endpoints and also download images:

- **`get_flyer(id)`** at `api.py:21` fetches the full JSON for one leaflet by its ID. Importantly for testing, if you set the `LEAFLETS_LIDL_FIXTURE_DIR` setting, it will read the JSON from a local file instead of hitting the network. That is exactly what the integration tests rely on.
- **`get_flyer_fallback()`** at `api.py:34` calls a Schwarz regional fallback endpoint that lists the current domain's leaflets.
- **`get_flyer_overview_html()`** at `api.py:42` and **`get_flyer_overview_ids()`** at `api.py:47` scrape Lidl's public folhetos landing page HTML and use regexes to pull out the flyer UUIDs embedded in `data-track-id` attributes (with a fallback to `id="flyer-..."` attributes). This is the dynamic discovery path.
- **`download_binary(url, path)`** at `api.py:54` downloads a binary file (used for page images) and creates the parent directories on the way.
- **`parse_iso_date`** at `retailers/lidl/api.py:65` parses an ISO date string like `2026-07-08T00:00:00` into a `date` object by slicing the first 10 characters.

### 2.2 The discovery algorithm

`discover_leaflets` in `src/leaflet_automation/retailers/lidl/discovery.py:21` is where the actual finding happens. It works like a small crawl:

1. It builds a list of starting flyer IDs. This uses `_initial_flyer_ids` at `discovery.py:44`, which first tries the dynamic landing-page discovery (`get_flyer_overview_ids`). If that fails or returns nothing, it falls back to a hardcoded list of three verified seed IDs called `SEED_FLYER_IDS` at `discovery.py:14`. When running against fixtures, it always uses the seeds directly.
2. It then does a breadth-first walk: for each flyer ID it has not seen yet, it fetches that flyer, parses it into a `Leaflet`, and then looks at the flyer's `relatedFlyers` list to find more IDs to visit next.
3. When the walk finishes, it de-duplicates the collected leaflets (by ID) and returns them.

This seed-plus-related-flyers walk is the heart of discovery. The seeds are a safety net so discovery still works when the landing page markup changes, and related-flyers traversal is how it expands from a seed to a full campaign.

### 2.3 Turning raw JSON into Leaflet objects

`parse_leaflet` at `src/leaflet_automation/retailers/lidl/parser.py:146` takes the raw payload from Lidl and builds the project's own `Leaflet` and `LeafletPage` objects (see section 6). It pulls the flyer's name, title, category, dates, URLs, etc. from the JSON, and for each entry under `flyer.pages` it builds a `LeafletPage` with the page's image URLs, alt text, and keywords. Two helper functions in the same file also extract product name candidates from text, and these are reused later by the extractor:

- **`extract_product_names_from_alt_text`** at `parser.py:105`. Lidl writes alt text like *"Ofertas de frutas e legumes frescos com desconto, destacando tomate cacho, mirtilos, maçã Golden e couve coração."* This function looks for marker phrases (`destacando`, `incluindo`, `com descontos em`, etc.), takes the text after the marker, and splits it on commas and the Portuguese "e". It then cleans each candidate (strips noise words like "preço", "loja", "kg") and de-duplicates. This is the primary way products are named today.
- **`extract_product_names_from_keywords`** at `parser.py:121` is the fallback. The `keyWords` field uses a compact format with `NºXX` codes, e.g. `Nº67 -31 Tomate Cacho`. This function finds each `Nº<number>` pattern, takes a small window of text before it, strips noise words, and keeps the last few tokens as a candidate name.

### 2.4 Filtering: which leaflets and which pages we care about

Not every leaflet and not every page matters. Filtering lives in `src/leaflet_automation/retailers/lidl/filters.py`.

- **`filter_target_leaflets`** at `filters.py:20` keeps only leaflets that are upcoming or currently running, based on their offer dates. Before checking, it calls `infer_program_type` to tag each leaflet with a program type.
- **`infer_program_type`** at `filters.py:9` classifies a leaflet as WEEKLY, WEEKEND, SPECIAL, or UNKNOWN by looking for words like "fim de semana", "sexta", "seman", "especial" in the leaflet's name and title.
- **`is_candidate_page`** at `filters.py:29` is the page-level filter. It decides whether a page inside a leaflet is interesting for product extraction by checking whether the page's `alt_text` plus `keyWords` text contains any of the category keywords from `retailers/lidl/keywords.py` (`CATEGORY_KEYWORDS`). This is currently the only category gate and it is keyword-based, which is simple and effective but not perfect.

### 2.5 Tying it together: discovery orchestration

The orchestration function `run_lidl_discovery` at `src/leaflet_automation/jobs/discover_leaflets.py:12` is what the `discover-lidl` CLI command calls. It is intentionally small and linear: it creates the Lidl adapter, opens a SQLite connection, asks the adapter to discover leaflets, asks it to filter them down to targets, optionally restricts them to a set of allowed program types, and saves them with the `LeafletRepository`. The connection is closed in a `finally` block so it never leaks.

The weekly wrapper `run_weekly_lidl` at `src/leaflet_automation/jobs/run_weekly.py:7` simply calls that function with `allowed_program_types={ProgramType.WEEKLY}`.

---

## 3. How Products Are Extracted From a Leaflet Page

This is the part the project is actively trying to improve, because it works end-to-end but has two confirmed accuracy bugs. It is worth understanding what exists today before reading the design spec that replaces parts of it.

The entry point is `LidlAdapter.extract_products_from_page` at `src/leaflet_automation/retailers/lidl/adapter.py:44`. Given a leaflet and one page, it produces a list of `ExtractedProduct` objects. The flow, in plain terms:

1. **Classify the page.** It joins the page's `alt_text` and `keyWords` and asks the product classifier what category that text belongs to (`ProductClassifier.classify` at `src/leaflet_automation/services/classifier.py:11`). It also separately checks whether the page is a "produce" page by looking for the words `frutas`, `fruta`, `legumes`, or `frescos` in the normalized alt text, so that names that do not classify on their own can still inherit the page's produce category.
2. **Get product name candidates.** It first tries the alt-text name extractor (`adapter.py:54`). For every name it finds, it tries to classify it on its own; if classification fails but the page is a produce page, it assigns the page's category as a fallback (`adapter.py:57`). Each name that ends up with a category becomes a provisional `ExtractedProduct`.
3. **Fallback to keywords (currently gated).** At `adapter.py:76`, if and only if alt text produced no names, it tries the keyword name extractor instead. This `if not alt_text_products:` is the **known limitation**: when alt text gives some names, keyword names are skipped, so products that are only visible in the keywords field are never included. Fixing this to merge both sources is one of the planned improvements.
4. **Attach visuals and prices.** If any products were found, it calls `_attach_screenshots` at `adapter.py:111`, which is where OCR, screenshots, and price matching happen. This step is described in section 4 below because it involves several services.

The classifier itself, `ProductClassifier` at `src/leaflet_automation/services/classifier.py:11`, is simple: it normalizes text (strips accents and lowercases via `normalize_text` in the same file) and returns the first category whose keyword list has any substring match inside the normalized text. If nothing matches, it returns `None`, which signals "we could not classify this."

---

## 4. Screenshots, OCR, and Price Extraction

When `_attach_screenshots` runs at `src/leaflet_automation/retailers/lidl/adapter.py:111`, it does several things in sequence:

1. **Download the full page image.** It picks the best available image URL (prefers the `zoom_url`, falls back to `image_url`) and downloads it with `LidlLeafletApi.download_binary`, saving it under `data/<retailer>/<leaflet_id>/pages/page-NN.png` (the path is built by `leaflet_page_image_path` at `src/leaflet_automation/core/storage.py:15`).
2. **Run OCR on the image.** It calls `OcrService.extract_lines` at `src/leaflet_automation/services/ocr.py:32`. The OCR engine is `rapidocr-onnxruntime`, a local (no-cloud) OCR library. For every block of text it finds, it returns an `OcrLine` (defined at `ocr.py:8`) containing the text, an OCR confidence score, and the bounding box (`left`, `top`, `right`, `bottom`) in pixel coordinates. `OcrLine` also exposes `center_x` and `center_y` properties that the price matcher uses for proximity calculations.
3. **Try to attach a price to each product.** `_attach_prices` at `adapter.py:123` does this per product. For each product name, it calls `_match_product_label` at `adapter.py:136`, which scores each OCR line by how many of the name's tokens appear in it (with a bonus when the line starts with the full name) and picks the best-scoring line. Then it calls `_match_price_line` at `adapter.py:161`, which scans the OCR lines for ones that look like a price using the regex `(?<!\d)(\d+[.,]\d{2})(?!\d)` (a number with a two-digit decimal, either with a comma or a dot), and applies proximity filters: it skips lines too far below the label line, lines that are obviously to its left, and lines that look like weight/quantity markers (containing `kg=`, `n°`, `n9`). It then picks the price line with the smallest combined horizontal + vertical penalty. If both are found, it sets `price_text` (with the decimal separator normalized to a comma for display) and `price_value` (a float), and appends the OCR evidence to `raw_text`.
4. **Detect product blocks (the current, buggy way).** `_attach_screenshots` then calls `ImageService.detect_product_blocks` at `src/leaflet_automation/services/images.py:10`. This is the source of the screenshot bug: given an expected number of blocks, it simply splits the page image into that many **equal horizontal strips** spanning the full width. So for 4 products on a 1415×2400 page, it produces 4 crops of 1415×600 each, meaning each screenshot contains the full width of the page and a quarter of the height — which on a grid flyer means each screenshot shows an entire row with multiple products in it. A retailer-agnostic replacement exists (`CardDetector._grid_boxes()` in `src/leaflet_automation/services/cards.py`, US-1.1) but is NOT yet wired into `_attach_screenshots` (wiring is US-3.1); it detects clean grids via projection profiles but saturates to full-width strips on dense real pages, so the OpenCV contour fallback (US-1.2) and per-card regression (US-5.2) are still pending.
5. **Crop and save one screenshot per product.** For each product, it takes the corresponding block (using `min(index, len(boxes) - 1)` so the last box absorbs overflow), computes a screenshot path via `product_screenshot_path` at `src/leaflet_automation/core/storage.py:20` (something like `data/lidl/<leaflet_id>/products/page-04-maçã-golden-03.png`), and crops the image with `ScreenshotService.crop` at `src/leaflet_automation/services/screenshots.py:7`.

The `ScreenshotService` at `screenshots.py:6` is a thin wrapper around PIL's `Image.crop`. Its `crop` method takes an input image path, a box `(x, y, w, h)`-style tuple, and an output path, creates the parent directory, crops, and saves. It has no Lidl-specific knowledge, which is good — the design spec reuses it as-is to crop real card boxes instead of strips.

`OcrService` also has an `extract_text` method at `ocr.py:29` that simply joins all OCR line texts with ` | ` separators; it is a convenience used mainly in tests.

`ImageService.preprocess_for_ocr` at `services/images.py:7` is a stub: it returns the same path it was given unchanged. It exists as a hook so preprocessing (contrast, rotation, etc.) can be added later without changing call sites.

---

## 5. Extraction Orchestration and Persistence

The `extract-lidl` CLI command calls `run_lidl_extraction` at `src/leaflet_automation/jobs/extract_leaflet.py:32`. This is the function that turns "a leaflet ID" into "rows in the `products` table." Step by step:

1. It creates a `LidlAdapter`, opens a SQLite connection via `connect` at `src/leaflet_automation/db/sqlite.py:5`, and makes sure the schema exists via `initialize_schema` at `src/leaflet_automation/db/schema.py:4` (which runs `CREATE TABLE IF NOT EXISTS` for `leaflets`, `products`, and `leaflet_pages`).
2. It loads the leaflet by ID using `LeafletRepository.get_by_id` at `src/leaflet_automation/db/repositories/leaflets.py:11`. If the ID is not in the database, it raises a `LookupError` with a friendly message; the CLI catches that and prints it as an error instead of crashing.
3. If the leaflet was discovered earlier but its pages were not persisted (an older database situation), it re-fetches the live flyer via `adapter.get_leaflet`, preserves the previously inferred `program_type`, saves the refreshed leaflet back with `LeafletRepository.upsert_many`, and continues.
4. It asks the adapter for candidate pages and loops over them, calling `extract_products_from_page` for each (this is the part described in sections 3 and 4).
5. It de-duplicates the accumulated products with `dedupe_products` at `src/leaflet_automation/core/dedupe.py:11`, which keys on `(leaflet_id, page_number, name, price_text)` so the same product from both alt text and keywords collapses to one row.
6. It prepares the persistence side: `ProductRepository.delete_by_leaflet_id` at `src/leaflet_automation/db/repositories/products.py:10` first wipes any previously extracted products for that leaflet, so re-running extraction is idempotent. Then, if there are unique products, `ProductRepository.insert_many` at `products.py:17` inserts them all in one `executemany` call.
7. It returns an `ExtractionResult` (defined at `extract_leaflet.py:14`) carrying the leaflet, the count of candidate pages, the count of extracted products, and the count of persisted products — exactly the numbers the CLI prints.

There is also a simpler single-purpose helper `extract_lidl_leaflet` at `extract_leaflet.py:21` that extracts products from a leaflet object in memory without any database interaction; it is used where you just want the extraction logic with persistence handled separately.

### 5.1 The leaflet repository

`LeafletRepository` at `src/leaflet_automation/db/repositories/leaflets.py:7` handles all leaflet and page persistence:

- **`get_by_id`** at `leaflets.py:11` selects the leaflet row and also pulls its pages (ordered by `page_number`) via `_get_pages` at `leaflets.py:115`, building a full `Leaflet` object including pages.
- **`upsert_many`** at `leaflets.py:39` does an `INSERT ... ON CONFLICT(id) DO UPDATE` so a leaflet can be saved again safely, then deletes and re-inserts all that leaflet's pages (since pages are keyed by `(leaflet_id, page_number)`).

### 5.2 The product repository

`ProductRepository` at `src/leaflet_automation/db/repositories/products.py:6` is small: `delete_by_leaflet_id` clears products for a leaflet, and `insert_many` writes a list of `ExtractedProduct` objects, converting each into the 13 columns of the `products` table (including converting `Promise`/date fields and the `screenshot_path` to strings).

### 5.3 Storage helpers

`src/leaflet_automation/core/storage.py` centralizes filesystem path conventions: `leaflet_directory`, `leaflet_page_image_path`, `product_screenshot_path`, and `ensure_directory`. This is why screenshots always land under `<data_dir>/<retailer>/<leaflet_id>/products/page-NN-<name>.png` and page images under `.../pages/page-NN.png`.

---

## 6. Domain Models

The project uses Pydantic models for all data in flight, defined in `src/leaflet_automation/core/models.py`.

- **`LeafletPage`** at `models.py:9` represents one page of a flyer: its number, image URLs (image, zoom, thumbnail), an optional `local_image_path` that gets set after the image is downloaded, and the `alt_text` and `keywords` strings used for extraction.
- **`Leaflet`** at `models.py:20` represents a whole flyer: its ID, retailer, name, title, category, status, inferred `program_type`, all the date fields (start, end, offer start, offer end), URLs (including PDF and high-res PDF URLs for future PDF extraction), thumbnail, and its `pages` list.
- **`ExtractedProduct`** at `models.py:40` is the output of product extraction: retailer, leaflet ID, page number, program type, category, name, optional price text and numeric price value, promo start/end dates, optional screenshot path, raw text (source evidence), and an optional confidence score.
- **`RunRecord`** at `models.py:56` is a scaffold for tracking run status; it is defined but not actively used by any flow today.

Enums live in `src/leaflet_automation/core/enums.py`: `ProgramType` (`WEEKLY`, `WEEKEND`, `SPECIAL`, `UNKNOWN`) and `RunStatus`. These feed filtering, persistence, and the model defaults.

---

## 7. Configuration

All runtime configuration uses `pydantic-settings` and is driven by `LEAFLETS_` environment variables, defined in `src/leaflet_automation/app/config.py`. Verified defaults include `LEAFLETS_DATA_DIR=data` (where downloaded images and screenshots go), `LEAFLETS_DATABASE_PATH=data/leaflets.db` (the SQLite file), and `LEAFLETS_REQUEST_TIMEOUT_SECONDS=30.0` (the HTTP timeout used by `LidlLeafletApi`). There is also a `LEAFLETS_LIDL_FIXTURE_DIR` setting used to run against locally cached JSON payloads instead of the live Lidl endpoints.

---

## 8. Tests

The project has these test files plus offline fixtures:

- **`tests/test_lidl_extraction_integration.py`** exercises Lidl parsing and extraction using fixtures under `tests/fixtures/`. This is the test that the new card-extraction regression test will extend.
- **`tests/test_us_4_1_keyword_union.py`** covers the US-4.1 fix (keyword fallback runs in union with alt-text) using the offline produce-leaflet fixture.
- **`tests/test_cards.py`** covers the US-1.1 grid detector (`CardBox`, `CardDetector._grid_boxes`): CardBox center math, degenerate images (empty/solid-color → `[]`), a synthetic 2×2 grid (4 sorted, area-non-overlapping cells + strip-regression guard), and a real `page-04.png` smoke test (≥2 boxes, sorted, >40 % page coverage). Runs offline via `.venv/bin/python -m unittest tests.test_cards`.
- **`tests/test_lidl_live_e2e.py`** is a live, network-dependent end-to-end test that actually calls the Lidl endpoints and asset hosts; it only passes when those hosts are reachable.
- **`tests/fixtures/`** holds the offline JSON payloads so the integration test can run without network access.

There is no declared test runner configuration in `pyproject.toml` yet; pytest is available in the venv but the project has not formalized how tests should be invoked.

---

## 9. Known Limitations (things that are implemented but not ideal)

These are existing behaviors, not missing features, and they are the reason the new design spec exists:

- **Screenshots span multiple products.** `ImageService.detect_product_blocks` at `services/images.py:10` slices the page into equal horizontal strips, so each screenshot can contain a whole row of products instead of just one product card. This is the bug that triggered the redesign. A grid detector (`CardDetector` in `services/cards.py`, US-1.1) now exists but is not wired into the adapter yet (US-3.1); it handles clean grids but saturates on dense real pages, so the contour fallback (US-1.2) is still pending.
- **Keyword names are dropped when alt text has names.** The `if not alt_text_products:` branch at `adapter.py:76` means products only visible in the keywords field are silently lost when alt text yields anything. The fix is to merge both sources.
- **PDF extraction is still a stub.** `services/pdf.py` exists but does not implement real PDF parsing.
- **Test configuration is not declared.** `pyproject.toml` does not list pytest or any test runner config.
- **Some installed dependencies are not declared in `pyproject.toml`.** `opencv-python` and `numpy` are present in the venv and used by the planned card-detection work, but they are not in the project's declared `dependencies` list.

---

## 10. Project Layout and Documentation

- **Package metadata and declared dependencies** live in `pyproject.toml` (declared deps: `httpx`, `Pillow`, `pydantic`, `pydantic-settings`, `rapidocr-onnxruntime`, `typer`). The CLI script is `leaflets`, mapped to `leaflet_automation.cli.main:app`.
- **Each first-level package** under `src/leaflet_automation/` (`app`, `cli`, `core`, `db`, `jobs`, `retailers`, `services`) has its own `README.md` for maintainers.
- **The top-level `README.md`** describes the architecture, limitations, and the key files to look at.
- **`docs/LIDL_LEAFLETS_API_RESEARCH.md`** is the reverse-engineering source of truth for how the Lidl endpoints behave and should be read before changing discovery, date filtering, or API usage.
- **`docs/IMPLEMENTATION_BACKLOG.md`** is the existing product backlog of remaining work.
- **`docs/superpowers/specs/2026-07-08-generic-card-extraction-design.md`** is the design for the next extraction improvement (retailer-agnostic card detection, per-card OCR, and per-card screenshots).