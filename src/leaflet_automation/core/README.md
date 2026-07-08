# `core`

## Purpose

This package contains shared domain models and helper logic used across discovery, filtering, persistence, and future extraction.

If a concept is not specific to one retailer or one job, it usually belongs here.

## What Currently Works

- shared enums for program type and run status
- Pydantic models for leaflets, pages, products, and runs
- date-based filtering helper logic
- simple dedupe helpers for leaflets and products
- storage path helpers for leaflets and product screenshots

## Important Files

- `enums.py`
  - defines `ProgramType`
  - defines `RunStatus`

- `models.py`
  - `LeafletPage`: page metadata including URLs and text hints
  - `Leaflet`: leaflet metadata and in-memory pages
  - `ExtractedProduct`: target extraction output model
  - `RunRecord`: future run-tracking model

- `dates.py`
  - date helper logic used when selecting relevant leaflets

- `dedupe.py`
  - deduplicates leaflets by ID
  - deduplicates products using a simple composite key

- `storage.py`
  - ensures directories exist
  - computes filesystem paths for leaflet and product assets

## How It Fits Into The Flow

This package is the shared contract layer:

- Lidl parsing creates `Leaflet` and `LeafletPage`
- filtering updates `Leaflet.program_type`
- repositories consume `Leaflet` and `ExtractedProduct`
- future extraction will rely on `ExtractedProduct` and storage helpers more heavily

## Maintainer Notes

- `Leaflet.pages` is important in memory, but those pages are not currently persisted in SQLite.
- `ExtractedProduct` is defined ahead of the full implemented extraction flow.
- `RunRecord` exists as a model, but run tracking is not wired into persistence or orchestration yet.
- `dedupe_products()` is intentionally simple and can silently overwrite earlier products when keys collide.
- `product_screenshot_path()` derives names from product text, so filename collisions are possible.
