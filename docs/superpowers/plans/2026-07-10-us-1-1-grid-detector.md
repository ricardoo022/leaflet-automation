# US-1.1 Projection-Profile Grid Detector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a retailer-agnostic grid detector (`CardDetector._grid_boxes`) that, given a leaflet page image, returns one non-overlapping, sorted `CardBox` per detected product-card cell using PIL + numpy projection profiles.

**Architecture:** A new module `src/leaflet_automation/services/cards.py` exposes a `CardBox` dataclass and a `CardDetector` class. Grid detection works by computing a per-row and per-column dark-pixel energy profile, finding whitespace-gap bands (low-energy runs), and taking the Cartesian product of the row-content spans and column-content spans to yield card cells. Cells are sorted top→bottom, left→right. Only PIL + numpy are used (no `cv2` — that arrives in US-1.2).

**Tech Stack:** Python 3.11, Pillow, numpy, stdlib `unittest`. Tests run via `.venv/bin/python -m unittest`. Syntax verified via `.venv/bin/python -m compileall src`.

## Global Constraints

- No new runtime dependency beyond `Pillow` + `numpy` (US-1.1 explicitly forbids new deps; `opencv-python` is US-1.2's job).
- Live fixture path: `demo_screenshots/data/lidl/019e6f22-4ece-7cf2-8ab3-6a958456e86a/pages/page-04.png` (1415×2400 RGB).
- Tests must run offline (no network).
- Follow TDD strictly: write the failing test, watch it fail, write minimal code, watch it pass.
- Use `.venv/bin/python` for ALL python invocations (system `python3` lacks PIL/numpy).
- Add no comments to production code unless asked.

## File Structure

- **Create:** `src/leaflet_automation/services/cards.py` — `CardBox` dataclass + `CardDetector` class (grid path only this slice).
- **Create:** `tests/test_cards.py` — unit tests using a synthetic grid image and the real `page-04.png` fixture.

No existing files are modified in this slice.

## Interfaces

**Produces (imported by later stories):**
```python
# src/leaflet_automation/services/cards.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CardBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float: ...   # x + w/2
    @property
    def cy(self) -> float: ...   # y + h/2

class CardDetector:
    def _grid_boxes(self, image_path: Path) -> list[CardBox]: ...
        # sorted top→bottom, left→right; non-overlapping; [] on degenerate input
```

**Consumes:** None (US-1.1 has no dependencies).

---

### Task 1: CardBox dataclass + module skeleton

**Files:**
- Create: `src/leaflet_automation/services/cards.py`
- Test: `tests/test_cards.py`

**Interfaces:**
- Produces: `CardBox(x, y, w, h)` with `cx`, `cy` properties.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cards.py
import unittest
from pathlib import Path

from leaflet_automation.services.cards import CardBox, CardDetector

FIXTURE_PAGE04 = (
    Path(__file__).resolve().parent.parent
    / "demo_screenshots"
    / "data"
    / "lidl"
    / "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
    / "pages"
    / "page-04.png"
)


class CardBoxTests(unittest.TestCase):
    def test_center_properties(self) -> None:
        box = CardBox(x=10, y=20, w=100, h=40)
        self.assertEqual(box.cx, 60.0)
        self.assertEqual(box.cy, 40.0)

    def test_fields_are_ints(self) -> None:
        box = CardBox(x=1, y=2, w=3, h=4)
        self.assertEqual((box.x, box.y, box.w, box.h), (1, 2, 3, 4))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'leaflet_automation.services.cards'` (or `ImportError`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/leaflet_automation/services/cards.py
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CardBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class CardDetector:
    def _grid_boxes(self, image_path: Path) -> list[CardBox]:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: PASS (2 tests; `_grid_boxes` is not exercised yet).

- [ ] **Step 5: Commit**

```bash
git add src/leaflet_automation/services/cards.py tests/test_cards.py
git commit -m "feat(cards): add CardBox dataclass + CardDetector skeleton (US-1.1)"
```

---

### Task 2: Degenerate-input safety — empty/solid-color images return []

**Files:**
- Modify: `src/leaflet_automation/services/cards.py` (`CardDetector._grid_boxes`)
- Test: `tests/test_cards.py`

**Interfaces:**
- Produces: `CardDetector._grid_boxes(image_path: Path) -> list[CardBox]` returning `[]` for empty / solid-color images and never raising.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cards.py` (inside the file, after `CardBoxTests`):

```python
import tempfile


def _make_solid_image(path: Path, size: tuple[int, int], fill: tuple[int, int, int]) -> None:
    from PIL import Image
    Image.new("RGB", size, fill).save(path)


class GridDetectorDegenerateTests(unittest.TestCase):
    def test_solid_white_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "white.png"
            _make_solid_image(p, (200, 200), (255, 255, 255))
            self.assertEqual(CardDetector()._grid_boxes(p), [])

    def test_solid_black_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "black.png"
            _make_solid_image(p, (200, 200), (0, 0, 0))
            self.assertEqual(CardDetector()._grid_boxes(p), [])

    def test_empty_image_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tiny.png"
            _make_solid_image(p, (1, 1), (255, 255, 255))
            result = CardDetector()._grid_boxes(p)
            self.assertIsInstance(result, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: 3 new tests FAIL with `NotImplementedError` from the skeleton.

- [ ] **Step 3: Write minimal implementation**

Replace the `NotImplementedError` body of `_grid_boxes` with a PIL+numpy load + a trivially-empty return that still routes the image through numpy so degenerate inputs are exercised:

```python
# src/leaflet_automation/services/cards.py
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class CardBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class CardDetector:
    def _grid_boxes(self, image_path: Path) -> list[CardBox]:
        with Image.open(image_path) as image:
            gray = image.convert("L")
        arr = np.asarray(gray)
        if arr.size == 0:
            return []
        row_bands = self._content_bands(arr.sum(axis=1), arr.shape[1])
        col_bands = self._content_bands(arr.sum(axis=0), arr.shape[0])
        if not row_bands or not col_bands:
            return []
        boxes: list[CardBox] = []
        for y0, y1 in row_bands:
            for x0, x1 in col_bands:
                boxes.append(CardBox(x=x0, y=y0, w=x1 - x0, h=y1 - y0))
        return self._sort_tb_lr(boxes)

    def _content_bands(self, profile: np.ndarray, span: int) -> list[tuple[int, int]]:
        if profile.size == 0:
            return []
        threshold = float(profile.max()) * 0.08
        bands: list[tuple[int, int]] = []
        in_content = False
        start = 0
        for i, value in enumerate(profile):
            content = bool(value >= threshold)
            if content and not in_content:
                in_content = True
                start = i
            elif not content and in_content:
                bands.append((start, i))
                in_content = False
        if in_content:
            bands.append((start, int(profile.size)))
        return bands

    @staticmethod
    def _sort_tb_lr(boxes: list[CardBox]) -> list[CardBox]:
        return sorted(boxes, key=lambda b: (b.y, b.x))
```

Notes for the implementer:
- Solid white → no dark pixels → all-energy `sum` for white `L` rows is high but uniform; the `threshold = max * 0.08` makes every row "content", producing one giant band spanning the whole axis → a single cell equal to the whole image, NOT `[]`. To make solid images return `[]`, guard against the trivial single-band case: when only one row band spans essentially the full height AND only one col band spans the full width, treat it as "no grid" and return `[]`. Add this guard below before building boxes.

Apply that guard by inserting before the box-building loop:

```python
        full_height = arr.shape[0]
        full_width = arr.shape[1]
        if (
            len(row_bands) == 1
            and row_bands[0][1] - row_bands[0][0] >= full_height * 0.98
            and len(col_bands) == 1
            and col_bands[0][1] - col_bands[0][0] >= full_width * 0.98
        ):
            return []
```

(Place this immediately after computing `row_bands`/`col_bands` and the `if not row_bands or not col_bands: return []` line.)

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: PASS (all 5 tests). Solid white/black → `[]`, tiny image → `[]`.

- [ ] **Step 5: Commit**

```bash
git add src/leaflet_automation/services/cards.py tests/test_cards.py
git commit -m "feat(cards): grid detector returns [] on degenerate input (US-1.1)"
```

---

### Task 3: Detect a 2×2 grid on a synthetic image

**Files:**
- Modify: `tests/test_cards.py` (add grid test)
- Modify: `src/leaflet_automation/services/cards.py` (rename `_content_bands` to a dark-energy form so a uniform white background yields true gaps; keep the band logic)

**Interfaces:**
- Produces: `_content_bands` robust against a uniform-bright background (uses dark-pixel energy, not raw channel sum).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cards.py`:

```python
def _make_grid_image(path: Path) -> None:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    card_w, card_h = 180, 180
    for row in range(2):
        for col in range(2):
            x0 = 10 + col * 200
            y0 = 10 + row * 200
            draw.rectangle(
                [x0, y0, x0 + card_w - 1, y0 + card_h - 1],
                fill=(30, 30, 30),
            )
    img.save(path)


class GridDetectorSyntheticTests(unittest.TestCase):
    def test_detects_four_cells_in_2x2_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        self.assertEqual(len(boxes), 4)
        xs = sorted({b.x for b in boxes})
        ys = sorted({b.y for b in boxes})
        self.assertEqual(len(xs), 2)
        self.assertEqual(len(ys), 2)

    def test_boxes_are_sorted_top_to_bottom_left_to_right(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))

    def test_boxes_do_not_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual((overlap_x, overlap_y), (0, 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards.GridDetectorSyntheticTests -v
```
Expected: FAIL — the dark rectangles sum to a low `L` value (30 ≈ dark), but the white background sums to a high value. With current `_content_bands` (threshold `max*0.08`), every white row is "content" (high sum) and dark rows are "gap" → only one band, or wrong bands. The tests assert 4 boxes → fail.

- [ ] **Step 3: Write minimal implementation**

Switch the projection from raw grayscale sum to **dark-pixel energy** (count of pixels darker than a brightness threshold). Rewrite `_grid_boxes` and `_content_bands`:

```python
# src/leaflet_automation/services/cards.py
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class CardBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class CardDetector:
    DARK_THRESHOLD = 200
    GAP_RATIO = 0.08

    def _grid_boxes(self, image_path: Path) -> list[CardBox]:
        with Image.open(image_path) as image:
            gray = image.convert("L")
        arr = np.asarray(gray)
        if arr.size == 0:
            return []

        dark = arr < self.DARK_THRESHOLD
        row_profile = dark.sum(axis=1).astype(np.float64)
        col_profile = dark.sum(axis=0).astype(np.float64)

        row_bands = self._content_bands(row_profile)
        col_bands = self._content_bands(col_profile)
        if not row_bands or not col_bands:
            return []

        full_height, full_width = arr.shape
        if (
            len(row_bands) == 1
            and row_bands[0][1] - row_bands[0][0] >= full_height * 0.98
            and len(col_bands) == 1
            and col_bands[0][1] - col_bands[0][0] >= full_width * 0.98
        ):
            return []

        boxes: list[CardBox] = []
        for y0, y1 in row_bands:
            for x0, x1 in col_bands:
                boxes.append(CardBox(x=int(x0), y=int(y0), w=int(x1 - x0), h=int(y1 - y0)))
        return self._sort_tb_lr(boxes)

    def _content_bands(self, profile: np.ndarray) -> list[tuple[int, int]]:
        if profile.size == 0:
            return []
        threshold = float(profile.max()) * self.GAP_RATIO
        if threshold <= 0:
            return []
        bands: list[tuple[int, int]] = []
        in_content = False
        start = 0
        for i, value in enumerate(profile):
            content = bool(value >= threshold)
            if content and not in_content:
                in_content = True
                start = i
            elif not content and in_content:
                bands.append((start, i))
                in_content = False
        if in_content:
            bands.append((start, int(profile.size)))
        return bands

    @staticmethod
    def _sort_tb_lr(boxes: list[CardBox]) -> list[CardBox]:
        return sorted(boxes, key=lambda b: (b.y, b.x))
```

Notes for the implementer:
- Synthetic grid: white background → `dark` is False there → `dark.sum` = 0 over background rows/cols → those positions are `0 < threshold` → gap. Dark card bodies (30 < 200) → `dark.sum` ≈ card width → above `max*0.08` → content band. Yields 2 row bands × 2 col bands = 4 cells. ✓
- Solid-white image → `profile.max() == 0` → `threshold <= 0` → `_content_bands` returns `[]` → `_grid_boxes` returns `[]`. ✓ (keep the `full_*` guard harmless.)
- Solid-black image → every pixel dark → one full-span band on each axis → caught by the `full_*` 0.98 guard → `[]`. ✓

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: PASS (8 tests: CardBox ×2, degenerate ×3, synthetic 2×2 grid ×3).

- [ ] **Step 5: Commit**

```bash
git add src/leaflet_automation/services/cards.py tests/test_cards.py
git commit -m "feat(cards): projection-profile grid detection on 2x2 synthetic grid (US-1.1)"
```

---

### Task 4: Real page-04 fixture smoke test (≥2 boxes, sorted, non-overlapping)

**Files:**
- Modify: `tests/test_cards.py` (add a fixture-using test guarded by file existence)

**Interfaces:**
- Produces: confidence that `_grid_boxes` runs on a real Lidl produce page without raising and yields a usable sorted, non-overlapping card list.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cards.py`:

```python
@unittest.skipUnless(FIXTURE_PAGE04.exists(), "page-04 fixture missing")
class GridDetectorPage04Tests(unittest.TestCase):
    def test_returns_at_least_two_boxes_on_page04(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        self.assertGreaterEqual(len(boxes), 2)

    def test_boxes_sorted_and_non_overlapping_on_page04(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual((overlap_x, overlap_y), (0, 0))

    def test_boxes_cover_large_share_of_page_area(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        from PIL import Image
        with Image.open(FIXTURE_PAGE04) as img:
            total = img.size[0] * img.size[1]
        covered = sum(b.w * b.h for b in boxes)
        self.assertGreater(covered / total, 0.40)
```

Note: the spec's >90 %-coverage criterion refers to "printable product area", which is unknown without ground-truth card masks; on the real page-04 the dark-energy approach will include some page chrome. The test asserts ≥40 % of total page area as a smoke floor (well above the single strip bug, well below unrealistic perfection). Tuning to the true >90 %-of-product-area is deferred to US-5.2's per-card regression.

- [ ] **Step 2: Run test to verify it fails OR passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards.GridDetectorPage04Tests -v
```
Expected outcome to watch for:
- If it PASSES: the implementation already handles the real fixture — keep the test as a regression guard and proceed (do NOT weaken the assertion; the implementation is the source of truth, not the test).
- If it FAILS (e.g. `assertGreaterEqual(len(boxes), 2)` returns 0 or 1): tune the detector. Most likely cause: real page has full-width header/footer bands of dark pixels that merge row bands, collapsing to ≤1 row band. Fix by lowering `GAP_RATIO` or adding a **min-gap-merge step** in `_content_bands`: after collecting bands, split any single band that spans more than, say, 45 % of the profile length by re-thresholding at a higher ratio, OR — simpler and minimal — set `GAP_RATIO = 0.02` so subtle whitespace rows still register as gaps. Make the smallest change that makes the test pass while keeping all prior tests green.

If a tuning change is needed, edit `src/leaflet_automation/services/cards.py` `GAP_RATIO` (and document nothing in code — no comments). Re-run until the page-04 test passes AND `tests.test_cards` is fully green.

- [ ] **Step 3: Run the whole test module to verify everything passes**

Run:
```bash
.venv/bin/python -m unittest tests.test_cards -v
```
Expected: PASS (all tests; 8 + 3 page-04 = 11).

- [ ] **Step 4: Run syntax check on src and tests**

Run:
```bash
.venv/bin/python -m compileall src
.venv/bin/python -m compileall tests
```
Expected: both succeed with no errors.

- [ ] **Step 5: Confirm no new dependency was added**

Run:
```bash
git diff --stat pyproject.toml
```
Expected: empty (US-1.1 must NOT touch `pyproject.toml`).

- [ ] **Step 6: Commit**

```bash
git add tests/test_cards.py src/leaflet_automation/services/cards.py
git commit -m "test(cards): real page-04 grid smoke test (US-1.1)"
```

---

### Task 5: Full-suite regression + final verification

**Files:**
- None modified.

- [ ] **Step 1: Run the entire offline test suite**

Run:
```bash
.venv/bin/python -m unittest discover -s tests -v 2>&1 | tail -40
```
Expected: all offline tests PASS (no regressions in `test_us_4_1_keyword_union`, `test_lidl_extraction_integration`). Live-e2e tests may be skipped/erroring unchanged — they are not part of this slice.

- [ ] **Step 2: Syntax check final**

Run:
```bash
.venv/bin/python -m compileall src
.venv/bin/python -m compileall tests
```
Expected: both succeed.

- [ ] **Step 3: Mark US-1.1 acceptance criteria**

Self-check against the spec's US-1.1 Acceptance Criteria:
- [x] Grid-style page → `_grid_boxes()` returns non-overlapping `CardBox` covering a large share of the product area (Task 4 smoke floor; full >90 %-of-product-area refined in US-5.2).
- [x] Boxes do not overlap (asserted in Task 3 + Task 4).
- [x] Boxes sorted top→bottom, left→right (`_sort_tb_lr`; asserted in Task 3 + Task 4).
- [x] No new runtime dependency beyond PIL + numpy (Task 4 Step 5).
- [x] Does not crash on empty / solid-color images, returns `[]` (Task 2 + Task 3 solid-black).

No commit in this task — it's a verification gate only.

---

## Self-Review

**1. Spec coverage (US-1.1 Requirements & Acceptance):**
- "grid detector using projection profiles (per-row and per-column sum of dark-pixel energy) computed with PIL + numpy" → Task 3 implementation uses `dark = arr < DARK_THRESHOLD` and `dark.sum(axis=1/0)` — exactly per-row/per-column dark-pixel energy via numpy. ✓
- "Identify whitespace gaps as minima in the projection profile and use them as grid lines" → `_content_bands` thresholds the profile; whitespace runs (below `max*GAP_RATIO`) are the gaps, and the content spans between them become the grid lines. ✓
- "Produce one `CardBox(x, y, w, h)` per detected cell" → Cartesian product of row × col content spans. ✓
- Acceptance: non-overlapping ✓ (Task 3), sorted ✓ (Task 3), no new dep beyond PIL+numpy ✓ (Task 4 Step 5), no crash on empty/solid-color → `[]` ✓ (Task 2 + Task 3). Spec's ">90 % of printable product area" is not ground-truthable without card masks; covered as a smoke floor in Task 4 with a note deferring the precise figure to US-5.2 — flagged explicitly.

**2. Placeholder scan:** no TBD / TODO / "add error handling" / vague steps. Every code step contains complete code or a single precise constant change (`GAP_RATIO`).

**3. Type consistency:** `CardBox(x, y, w, h)` + `cx`/`cy` defined in Task 1 and used identically in Tasks 3–4. `_grid_boxes(image_path: Path) -> list[CardBox]` signature stable across all tasks. `_content_bands` signature changes once (Task 2 → Task 3) within its own task; no later task depends on the Task-2 form.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-10-us-1-1-grid-detector.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?