# US-4.1 Keyword Fallback Union Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Lidl keyword-name fallback run in union with alt-text names (instead of only when alt-text yields nothing) and de-duplicate the merged names case-insensitively, so every visible product is identified.

**Architecture:** `LidlAdapter.extract_products_from_page` currently gates keyword extraction behind `if not alt_text_products:`. We remove that exclusive gate so both alt-text (confidence 0.8) and keyword (confidence 0.55) products are produced, then add a case-insensitive `seen` set so a keyword name equal (case-folded) to an already-added alt-text name is skipped — keeping the higher-confidence alt-text record. No network is needed: tests construct pages with `image_url=None`/`zoom_url=None` so `_attach_screenshots` returns early and the identification logic is exercised offline.

**Tech Stack:** Python 3.11 (`.venv`), unittest, existing `leaflet_automation.retailers.lidl` parser/classifier. Run syntax check with `python3 -m compileall src tests` (use `.venv/bin/python`).

---

## Reference facts (verified offline, do not re-derive)

- Fixture `tests/fixtures/lidl/019e6f22-4ece-7cf2-8ab3-6a958456e86a.json` page index 1 (page‑04, produce):
  - `extract_product_names_from_alt_text` → `["tomate cacho", "mirtilos", "maçã Golden", "couve coração"]`. The first three classify; `"couve coração"` is kept only because `produce_context` is `True` and gets `page_category` (`"frutas"`). So alt-text path yields **4** products.
  - `extract_product_names_from_keywords` → 8 names, **all** classify (`"Mesmo Tomate Cacho"`, `"Tomate Cacho Nacional Mirtilo"`, `"Mirtilo Mini Maçã Golden"`, `"Maçã Golden Couve Coração"`, `"Golden Couve Coração Cebola"`, `"Couve Coração Cebola Pêssego"`, `"Coração Cebola Pêssego Curgete"`, `"Curgete Laranja Sumo"`). None case-folds to an alt-text name.
  - Fixed logic result: **12** products (4 alt + 8 keyword), **no** case-insensitive duplicates.
- Synthetic dedup fixture: `alt_text="com destaque para tomate cacho"`, `keywords="stock Tomate Cacho Nºb"`.
  - alt → `["tomate cacho"]` (classify `legumes`); kw → `["Tomate Cacho"]` (classify `legumes`, case-fold equal to alt).
  - Gate removed, NO dedup → 2 products (duplicate) → RED for dedup test.
  - Dedup added → 1 product `"tomate cacho"` at confidence `0.8` (alt-text precedence) → GREEN.
- Baseline unittest run (`tests.test_lidl_extraction_integration`): 14 `ok`, 3 FAIL (live discovery returns 0 target leaflets today), 5 ERROR (CDN image download 404 — expired). The 8 FAIL/ERROR tests are live-network tests, **not** an offline regression gate. The change must keep the 14 offline-green tests green and introduce no new failures among the offline-green set.

---

## File Structure

- **Create:** `tests/test_us_4_1_keyword_union.py` — offline unittests for the union + dedup behavior of `LidlAdapter.extract_products_from_page`.
- **Modify:** `src/leaflet_automation/retailers/lidl/adapter.py:44-99` — `extract_products_from_page`: remove the exclusive gate, add case-insensitive de-dup.

No other files change for US-4.1. `parser.py` is read-only reuse.

---

## Task 1: Keyword fallback runs in union with alt-text (RED → GREEN)

**Files:**
- Create: `tests/test_us_4_1_keyword_union.py`
- Modify: `src/leaflet_automation/retailers/lidl/adapter.py:44-99`

- [ ] **Step 1: Write the failing test**

Create `tests/test_us_4_1_keyword_union.py`:

```python
import json
import unittest
from datetime import date
from pathlib import Path

from leaflet_automation.core.enums import ProgramType
from leaflet_automation.core.models import Leaflet, LeafletPage
from leaflet_automation.retailers.lidl.adapter import LidlAdapter
from leaflet_automation.retailers.lidl.parser import (
    extract_product_names_from_keywords,
    parse_leaflet,
)
from leaflet_automation.services.classifier import ProductClassifier

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lidl"
PRODUCE_LEAFLET_ID = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"


def _load_leaflet(leaflet_id: str) -> Leaflet:
    payload = json.loads((FIXTURE_DIR / f"{leaflet_id}.json").read_text(encoding="utf-8"))
    return parse_leaflet(payload)


class KeywordFallbackUnionTests(unittest.TestCase):
    def test_keyword_names_not_dropped_when_alt_text_yields_names(self) -> None:
        leaflet = _load_leaflet(PRODUCE_LEAFLET_ID)
        page = leaflet.pages[1]  # page-04 (produce)
        page.image_url = None
        page.zoom_url = None

        adapter = LidlAdapter()
        try:
            products = adapter.extract_products_from_page(leaflet, page)
        finally:
            adapter.close()

        classified_keyword_names = [
            name
            for name in extract_product_names_from_keywords(page.keywords)
            if ProductClassifier().classify(name) is not None
        ]
        keyword_origin = [product for product in products if product.confidence == 0.55]

        self.assertGreater(len(keyword_origin), 0)
        self.assertEqual([p.name for p in keyword_origin], classified_keyword_names)

        names = [p.name.casefold() for p in products]
        self.assertEqual(len(names), len(set(names)))

        alt_origin = [p.name.casefold() for p in products if p.confidence == 0.8]
        for alt_name in ("tomate cacho", "mirtilos", "maçã golden", "couve coração"):
            self.assertIn(alt_name, alt_origin)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
.venv/bin/python -m unittest tests.test_us_4_1_keyword_union.KeywordFallbackUnionTests.test_keyword_names_not_dropped_when_alt_text_yields_names -v
```
Expected: **FAIL** — `len(keyword_origin)` is `0` because the current code skips the keyword loop whenever alt-text yields products (`if not alt_text_products:` at `adapter.py:76`). Assertion `assertGreater(len(keyword_origin), 0)` fails.

