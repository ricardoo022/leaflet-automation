# Generic Product Card Extraction — Design Spec

Date: 2026-07-08
Status: Approved (pending user review)
Supersedes relevant sections of: `docs/IMPLEMENTATION_BACKLOG.md` (Epic 2 / Epic 3 re: extraction accuracy & screenshots)

## 1. Problem Statement

The current leaflet extraction pipeline has two confirmed mistakes that prevent it from meeting the requirement *"screenshot must contain only the product we want; identify the product and extract all the data"*:

1. **Framing ignores the grid.** `src/leaflet_automation/services/images.py:10` `detect_product_blocks()` slices each page into `N` equal **horizontal, full-width** strips of size `width × (height/N)`. On a grid flyer (rows × columns) each "product screenshot" therefore contains a whole row with 2+ products sitting side-by-side.
   - Evidence: `demo_screenshots/.../page-04.png` is 1415×2400; the extractor thinks there are 4 products and produces 4 crops of 1415×600 each — every crop spans the full page width and contains multiple product cards.
2. **Identification undercounts products.** `src/leaflet_automation/retailers/lidl/adapter.py:76` skips the keyword fallback entirely whenever `alt_text` yields any names. Alt text only lists the "destaque" products (e.g. 4 on page-04), but the page's `keyWords` list ~8 more actually visible products (`cebola`, `pêssego`, `curgete`, `laranja`, `sumo xxl`, ...). As soon as alt-text gives names, the other half of the page is never extracted.

A third structural problem the user wants addressed:

3. **Logic is Lidl-coupled.** Extraction lives under `src/leaflet_automation/retailers/lidl/`. The same framing/identification mistakes will recur per-company instead of being solved once. The user's goal: *"work for every type of newspaper, every type of company"*.

## 2. Goals & Non-Goals

### Goals
- Each extracted product's screenshot contains exactly one product card.
- Every visible product on a page is identified (no silent drops due to alt-text gating).
- Price and name are read from text that actually belongs to the same card as the product.
- The detection/extraction core is **retailer-agnostic** and reusable by any future retailer adapter (Continente, Pingo Doce, ...). Lidl is the first consumer, not the only one.

### Scope focus: fruits only (this slice)

The **success criterion for this slice is scoped to fruits** ("Frutas"). The category already exists in `src/leaflet_automation/retailers/lidl/keywords.py:2` (`CATEGORY_KEYWORDS["frutas"]`: banana, maçã, mirtilos, mamão, pera, pêssego, laranja, uva, melão, morango, ...).

What this means concretely:
- The candidate-page and product filters (`filters.py`, `classifier.py`) preserve all categories, but the **acceptance tests and regression verification for this slice assert completeness only on fruit cards** — i.e. "every fruit on the latest leaflet's produce pages is extracted, none dropped."
- The card-detection + per-card OCR infrastructure is built generically so that "vegetables" ("Legumes") and other categories work without rewrites later — we simply do not assert completion for them in this slice.
- Rationale: "every fruit" is a sharp, measurable success criterion ("the latest leaflet's produce pages → one row + one screenshot per fruit card, nothing missing"). Vegetables/other categories reuse the same machinery in a future slice.

### Non-Goals (this slice)
- Wiring the generic extractor into a non-Lidl retailer (no fixtures for other retailers exist yet).
- Exact price-accuracy guarantees across all layouts (heuristics improve accuracy; no formal accuracy target).
- PDF-based extraction (tracked separately in IMPLEMENTATION_BACKLOG "Not Implemented").
- No external/proprietary AI/LLM service is introduced. We use already-installed local libraries only.

## 3. Glossary

- **Card** — one product region on a leaflet page (a "product card": photo + name + price). One card = one product.
- **CardBox** — a bounding box `(x, y, w, h)` for a card on the page image, in pixel coordinates.
- **Projection profile** — sum of dark-pixel energy per row/column; minima = whitespace gaps = grid lines.
- **OCR line** — `OcrLine` from `src/leaflet_automation/services/ocr.py` (text + score + bbox).
- **Adapter** — `RetailerAdapter` subclass (`retailers/base.py`) implementing per-retailer discovery + extraction.

