# `retailers`

## Purpose

This package defines the retailer adapter abstraction and holds retailer-specific implementations.

Right now the codebase is architected for multiple retailers in the future, but only Lidl is implemented.

## What Currently Works

- generic retailer adapter interface exists in `base.py`
- Lidl API client works
- Lidl discovery works from the folhetos landing page with seed fallback and related-flyer traversal
- Lidl payload parsing works
- Lidl program-type inference works
- Lidl date-based filtering works
- Lidl candidate page filtering works
- Lidl extraction builds products, screenshots, and OCR-assisted prices

## Package Structure

- `base.py`
  - abstract contract for retailer behavior

- `lidl/`
  - concrete Lidl implementation
  - current center of gravity for the working business logic

## Lidl Subpackage Responsibilities

Important Lidl files:

- `lidl/api.py`
  - HTTP client for Lidl leaflet endpoints
  - basic date parsing helper

- `lidl/discovery.py`
  - starts from the public folhetos landing page
  - falls back to verified `SEED_FLYER_IDS` when needed
  - expands discovery using `relatedFlyers`
  - deduplicates results

- `lidl/parser.py`
  - turns raw API payloads into internal models
  - captures page image URLs and text hints

- `lidl/filters.py`
  - infers `ProgramType`
  - filters current/upcoming target leaflets
  - identifies candidate pages using page text metadata

- `lidl/keywords.py`
  - keyword taxonomy used for produce-oriented page matching and classification

- `lidl/adapter.py`
  - concrete adapter composition point
  - exposes the discovery/filter/page-selection interface used by jobs
  - performs heuristic extraction, OCR-assisted price matching, and screenshot generation

## How It Fits Into The Flow

Most business-specific logic lives here.

Discovery path today:

1. adapter creates API client
2. discovery expands from landing-page IDs or seed leaflets
3. parser builds internal models
4. filters select relevant leaflets and pages

## Maintainer Notes

- Discovery is more robust than before, but still depends on Lidl keeping the landing page markup stable.
- Candidate page selection is based on substring matching in `altText` and `keyWords`, so false positives and false negatives are expected.
- `LidlAdapter.discover_leaflets(today)` accepts `today` for interface consistency, but the current implementation does not use that parameter directly.
- Read `docs/LIDL_LEAFLETS_API_RESEARCH.md` before changing API or discovery behavior.
