# Leaflet Automation Product Backlog

## Purpose

This backlog is organized using a standard software engineering structure:

- Epics: large outcome-oriented initiatives
- Features: deliverable capabilities within an epic
- User stories: small implementation slices with acceptance criteria

It also distinguishes between what already exists and what still needs to be built.

## Current Solution Status

### Implemented

- Lidl leaflet discovery CLI exists
- Weekly Lidl discovery job exists
- Lidl public API integration exists
- Lidl landing-page based discovery exists with seed fallback
- Leaflet and page parsing exists
- Date and program-type filtering exists
- Candidate page filtering by `altText` and `keyWords` exists
- SQLite persistence for discovered leaflets exists
- Real `extract-lidl` CLI behavior exists
- Leaflet lookup by ID for extraction exists
- Lidl page-to-product extraction logic exists
- End-to-end product persistence flow exists
- OCR, image, and screenshot processing exist
- Leaflet page snapshots are persisted in SQLite
- Product model, schema, repository, and dedupe scaffolding exist
- Automated integration and live E2E tests exist

### Not Implemented

- PDF-based extraction fallback
- Stronger exact product and price extraction across more leaflet layouts
- Richer product-block detection than vertical page slicing — the grid detector (`services/cards.py`, US-1.1) is implemented but not wired into the adapter (US-3.1) and saturates to full-width strips on dense real pages; the OpenCV contour fallback (US-1.2) and per-card regression (US-5.2) are still pending
- Broader automated coverage and CI wiring

## Epic 1: Deliver a Usable Lidl Extraction Workflow

### Goal

Allow an operator to extract product records from a discovered Lidl leaflet through the CLI and persist the results.

### Business Value

This turns the current discovery-only solution into a usable extraction pipeline.

### Features

#### Feature 1.1: Extraction command execution

User story 1.1.1

As an operator, I want `leaflets extract-lidl <leaflet-id>` to run a real extraction flow so that I can process one discovered leaflet on demand.

Acceptance criteria:
- The command accepts a leaflet ID
- The command loads the requested leaflet
- The command executes extraction for candidate pages
- The command prints a summary of extracted results

User story 1.1.2

As an operator, I want a clean error when a leaflet ID is unknown so that I understand why extraction did not run.

Acceptance criteria:
- Unknown leaflet IDs return a clear error message
- The command exits without crashing

#### Feature 1.2: Leaflet lookup from persistence

User story 1.2.1

As the system, I want to retrieve a previously discovered leaflet by ID so that extraction can use persisted data instead of requiring a fresh discovery run.

Acceptance criteria:
- A repository method can fetch a leaflet by ID
- The loaded leaflet includes all fields required for extraction
- Missing records return a clean empty result

#### Feature 1.3: Product persistence orchestration

User story 1.3.1

As the system, I want extracted products to be saved automatically so that extraction results are stored for later use.

Acceptance criteria:
- Extracted products are inserted into the `products` table
- Empty product lists are handled safely
- Duplicate products are reduced using the existing dedupe logic before insert

## Epic 2: Implement Minimal Product Extraction

### Goal

Extract an initial useful set of product records from Lidl candidate pages using currently available metadata before introducing OCR.

### Business Value

This delivers a working vertical slice quickly and validates the extraction pipeline with minimal complexity.

### Features

#### Feature 2.1: Metadata-based extraction

User story 2.1.1

As the system, I want `LidlAdapter.extract_products_from_page()` to return `ExtractedProduct` objects so that the extraction pipeline can complete without raising `NotImplementedError`.

Acceptance criteria:
- The method no longer raises `NotImplementedError`
- The method returns a list of `ExtractedProduct`
- The extraction uses existing page metadata first

User story 2.1.2

As the system, I want extracted products to include core business fields so that downstream persistence and review are possible.

Acceptance criteria:
- Each product has retailer
- Each product has leaflet ID
- Each product has page number
- Each product has category
- Each product has a name or best-available label
- Raw source text is preserved when available

#### Feature 2.2: Extraction quality baseline

User story 2.2.1

As a developer, I want the first extraction version to be explicitly limited to metadata-derived output so that expectations are clear and the implementation stays small.

Acceptance criteria:
- The implementation does not depend on OCR libraries yet
- The implementation does not claim exact pricing accuracy
- The output shape is compatible with later OCR enhancement

## Epic 3: Improve Extraction Accuracy with Visual Processing

### Goal

Add OCR and image/PDF processing to improve product identification, pricing accuracy, and screenshot generation.

### Business Value

This is the step that makes extraction precise enough for production-style downstream use.

### Features

#### Feature 3.1: OCR pipeline

User story 3.1.1

As the system, I want to extract text from leaflet page images so that product names and prices can be read from visual content.

Acceptance criteria:
- Page images can be prepared for OCR
- OCR returns page text
- OCR output can be attached to extracted products or page-level processing

#### Feature 3.2: Product block detection

User story 3.2.1

As the system, I want to detect product regions on a page so that product records can be built from smaller visual blocks instead of the whole page.

Acceptance criteria:
- Product block coordinates can be generated for a page
- Detected blocks can be processed individually

#### Feature 3.3: Screenshot generation

User story 3.3.1

As an operator, I want a screenshot for each extracted product so that extraction results can be reviewed visually.

Acceptance criteria:
- A screenshot path is generated for extracted products
- Cropped product images are saved to disk

#### Feature 3.4: Price extraction

User story 3.4.1

As the system, I want to extract exact `price_text` and `price_value` so that the output is commercially useful.

Acceptance criteria:
- Extracted products can include `price_text`
- Extracted products can include numeric `price_value`
- Price extraction is based on visual or OCR-derived data rather than page keywords alone

## Epic 4: Harden Discovery and Coverage

### Goal

Reduce operational fragility by improving discovery robustness and adding automated verification.

### Business Value

This lowers maintenance cost and makes future extraction work safer.

### Features

#### Feature 4.1: Dynamic discovery

User story 4.1.1

As the system, I want to discover current leaflets without depending only on hardcoded seed IDs so that the pipeline keeps working as campaigns change.

Acceptance criteria:
- New relevant leaflet IDs can be discovered without manual code edits
- Existing discovery behavior is not regressed

#### Feature 4.2: Automated tests

User story 4.2.1

As a developer, I want parser and filter coverage so that basic Lidl behavior is protected during changes.

Acceptance criteria:
- Lidl payload parsing has automated coverage
- Candidate page filtering has automated coverage

User story 4.2.2

As a developer, I want extraction and persistence coverage so that the first usable extraction flow is protected during refactoring.

Acceptance criteria:
- Minimal extraction behavior has automated coverage
- Product persistence behavior has automated coverage

## Recommended Delivery Order

1. Epic 1: Deliver a usable CLI extraction workflow
2. Epic 2: Implement minimal metadata-based extraction
3. Epic 4 Feature 4.2: Add focused tests for the delivered flow
4. Epic 3: Add visual-processing accuracy improvements
5. Persist leaflet pages in SQLite so extraction can run from stored snapshots

## Recommended Next Sprint Scope

The next sprint should target a thin vertical slice from Epic 1 and Epic 2:

- Add leaflet lookup by ID
- Implement real `extract-lidl`
- Implement minimal `extract_products_from_page()`
- Persist deduplicated products
- Print extraction summary in the CLI

This is the smallest slice that converts the current scaffold into a working product extraction workflow.