## 4. Solution Direction (agreed)

A retailer-agnostic **card detection** service in `src/leaflet_automation/services/cards.py` that:
1. Detects the page grid via **projection-profile** whitespace-gap analysis (PIL + numpy).
2. Falls back to **OpenCV contour detection** when no clean grid is found (decorative/non-grid layouts).
3. Returns sorted card bounding boxes.
4. Assigns each RapidOCR text line to the card whose box contains the line center.
5. Per card: derives name from the card's text lines and price via a `\d+[,.]\d{2}` regex inside that card's lines only.
6. Crops each card box to one PNG = one product screenshot.
7. Fixes the keyword-fallback gating so it runs in union with alt-text.

## 5. Architecture

### 5.1 Component boundaries

```
services/cards.py        ← NEW. Retailer-agnostic. CardDetector + CardBox + projection-profile + contour fallback.
services/images.py       ← existing ImageService.detect_product_blocks() becomes DEPRECATED; replaced by CardDetector.
services/ocr.py          ← unchanged (OcrLine / OcrService already exist).
services/screenshots.py   ← unchanged API; now receives a CardBox instead of an equal-strip box.
retailers/lidl/adapter.py ← consumes CardDetector; assigns OCR lines to cards; per-card name+price; per-card crop.
retailers/lidl/parser.py  ← name helpers reused as fallback when OCR name is missing.
retailers/base.py         ← unchanged interface (extract_products_from_page stays the contract).
```

The only place that knows about Lidl is the adapter (and `parser.py` name-fallback helpers). `CardDetector`, `OcrService`, `ScreenshotService` are retailer-agnostic and could be called by any future `RetailerAdapter` subclass.

### 5.2 Data flow (extraction, one page)

```
page image (downloaded by adapter._attach_screenshots)
   │
   ▼
CardDetector.detect(image_path) → list[CardBox]            # grid first, contour fallback
   │
   ▼
OcrService.extract_lines(image_path) → list[OcrLine]       # existing
   │
   ▼
assign OcrLine → CardBox (line center inside box)
   │
   ▼
per card: name (topmost OCR line(s) / alt-text/keyword fallback) + price (regex within card lines)
   │
   ▼
ScreenshotService.crop(image, card_box, out_path) → one PNG per card
   │
   ▼
ExtractedProduct(retailer, leaflet_id, page, category, name, price_text, price_value, screenshot_path, raw_text, confidence)
```

### 5.3 Key interfaces (proposed)

```python
# src/leaflet_automation/services/cards.py
@dataclass
class CardBox:
    x: int; y: int; w: int; h: int
    @property
    def cx(self) -> float: ...  # center x
    @property
    def cy(self) -> float: ...  # center y

class CardDetector:
    def detect(self, image_path: Path) -> list[CardBox]:
        """Try grid (projection profile); fall back to OpenCV contours.
        Returns boxes sorted top→bottom, left→right."""

    def _grid_boxes(self, image_path: Path) -> list[CardBox]: ...   # PIL + numpy
    def _contour_boxes(self, image_path: Path) -> list[CardBox]: ... # cv2

def assign_lines_to_cards(lines: list[OcrLine], cards: list[CardBox]) -> list[list[OcrLine]]:
    """Returns, for each card, the OCR lines whose center falls in that card."""
```

## 6. Dependencies

