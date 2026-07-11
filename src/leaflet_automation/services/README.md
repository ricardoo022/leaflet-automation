# `services`

## Purpose

This package is the planned implementation surface for the missing extraction pipeline.

It is intended to hold shared helper services such as:

- OCR
- image preprocessing
- PDF page extraction
- screenshot cropping
- text/category classification

## What Currently Works

- `classifier.py`
  - contains a simple keyword-based classifier
  - maps text to categories using the Lidl keyword lists (`ProductClassifier.classify`)

- `ocr.py`
  - real OCR via `rapidocr-onnxruntime` (local, no cloud)
  - `OcrService.extract_lines()` returns `OcrLine` objects with text + bounding box + score
  - `OcrService.extract_text()` returns a joined string (used in tests)

- `images.py`
  - `ImageService.detect_product_blocks()` slices a page into N equal vertical strips (heuristic; being replaced by card detection — see note below)
  - `ImageService.preprocess_for_ocr()` is a pass-through stub returning the same path

- `screenshots.py`
  - `ScreenshotService.crop()` crops an image box to a PNG file (PIL)

- `cards.py` (US-1.1 grid detector ✅ DONE + US-1.2 contour fallback ✅ DONE; not yet wired into the adapter)
  - `CardBox` dataclass (`x, y, w, h` + `cx`/`cy` center properties)
  - `CardDetector._grid_boxes(image_path)` (US-1.1) detects a page grid via per-row/per-column dark-pixel energy profiles (PIL + numpy); whitespace gaps (below `GAP_RATIO=0.08` of max) become grid lines; cells = row-band × col-band product, sorted top→bottom, left→right
  - `CardDetector._contour_boxes(image_path)` (US-1.2, PR #3) is the OpenCV fallback: `cv2.imread` → adaptive threshold (`ADAPTIVE_THRESH_GAUSSIAN_C`) → morphological close (`MORPH_RECT` kernel `21`) → `findContours(RETR_EXTERNAL)` → area/aspect filter → greedy IoU NMS (`NMS_IOU=0.3`) → reuse `_sort_tb_lr`. Tuned constants `MORPH_KERNEL=21`, `ADAPTIVE_C=5` yield 3 pixel-disjoint boxes with 3 distinct x-columns on the real `page-04.png` fixture (the distinct-column guard the grid-only path could not satisfy on dense real produce pages)
  - `_iou(a, b)` / `_nms(boxes)` private helpers support the contour path's overlap removal
  - degenerate inputs (empty / solid-color / missing file / 1×1) return `[]` without raising
  - `numpy` + `Pillow` used by the grid path; `cv2` (opencv-python, now declared in `pyproject.toml` as `>=4.8,<5`) used by the contour path
  - covered by `tests/test_cards.py` (22 offline tests: 12 grid + 10 contour)
  - **not yet the adapter's source of boxes:** wiring into `_attach_screenshots` is US-3.1; the unified `CardDetector.detect()` orchestrator ("try grid, fall back to contours") is US-1.3 (pending); per-card regression quality on dense real pages is US-5.2

## What Is Still Stubbed

Only `pdf.py` remains a placeholder — PDF extraction is not implemented yet.

## Important Files

- `classifier.py` — `ProductClassifier.classify()` + `normalize_text()`
- `ocr.py` — `OcrLine` (text + bbox + score), `OcrService` (RapidOCR; `extract_lines`, `extract_text`)
- `images.py` — `ImageService.detect_product_blocks()` (equal-strip heuristic, being replaced), `preprocess_for_ocr()` (pass-through)
- `cards.py` — `CardBox` + `CardDetector._grid_boxes()` (US-1.1 grid detector) + `CardDetector._contour_boxes()` / `_iou()` / `_nms()` (US-1.2 contour fallback, PR #3)
- `pdf.py` — PDF extraction, still a stub
- `screenshots.py` — `ScreenshotService.crop()` PIL crop to disk

## How It Fits Into The Flow

This package is on the extraction runtime path today. `LidlAdapter._attach_screenshots()` calls `OcrService` → `ImageService.detect_product_blocks()` → `ScreenshotService.crop()` to attach prices and screenshots to each `ExtractedProduct`.

Planned flow (per the card-extraction design spec at `docs/superpowers/specs/...`):

1. obtain page assets
2. detect product cards (new `services/cards.py`, retailer-agnostic)
3. extract OCR text per card
4. assign OCR lines to cards
5. crop one screenshot per card
6. build precise `ExtractedProduct` records

## Maintainer Notes

- `ocr.py`, `images.py`, and `screenshots.py` are implemented and on the runtime path. `cards.py` (US-1.1 grid detector + US-1.2 contour fallback ✅ DONE, PR #3) is implemented and unit-tested but NOT yet called by the adapter (wiring is US-3.1); the unified `CardDetector.detect()` orchestrator is US-1.3 (pending). Only `pdf.py` is a stub.
- Declared deps in `pyproject.toml`: `Pillow`, `rapidocr-onnxruntime`, `opencv-python>=4.8,<5` (US-1.2). `numpy` is installed transitively and used by `cards.py` (grid + contour paths) but is not declared explicitly yet.
- `ImageService.detect_product_blocks()` is a known-weak equal-strip heuristic; the card-extraction design spec replaces it with `CardDetector` in `cards.py` (US-1.1 grid + US-1.2 contour implemented; wiring pending US-3.1).
- Although this package is meant to be shared infrastructure, the classifier logic is retailer-specific because it reuses Lidl keyword lists.
