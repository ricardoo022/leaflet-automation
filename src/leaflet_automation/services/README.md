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

## What Is Still Stubbed

Only `pdf.py` remains a placeholder — PDF extraction is not implemented yet.

## Important Files

- `classifier.py` — `ProductClassifier.classify()` + `normalize_text()`
- `ocr.py` — `OcrLine` (text + bbox + score), `OcrService` (RapidOCR; `extract_lines`, `extract_text`)
- `images.py` — `ImageService.detect_product_blocks()` (equal-strip heuristic, being replaced), `preprocess_for_ocr()` (pass-through)
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

- `ocr.py`, `images.py`, and `screenshots.py` are implemented and on the runtime path. Only `pdf.py` is a stub.
- Declared deps in `pyproject.toml`: `Pillow`, `rapidocr-onnxruntime`. `opencv-python` and `numpy` are installed in the venv but not declared yet — declare `opencv-python>=4.8` when the card-detection work lands.
- `ImageService.detect_product_blocks()` is a known-weak equal-strip heuristic; the card-extraction design spec replaces it with a `CardDetector` in a new `cards.py`.
- Although this package is meant to be shared infrastructure, the classifier logic is retailer-specific because it reuses Lidl keyword lists.