- `Pillow` — already declared.
- `numpy` — already installed (transitive).
- `opencv-python` — ✅ declared `opencv-python>=4.8,<5` in `[project.dependencies]` (US-1.2 DONE, PR #3).
- `rapidocr-onnxruntime` — already declared.

No new external/AI services introduced.

## 7. Epics & User Stories

Stories follow the format: **US-X.Y: Title** — *Como <role>, quero <goal>, para <benefit>*. Each carries Priority, Effort, Dependencies, Acceptance Criteria, and Files.

---

### Epic 1: Retailer-Agnostic Product Card Detection

**Epic goal:** A generic service that, given a leaflet page image, returns one bounding box per product card — regardless of retailer.

**Epic business value:** Unlocks accurate per-product screenshots and per-card data extraction for any retailer, removing the duplicated per-company framing logic.

---

#### US-1.1: Projection-profile grid detector  ✅ DONE (PR #2)

As the engine, I want to detect the row/column grid of a leaflet page so that every product card gets its own bounding box.

- **Priority:** Must Have
- **Effort:** M
- **Dependencies:** None
- **Status:** Implemented in `src/leaflet_automation/services/cards.py` (`CardBox`, `CardDetector._grid_boxes`). Grid detection uses per-row/per-column dark-pixel energy profiles (PIL + numpy); whitespace gaps (below `GAP_RATIO=0.08` of max energy) become grid lines; cells = row-band × col-band Cartesian product, sorted top→bottom, left→right. Degenerate inputs (empty / solid-color) return `[]` via the `threshold <= 0` early return + the full-span 0.98 guard. Only `numpy` + `Pillow` used (no `cv2`). Covered by `tests/test_cards.py` (12 offline tests: CardBox centers, degenerate images, synthetic 2×2 grid, real `page-04.png` smoke). PR #2, branch `us-1-1-grid-detector`. **Not yet wired into the adapter** (that is US-3.1); see "US-1.1 grid-only limitation" under US-5.2.

**Requirements:**
- Implement a grid detector using projection profiles (per-row and per-column sum of dark-pixel energy) computed with PIL + numpy.
- Identify whitespace gaps as minima in the projection profile and use them as grid lines.
- Produce one `CardBox(x, y, w, h)` per detected cell.

**Acceptance Criteria:**
- Given a grid-style page image, `CardDetector._grid_boxes()` returns a list of non-overlapping `CardBox` covering >90 % of the printable product area.
- Boxes do not overlap.
- Boxes are sorted top→bottom, left→right.
- No new runtime dependency is introduced beyond PIL + numpy.
- The function does not crash on empty or solid-color images (returns an empty list).

**Files:**
- `src/leaflet_automation/services/cards.py` (new)

---

#### US-1.2: OpenCV contour fallback  ✅ DONE (PR #3)

As the engine, I want a contour-based fallback so that decorative/non-grid layouts still yield per-product boxes.

- **Priority:** Must Have
- **Effort:** M
- **Dependencies:** US-1.1
- **Status:** Implemented in `src/leaflet_automation/services/cards.py` (`CardDetector._contour_boxes`, `_iou`, `_nms`, contour tuning constants). Path: `cv2.imread` → adaptive threshold (`ADAPTIVE_THRESH_GAUSSIAN_C`) → morphological close (`MORPH_RECT` kernel) → `findContours(RETR_EXTERNAL)` → area/aspect filter (`MIN_AREA_RATIO`/`MAX_AREA_RATIO`/`MIN_ASPECT`/`MAX_ASPECT`) → greedy IoU NMS (`NMS_IOU=0.3`) → reuse existing `_sort_tb_lr`. Degenerate inputs (missing file → `imread` returns `None`, 1×1, solid-color, zero-area image) return `[]` without raising. Tuned constants against the real `page-04.png` fixture: `MORPH_KERNEL=21`, `ADAPTIVE_C=5` (within sanctioned plan ranges) — yields 3 pixel-disjoint boxes with 3 distinct x-columns on page-04, satisfying the distinct-column guard the US-1.1 grid-only path could not meet on the dense real produce page. `opencv-python>=4.8,<5` declared in `pyproject.toml`. Covered by `tests/test_cards.py` (10 new offline tests: 4 degenerate, 3 synthetic 3-rectangle, 3 real `page-04.png`). PR #3, branch `us-1-2-opencv-contour-fallback`. The unified `detect()` orchestration ("try grid, fall back to contours") is US-1.3 (not yet done). A large merged box (~694×627 px on page-04) is a known artifact within US-1.2 acceptance; per-card regression quality is deferred to US-5.2.

**Requirements:**
- Implement `_contour_boxes()` using `cv2` (adaptive threshold + findContours + area/aspect filtering).
- Declare `opencv-python` as a project dependency.

**Acceptance Criteria:**
- When grid detection returns fewer than 2 boxes (no clean grid), the fallback produces candidate boxes filtered by area and aspect ratio.
- Returned boxes are non-overlapping and sorted.
- `opencv-python>=4.8` appears in `pyproject.toml` `[project.dependencies]` and `python3 -m compileall src` succeeds.
- Fixture `demo_screenshots/.../page-04.png` yields ≥2 boxes via at least one of the two strategies.

**Files:**
- `src/leaflet_automation/services/cards.py`
- `pyproject.toml`

---

#### US-1.3: CardDetector unified interface

As an adapter, I want a single API `CardDetector.detect(image_path) -> list[CardBox]` so that any retailer can use it without knowing the implementation.

- **Priority:** Must Have
- **Effort:** S
- **Dependencies:** US-1.1, US-1.2

**Requirements:**
- `CardDetector.detect()` tries grid detection first, falls back to contours, returns the union of chosen boxes sorted top→bottom, left→right.
- Expose `CardBox` from the module.

**Acceptance Criteria:**
- Calling `detect()` never raises on a real Lidl page image; returns a deterministic, ordered list.
- A page with no detectable cards returns an empty list (not None).
- `CardBox` is importable from `leaflet_automation.services.cards`.

**Files:**
- `src/leaflet_automation/services/cards.py`

---

### Epic 2: OCR-to-Card Assignment & Per-Card Data Extraction

**Epic goal:** Given card boxes, assign OCR text to each card and extract name and price per card from only that card's text.

**Epic business value:** Stops prices from neighboring cards being matched to the wrong product (the silent correctness bug behind "we are not getting all the data").

---

#### US-2.1: OCR line → card assignment

As the engine, I want each OCR line assigned to the card whose box contains the line's center so that each card only sees its own text.

- **Priority:** Must Have
- **Effort:** S
- **Dependencies:** Epic 1

**Requirements:**
- Implement `assign_lines_to_cards(lines, cards)` that returns, for each card, the subset of `OcrLine` whose center lies inside the card's box.
- Lines whose center falls outside every card are discarded.

**Acceptance Criteria:**
- Each `OcrLine` is assigned to at most one card.
- Lines outside all cards are dropped (not silently attached to the nearest card).
- Return length equals `len(cards)`; ordering matches `cards`.

**Files:**
- `src/leaflet_automation/services/cards.py`

---

#### US-2.2: Per-card name extraction

As the engine, I want to derive the product name from the OCR lines of its own card so that identification no longer depends solely on alt-text/keywords.

- **Priority:** Should Have
- **Effort:** M
- **Dependencies:** US-2.1

**Requirements:**
- Per card, pick the name candidate from the topmost/largest OCR text line(s).
- Fall back to `extract_product_names_from_alt_text` / `extract_product_names_from_keywords` when the card has no usable OCR text.
- A card with no name candidate and no fallback is dropped (one card ⇄ one product).

**Acceptance Criteria:**
- Every returned `ExtractedProduct.name` is non-empty.
- When OCR text is available for a card, the name comes from that card's lines.
- When OCR text is missing, the name falls back to alt-text/keyword names matched by nearest-card position.
- A card with neither OCR name nor fallback name is skipped (no empty-name product inserted).

**Files:**
- `src/leaflet_automation/retailers/lidl/adapter.py`
- `src/leaflet_automation/retailers/lidl/parser.py` (read-only reuse)

---

#### US-2.3: Per-card price extraction

As the engine, I want `price_text`/`price_value` extracted only from the OCR lines of the same card so that the price belongs to the right product.

- **Priority:** Must Have
- **Effort:** M
- **Dependencies:** US-2.1

**Requirements:**
- Apply the existing `(?<!\d)(\d+[.,]\d{2})(?!\d)` regex **only** to the lines assigned to the card (no global line scan across the page).
- Pick the price line closest to the name line within the same card (reuse the existing `_match_price_line` proximity logic, scoped to the card).

**Acceptance Criteria:**
- A card with no price-pattern line leaves `price_text=None`, `price_value=None` (no crash, no cross-card fallback).
- A card with a clear price line sets `price_text` (comma decimal) and `price_value` (float).
- Regression: on `demo_screenshots/.../page-04.png`, each card's price matches the price printed on that card (manual spot-check on 4 cards asserts no neighbor bleed).

**Files:**
- `src/leaflet_automation/retailers/lidl/adapter.py` (`_match_price_line` refactor + `_attach_prices` per-card)

---

### Epic 3: Focused Product Screenshots

**Epic goal:** Replace equal-strip slicing with per-card crops so each screenshot contains exactly one product.

**Epic business value:** Restores trust in visual review of extraction; removes the bug that triggered this work.

---

#### US-3.1: Per-card screenshot crop

As an operator, I want the screenshot of each product to contain only that product so visual review is reliable.

- **Priority:** Must Have
- **Effort:** S
- **Dependencies:** Epic 1, US-2.1

**Requirements:**
- `_attach_screenshots` no longer calls `ImageService.detect_product_blocks(expected_blocks=len(products))` (the equal-strip path). It calls `CardDetector.detect(image_path)` and crops each CardBox.
- If the number of detected cards differs from the number of identified products, assignment is by sorted order (cards and products are both sorted top→bottom, left→right).

**Acceptance Criteria:**
- Each generated PNG corresponds to exactly one `CardBox` (no full-width strip).
- The `page-04` regression is fixed: the screenshot named `page-04-tomate-cacho.png` contains only the tomato card, not a full row.
- Screenshot paths remain under `data/<retailer>/<leaflet_id>/products/`.
- `python3 -m compileall src` succeeds.

**Files:**
- `src/leaflet_automation/retailers/lidl/adapter.py` (`_attach_screenshots`)
- `src/leaflet_automation/services/screenshots.py` (no API change; receives a `CardBox`)

---

#### US-3.2: Persist card box (optional)

As an operator, I want the card's box stored on the product record so later review knows where the product was on the page.

- **Priority:** Could Have
- **Effort:** S
- **Dependencies:** US-3.1

**Requirements:**
- Add a `card_box` column to the `products` table (format `"x,y,w,h"`; nullable).
- Add `card_box` to `ExtractedProduct` model and to `ProductRepository.insert_many`.

**Acceptance Criteria:**
- `initialize_schema` creates the `card_box` column on a fresh DB without error.
- Existing DBs are upgraded idempotently (add column if missing; SQLite `ALTER TABLE ADD COLUMN` guarded by a PRAGMA check).
- `card_box` is populated for products whose screenshot came from a detected card; `None` otherwise.

**Files:**
- `src/leaflet_automation/db/schema.py`
- `src/leaflet_automation/db/repositories/products.py`
- `src/leaflet_automation/core/models.py`

---

### Epic 4: Fix Product Identification Coverage

**Epic goal:** Stop silently dropping products the page actually shows.

**Epic business value:** Directly fixes the "we are not getting all the data" symptom — more products per page → more commercial coverage.

---

#### US-4.1: Keyword fallback runs in union with alt-text  ✅ DONE (PR #1)

As the engine, I want the keyword fallback to run even when alt-text already yields names so every visible product is identified.

- **Priority:** Must Have
- **Effort:** S
- **Dependencies:** None
- **Status:** Implemented in `src/leaflet_automation/retailers/lidl/adapter.py` (`extract_products_from_page`). The exclusive `if not alt_text_products:` gate is removed; both alt-text and keyword loops always run in union. Cross-source de-duplication is a shared `seen_names` set keyed on `name.strip().casefold()` (alt-text runs first, so it wins ties at confidence 0.8). Covered by `tests/test_us_4_1_keyword_union.py` (2/2 offline green). No integration-suite regression (14 offline-safe tests unchanged).

**Requirements:**
- Remove the exclusive branch at `adapter.py:76` (`if not alt_text_products:` → always run keyword extraction; merge results).
- De-duplicate merged names case-insensitively (existing `_unique_names` helper).

**Acceptance Criteria:**
- On `page-04`, the keyword-derived names (`cebola`, `pêssego`, `curgete`, `laranja`, ...) are no longer dropped when alt-text yields names.
- No duplicate names remain in the merged list (de-dup is case-insensitive).
- Existing tests in `tests/test_lidl_extraction_integration.py` do not regress (or are intentionally updated to reflect the higher count).

**Files:**
- `src/leaflet_automation/retailers/lidl/adapter.py`
- `src/leaflet_automation/retailers/lidl/parser.py`

---

#### US-4.2: Identification follows detected cards

As the engine, I want the number of extracted products to follow the number of detected cards (one product per identifiable card) so coverage matches what is visually on the page.

- **Priority:** Should Have
- **Effort:** M
- **Dependencies:** US-4.1, Epic 2

**Requirements:**
- After card detection + OCR assignment, the product list is built from cards that have a name (OCR or fallback).
- Cards with no name at all are dropped gracefully.

**Acceptance Criteria:**
- The number of products extracted from a page equals the number of cards with an identifiable name.
- Empty-name cards do not produce placeholder products.
- If card detection yields zero cards, extraction returns an empty list without raising.

**Files:**
- `src/leaflet_automation/retailers/lidl/adapter.py`

---

### Epic 5: Verification & Coverage

**Epic goal:** Protect the new flow with automated tests so it does not regress.

**Epic business value:** Lowers maintenance cost and makes future per-retailer work safer (aligns with Epic 4 of the existing IMPLEMENTATION_BACKLOG).

---

#### US-5.1: CardDetector unit tests

As a developer, I want unit tests for grid and contour detection so card detection is protected during changes.

- **Priority:** Must Have
- **Effort:** M
- **Dependencies:** Epic 1

**Requirements:**
- New test module `tests/test_cards.py` using `demo_screenshots/.../page-04.png` and a synthetic grid image.
- Asserts: non-empty card list, non-overlapping boxes, sorted order, ≥N boxes on page-04.

**Acceptance Criteria:**
- `python3 -m pytest tests/test_cards.py` passes (or the project's test runner if different).
- Test covers both `_grid_boxes` and `_contour_boxes` code paths.
- `python3 -m compileall tests` succeeds.

**Files:**
- `tests/test_cards.py` (new)

---

#### US-5.2: Extraction integration regression test

As a developer, I want an integration test that asserts the page-04 mistakes are fixed so the fix is protected from future regressions.

- **Priority:** Must Have
- **Effort:** M
- **Dependencies:** Epic 1, Epic 2, US-3.1, US-4.1

**Requirements:**
- Extend `tests/test_lidl_extraction_integration.py` (or add a focused `tests/test_page04_regression.py`) with assertions that encode the bug fix:
  - Number of products per page equals number of detected cards with a name.
  - Each saved screenshot's pixel dimensions are consistent with one CardBox (not a full-width strip of `width × height/N`).
  - Page-04 produces ≥ the number of products visible in keywords (i.e. keyword names not dropped).
  - **Fruit completeness:** every fruit card on the latest leaflet's produce pages (category `"frutas"`) is extracted — none dropped. Verified by cross-checking detected fruit cards against `CATEGORY_KEYWORDS["frutas"]` and asserting the extracted fruit product count equals the fruit-card count.
  - Prices assigned to products belong to the same card (mocked OCR lines per card).
  - **Page-04 distinct-column guard (deferred from US-1.1):** assert `len({box.x for box in CardDetector().detect(page-04)}) >= 2` (and `len({box.y ...}) >= 2`). This guard was prototyped during US-1.1 but is RED there because the grid-only `_grid_boxes` saturates on the dense real produce page (no full-height/full-width gutter → returns full-width strips; see "US-1.1 grid-only limitation" below). It becomes enforceable once the US-1.2 contour fallback (or a per-row-band column-profile improvement) makes the detector return ≥2 columns on page-04. **US-5.2 must assert ≥2 distinct columns on page-04** once `CardDetector.detect()` (US-1.3) is in place. Until then it lives only as the synthetic-grid guard `test_synthetic_grid_has_distinct_columns_not_full_width_strips`.

**US-1.1 grid-only limitation (recorded 2026-07-10):** the global projection-profile approach in `CardDetector._grid_boxes` detects clean grids where gutters span the full page (synthetic 2×2 grid → 4 cells). On dense real flyers like `page-04.png` (1415×2400, near full-bleed artwork), every column has >~1845/2400 dark pixels and every row >~113/1415, so the `GAP_RATIO=0.08` threshold admits zero gap rows/columns and the detector collapses to full-width strips (effectively one box ≈ the whole page). Real per-card grid detection on such pages is handled by the US-1.2 OpenCV contour fallback (✅ DONE, PR #3) and the US-5.2 per-card regression, NOT US-1.1. A future improvement (per-row-band column profiling / local-minima gap detection) is tracked for a later slice.

**Acceptance Criteria:**
- The regression test fails on the current (buggy) `detect_product_blocks` + exclusive branch and passes after the fix.
- `python3 -m compileall tests` succeeds.
- Tests run offline (use stored fixtures from `demo_screenshots/`, no live network calls).

**Files:**
- `tests/test_lidl_extraction_integration.py` (or `tests/test_page04_regression.py`)

## 8. Error Handling

- Card detection failures: `detect()` returns `[]`; extraction returns `[]` (no crash).
- OCR unavailable/empty: per-card name falls back to alt-text/keyword helpers; price stays `None`.
- Image download failure (existing): handled in `adapter._attach_screenshots`; if no image, screenshots are skipped (existing behavior preserved).
- Price regex no match: `price_text=None, price_value=None`; product still persisted without price.
- Schema migration (US-3.2): idempotent `ALTER TABLE` gated by PRAGMA `table_info` so existing DBs upgrade safely.

## 9. Testing

- Unit tests for `CardDetector` (grid path, contour path, assign_lines_to_cards).
- Regression test using the real `page-04.png` fixture (offline).
- Existing `tests/test_lidl_extraction_integration.py` and `tests/test_lidl_live_e2e.py` are not deleted; the integration test may be updated intentionally to reflect higher product counts post-fix.
- Verified run command for syntax: `python3 -m compileall src` and `python3 -m compileall tests`.
- The project has no tracked test runner config yet; if pytest is used, document the invocation.

## 10. Recommended Delivery Order

1. ~~**US-4.1** — keyword fallback union (cheap, immediate coverage win, isolated change).~~ ✅ DONE (PR #1)
2. **Epic 1** (~~US-1.1~~ ✅ DONE (PR #2) → ~~US-1.2~~ ✅ DONE (PR #3) → US-1.3) — card detection foundation.
3. **Epic 2** (US-2.1 → US-2.3 → US-2.2) — per-card data extraction.
4. **US-3.1** — per-card screenshots (the headline fix).
5. **US-3.2** — optional box persistence.
6. **Epic 5** — tests landed alongside each epic (US-5.1 after Epic 1; US-5.2 after Epic 3/4).
7. **US-4.2** — identification follows cards; final glue.

## 11. Out of Scope (tracked elsewhere)

- PDF-based extraction fallback (`IMPLEMENTATION_BACKLOG` "Not Implemented").
- External/proprietary AI/LLM vision services (explicitly rejected in brainstorming — local libs only).
- Wiring the generic extractor into non-Lidl retailers (no fixtures yet; future epic).
- Dynamic discovery improvements (Epic 4 of the existing backlog).
- **Completeness assertions for non-fruit categories** (vegetables "Legumes", cogumelos, etc.). The card-detection + OCR infrastructure supports them, but this slice's acceptance tests only assert completeness for the `"frutas"` category. Adding completeness coverage for other categories is a future slice once the fruit path is proven end-to-end.