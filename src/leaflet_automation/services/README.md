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

Only one service has real implemented behavior today:

- `classifier.py`
  - contains a simple keyword-based classifier
  - maps text to categories using the Lidl keyword lists

## What Is Still Stubbed

These modules are intentional placeholders and currently raise `NotImplementedError`:

- `ocr.py`
- `images.py`
- `pdf.py`
- `screenshots.py`

The stub comments point at likely future dependencies such as:

- `pytesseract`
- Pillow
- OpenCV
- PyMuPDF
- `pdfplumber`

None of those dependencies are wired into the project yet.

## Important Files

- `classifier.py`
  - simplest implemented service in the package
  - currently tied to the Lidl keyword taxonomy

- `ocr.py`
  - intended page text extraction service

- `images.py`
  - intended preprocessing and product-block detection service

- `pdf.py`
  - intended PDF page extraction service

- `screenshots.py`
  - intended crop helper for product screenshots

## How It Fits Into The Flow

Today, this package is mostly outside the executed runtime path.

Future extraction flow will likely depend on it heavily:

1. obtain page assets
2. preprocess page images
3. extract OCR text
4. detect product blocks
5. crop screenshots
6. build precise `ExtractedProduct` records

## Maintainer Notes

- Do not assume these services are production-ready; most of them are scaffolds only.
- The current dependency set in `pyproject.toml` does not include the OCR/PDF/image libraries mentioned in stub comments.
- Although this package is meant to be shared infrastructure, the current classifier logic is retailer-specific because it reuses Lidl keyword lists.