- [ ] **Step 3: Write minimal implementation (remove the exclusive gate)**

Replace the body of `extract_products_from_page` in `src/leaflet_automation/retailers/lidl/adapter.py` (lines 44–99) with the gate-removed version below. This is the **minimal** change to pass the test — **no dedup yet** (that is Task 2):

```python
    def extract_products_from_page(self, leaflet: Leaflet, page: LeafletPage) -> list[ExtractedProduct]:
        page_text = " ".join(part for part in [page.alt_text, page.keywords] if part)
        page_category = self.classifier.classify(page_text)
        produce_context = any(
            marker in normalize_text(page.alt_text or "")
            for marker in ("frutas", "fruta", "legumes", "frescos")
        )
        products: list[ExtractedProduct] = []

        for name in extract_product_names_from_alt_text(page.alt_text):
            category = self.classifier.classify(name)
            if category is None and produce_context:
                category = page_category
            if category is None:
                continue
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.alt_text or "",
                    confidence=0.8,
                )
            )

        for name in extract_product_names_from_keywords(page.keywords):
            category = self.classifier.classify(name)
            if category is None:
                continue
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.keywords or "",
                    confidence=0.55,
                )
            )

        if products:
            self._attach_screenshots(leaflet, page, products)

        return products
```

(The `alt_text_products` local and the `if not alt_text_products:` branch are gone; both loops now always run.)

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_us_4_1_keyword_union.KeywordFallbackUnionTests.test_keyword_names_not_dropped_when_alt_text_yields_names -v
```
Expected: **PASS** — `keyword_origin` has 8 names equal to `classified_keyword_names`; alt-text names still present; no case-insensitive duplicates (the real page‑04 keyword names differ from alt-text names).

- [ ] **Step 5: Compile-check and commit**

Run:
```bash
.venv/bin/python -m compileall src tests
```
Expected: no errors.

```bash
git add tests/test_us_4_1_keyword_union.py src/leaflet_automation/retailers/lidl/adapter.py
git commit -m "feat(lidl): run keyword name fallback in union with alt-text (US-4.1)"
```

---

## Task 2: De-duplicate merged names case-insensitively (RED → GREEN)

**Files:**
- Modify: `tests/test_us_4_1_keyword_union.py` (add test)
- Modify: `src/leaflet_automation/retailers/lidl/adapter.py:44-99`

- [ ] **Step 1: Write the failing test**

Append this test method to the `KeywordFallbackUnionTests` class in `tests/test_us_4_1_keyword_union.py` (the imports `Leaflet`, `LeafletPage`, `ProgramType`, `date` are already at the top of the file from Task 1):

```python
    def test_merged_keyword_name_deduplicated_case_insensitively_with_alt_text_precedence(self) -> None:
        leaflet = Leaflet(
            id="L",
            retailer="lidl",
            name="",
            title="",
            url="",
            program_type=ProgramType.WEEKLY,
            offer_start_date=date(2026, 6, 1),
            offer_end_date=date(2026, 6, 7),
        )
        page = LeafletPage(
            leaflet_id="L",
            page_number=4,
            alt_text="com destaque para tomate cacho",
            keywords="stock Tomate Cacho Nºb",
        )

        adapter = LidlAdapter()
        try:
            products = adapter.extract_products_from_page(leaflet, page)
        finally:
            adapter.close()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name.lower(), "tomate cacho")
        self.assertEqual(products[0].confidence, 0.8)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
.venv/bin/python -m unittest tests.test_us_4_1_keyword_union.KeywordFallbackUnionTests.test_merged_keyword_name_deduplicated_case_insensitively_with_alt_text_precedence -v
```
Expected: **FAIL** — Task 1 removed the gate but added no de-dup, so the keyword name `"Tomate Cacho"` (case-fold equal to alt-text `"tomate cacho"`) is added on top of the alt-text product → `len(products) == 2`, assertion `assertEqual(len(products), 1)` fails.

- [ ] **Step 3: Write minimal implementation (case-insensitive de-dup)**

Replace the body of `extract_products_from_page` in `src/leaflet_automation/retailers/lidl/adapter.py` with the de-duplicating version below (adds a `seen_names` set; alt-text runs first so it wins ties by higher confidence):

```python
    def extract_products_from_page(self, leaflet: Leaflet, page: LeafletPage) -> list[ExtractedProduct]:
        page_text = " ".join(part for part in [page.alt_text, page.keywords] if part)
        page_category = self.classifier.classify(page_text)
        produce_context = any(
            marker in normalize_text(page.alt_text or "")
            for marker in ("frutas", "fruta", "legumes", "frescos")
        )
        products: list[ExtractedProduct] = []
        seen_names: set[str] = set()

        for name in extract_product_names_from_alt_text(page.alt_text):
            key = name.strip().casefold()
            if not name or key in seen_names:
                continue
            category = self.classifier.classify(name)
            if category is None and produce_context:
                category = page_category
            if category is None:
                continue
            seen_names.add(key)
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.alt_text or "",
                    confidence=0.8,
                )
            )

        for name in extract_product_names_from_keywords(page.keywords):
            key = name.strip().casefold()
            if not name or key in seen_names:
                continue
            category = self.classifier.classify(name)
            if category is None:
                continue
            seen_names.add(key)
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.keywords or "",
                    confidence=0.55,
                )
            )

        if products:
            self._attach_screenshots(leaflet, page, products)

        return products
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_us_4_1_keyword_union -v
```
Expected: **PASS** for both tests. The synthetic page yields exactly 1 product, `"tomate cacho"` at confidence `0.8`; the real page‑04 union test still yields 12 products with no duplicates.

- [ ] **Step 5: Compile-check and commit**

Run:
```bash
.venv/bin/python -m compileall src tests
```
Expected: no errors.

```bash
git add tests/test_us_4_1_keyword_union.py src/leaflet_automation/retailers/lidl/adapter.py
git commit -m "feat(lidl): de-duplicate merged alt-text/keyword names case-insensitively (US-4.1)"
```

---

## Task 3: Verify no offline regression in the integration suite

**Files:** none modified (verification only).

- [ ] **Step 1: Run the offline-safe integration tests**

Run:
```bash
.venv/bin/python -m unittest tests.test_lidl_extraction_integration -v 2>&1 | grep -E '^(ok|FAIL|ERROR)'
```
Expected: the same 14 `ok` lines as the baseline (see Reference facts). The 3 FAIL (live discovery) and 5 ERROR (CDN image 404) are pre-existing network-dependent failures and must remain the **same** set — no new `ok` test turns into `FAIL`/`ERROR`. In particular these must stay `ok`:
- `test_extract_product_names_from_real_alt_text_produce_page`
- `test_extract_product_names_from_real_keywords_fallback_text`
- `test_parse_real_fixture_preserves_candidate_pages`
- `test_parse_real_leaflet_preserves_page_numbers_and_media_urls`
- `test_parse_real_weekly_leaflet_maps_core_metadata_and_dates`
- `test_is_candidate_page_matches_real_produce_page_and_skips_non_target_page`
- `test_filter_target_leaflets_excludes_expired_real_fixture_for_reference_date`
- `test_infer_program_type_from_real_weekly_payload`
- `test_leaflet_repository_upsert_and_get_by_id_round_trip_real_leaflet`
- `test_run_lidl_discovery_persists_only_target_leaflets_to_real_sqlite`
- `test_run_lidl_extraction_raises_lookup_error_for_unknown_leaflet_id`
- `test_discover_leaflets_follows_real_related_flyers_and_dedupes`
- `test_run_weekly_lidl_returns_target_count_from_real_fixtures`
- `test_cli_extract_lidl_missing_leaflet_exits_1_with_lookup_message`

- [ ] **Step 2: Final compile check**

Run:
```bash
.venv/bin/python -m compileall src tests
```
Expected: no errors.

- [ ] **Step 3: Confirm US-4.1 acceptance criteria**

Verify by inspection against the spec:
- ✅ The exclusive branch at `adapter.py:76` is gone — keyword extraction always runs.
- ✅ Merged names are de-duplicated case-insensitively (`seen_names` using `casefold()`).
- ✅ On page‑04 the keyword-derived names (`cebola`, `pêssego`, `curgete`, `laranja`, … inside the keyword-name strings) are no longer dropped when alt-text yields names (8 keyword-origin products now present).
- ✅ Existing offline integration tests do not regress (14 still green).

**Notes for the executing engineer:**
- The live-network tests that assert an exact `persisted=9` (`test_cli_extract_lidl_prints_counts_and_persists_products`) and the page‑04 price spot-check (`test_adapter_extract_products_from_real_candidate_page_attaches_categories_dates_and_screenshots`) currently **ERROR** because the Lidl CDN image URLs in the fixtures have expired (HTTP 404) — they were already failing before this change. The exact post-fix persisted product count is not computable offline (it requires the images to download and OCR to run). Recalibrating these exact live-network counts to the higher post-fix value is deferred to **US-5.2**, which builds offline regression fixtures (stored `demo_screenshots/.../page-04.png`) and asserts the page‑04 bug fixes (including the higher product count). Do **not** edit those tests in US-4.1 — they are out of scope and are not part of the offline regression gate.