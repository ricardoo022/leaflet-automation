# Lidl Leaflets API Research

## Purpose

This document captures the reverse-engineering work done on Lidl Portugal's leaflet system so the implementation can start from verified facts instead of assumptions.

Primary goal of this research:

- determine whether leaflet data is available through a public API
- identify which parts of the final solution can use API data directly
- identify which parts still require image/PDF processing, OCR, or browser automation

This is written as implementation guidance for the backend.

## Main conclusion

The leaflet system does use a public JSON API, and it is worth using.

However, based on the payloads tested so far, the API is best used as a:

- leaflet discovery layer
- metadata source
- date filtering source
- page image/PDF source
- page text hint source

It is not yet sufficient by itself for:

- exact product-level extraction
- exact price extraction for all products
- exact per-product screenshot extraction

The current best approach is:

1. use the API to discover and prioritize leaflets
2. use API metadata and page text to narrow down relevant pages
3. use page images or PDFs for product extraction
4. use OCR and image segmentation where structured data is missing
5. optionally use Playwright later if viewer interaction or screenshot automation is still needed

## Entry points discovered

### Public leaflet page

Lidl Portugal leaflet landing page:

`https://www.lidl.pt/c/folhetos/s10020672`

This page is useful because it exposes:

- visible leaflet titles
- visible date labels such as `A partir de 01/06`
- leaflet page URLs
- leaflet preview images

Example leaflet URLs found on that page:

- `https://www.lidl.pt/l/pt/folhetos/promocoes-a-partir-de-01-06/ar/0?lf=HHZ`
- `https://www.lidl.pt/l/pt/folhetos/novidades-a-partir-de-01-06/ar/0?lf=HHZ`
- `https://www.lidl.pt/l/pt/folhetos/promocoes-a-partir-de-25-05/ar/0?lf=HHZ`

### Leaflet SPA shell

Leaflet detail pages load a separate frontend application.

The detail page is effectively an SPA shell which points at:

- frontend host: `https://lidl.leaflets.schwarz`

The shell itself does not contain the useful product data directly.

### API host

The leaflet SPA bundle contains these environment values:

- `VITE_API_URL: "https://endpoints.leaflets.schwarz"`
- `VITE_API_VERSION: "v4"`

This makes the effective base API:

- `https://endpoints.leaflets.schwarz/v4`

## API endpoints verified

### 1. Flyer endpoint

Endpoint:

`GET https://endpoints.leaflets.schwarz/v4/flyer`

Verified behavior:

- endpoint is public
- returns JSON
- requires query parameter `flyer_identifier`

When called without the required parameter, it returns a structured error:

```json
{
  "message": "Request is missing one or more mandatory url parameters: flyer_identifier."
}
```

Known query parameters from the bundle:

- `flyer_identifier`
- `region_id`
- `region_code`
- `store_id`

Current interpretation:

- `flyer_identifier` is the main leaflet UUID
- the region/store parameters are likely needed for regionalized content in some markets or future cases

### 2. Flyer fallback endpoint

Endpoint:

`GET https://endpoints.leaflets.schwarz/v4/flyer-fallback?domain_url=https://www.lidl.pt`

Verified response:

```json
{
  "success": true,
  "fallback": {
    "matchingCategory": "2bfb0737-204e-11e7-a7b6-005056ab0fb6",
    "quitUrl": "https://www.lidl.pt/c/folhetos/s10020672",
    "homeUrl": "https://www.lidl.pt",
    "privacyUrl": "https://www.lidl.pt/c/protecao-de-dados-lidl-pt/s10026939",
    "imprintUrl": "https://www.lidl.pt/c/ficha-tecnica-lidl-pt/s10027346"
  }
}
```

Usefulness:

- confirms the API is live and public
- provides domain-specific fallback config
- not enough by itself to enumerate all leaflets

### 3. Translations fallback endpoint

Endpoint:

`GET https://endpoints.leaflets.schwarz/v4/translations-fallback?domain_url=https://www.lidl.pt&client_locale=pt-PT`

Verified behavior:

- returns localized UI strings
- confirms locale-related API behavior
- not directly relevant for promo extraction

Still useful because it confirms the leaflet app is parameterized by:

- `domain_url`
- locale values such as `pt-PT` / `lidl/pt-PT`

## How leaflet IDs were identified

The key implementation question was whether we could obtain valid `flyer_identifier` values.

### Result

Yes.

Preview image URLs on the listing page contain UUID-like values which successfully worked as `flyer_identifier` values.

Examples of working IDs:

- `019e6f22-4ece-7cf2-8ab3-6a958456e86a`
- `019e6f27-3178-7eb7-a151-758e09e1eb07`
- `019e4a4b-a039-7ba5-87b0-bca69e18d380`

These corresponded to real leaflets when passed to the flyer endpoint.

### Important note

This does not yet prove that the listing page image UUID is always the same as the leaflet `id` in every case, but it worked for the tested leaflets and is a strong signal that the system uses the same UUID consistently.

## Sample tested leaflets

### Promoções - A partir de 01/06

Identifier:

- `019e6f22-4ece-7cf2-8ab3-6a958456e86a`

API call:

- `https://endpoints.leaflets.schwarz/v4/flyer?flyer_identifier=019e6f22-4ece-7cf2-8ab3-6a958456e86a`

Key fields found:

- `flyer.name = "Promoções"`
- `flyer.title = "A partir de 01/06"`
- `flyer.category = "HHZ PT"`
- `flyer.subcategory = "Semanais"`
- `flyer.startDate = "2026-05-29"`
- `flyer.endDate = "2026-06-07"`
- `flyer.offerStartDate = "2026-06-01"`
- `flyer.offerEndDate = "2026-06-07"`
- `flyer.status = "current"`

### Novidades - A partir de 01/06

Identifier:

- `019e6f27-3178-7eb7-a151-758e09e1eb07`

Key fields found:

- `flyer.name = "Novidades"`
- `flyer.title = "A partir de 01/06"`
- `flyer.startDate = "2026-05-29"`
- `flyer.endDate = "2026-06-07"`

### Promoções - A partir de 25/05

Identifier:

- `019e4a4b-a039-7ba5-87b0-bca69e18d380`

Key fields found:

- `flyer.name = "Promoções"`
- `flyer.title = "A partir de 25/05"`
- `flyer.startDate = "2026-05-22"`
- `flyer.endDate = "2026-05-31"`
- `flyer.offerStartDate = "2026-05-25"`
- `flyer.offerEndDate = "2026-05-31"`

## Flyer payload structure

The tested responses shared this top-level shape:

```json
{
  "self": "...",
  "version": 4,
  "success": true,
  "message": "...",
  "dateTime": "...",
  "numberOfEntries": 1,
  "flyer": {
    "...": "..."
  }
}
```

### Important `flyer` fields found

Identity and navigation:

- `id`
- `name`
- `title`
- `category`
- `subcategory`
- `flyerUrlAbsolute`
- `quitUrl`
- `homeUrl`
- `privacyUrl`
- `imprintUrl`
- `newsletterUrl`

Dates and status:

- `startDate`
- `endDate`
- `offerStartDate`
- `offerEndDate`
- `status`

Locale and country:

- `locale`
- `clientLocale`
- `apiCountryCode`
- `countryCode`

File and asset references:

- `pdfUrl`
- `hiResPdfUrl`
- `thumbnailUrl`
- `publicThumbnail`
- `teasers.teaser_666x475`
- `teasers.teaser_2020x1440`
- `teasers.teaser_w1010`

Content collections:

- `pages`
- `products`
- `topics`
- `relatedFlyers`

## Related flyers

One of the most useful discoveries is that `relatedFlyers` exists and is populated.

This means a single leaflet payload can help navigate to additional leaflets.

### Structure seen in `relatedFlyers[]`

Each related flyer entry contained:

- `id`
- `name`
- `title`
- `slug`
- `url`
- `startDate`
- `endDate`
- `pdfUrl`
- `thumbnailUrl`
- `regionCodes`
- `stores`

### Example related flyer

```json
{
  "id": "019e6f22-4ece-7cf2-8ab3-6a958456e86a",
  "name": "Promoções",
  "title": "A partir de 01/06",
  "slug": "promocoes-a-partir-de-01-06",
  "url": "https://www.lidl.pt/l/pt/folhetos/promocoes-a-partir-de-01-06/ar/0?lf=HHZ",
  "startDate": "2026-05-29T00:00:00+00:00",
  "endDate": "2026-06-07T23:59:59+00:00",
  "pdfUrl": "...",
  "thumbnailUrl": "..."
}
```

### Why this matters

This is likely enough to build a discovery workflow such as:

1. get one known current leaflet ID
2. call `/v4/flyer`
3. collect `relatedFlyers`
4. filter by dates and category/subcategory
5. enqueue target leaflets for extraction

That could reduce or eliminate repeated scraping of the listing page.

## Pages structure

`flyer.pages` is populated and useful.

Tested payloads included:

- 38 pages for one weekly promo leaflet
- 25 pages for one `Novidades` leaflet
- 45 pages for another weekly promo leaflet

### Useful page fields found

The most useful fields under `flyer.pages[*]` were:

- `number`
- `image`
- `zoom`
- `thumbnail`
- `altText`
- `keyWords`
- `links`
- `pageType`
- `type`

### What these fields are useful for

`image`, `zoom`, `thumbnail`:

- direct page image access
- OCR input
- page segmentation input
- page screenshot fallback if browser automation is not used

`altText`:

- concise page description
- often contains human-readable category/product hints
- often contains date context

`keyWords`:

- most useful text-bearing field found so far
- appears to contain OCR-like or indexed page terms
- often includes product names and category clues

`links`:

- currently low value in tested leaflets
- mostly empty or generic media metadata

### Example useful `altText`

Examples found in tested page data:

- `Capa do folheto promocional do Lidl com destaque para descontos em cerveja Sagres Mini, bananas e vinho branco de Borba.`
- `Promoções de talho, peixaria e frescos do Lidl, incluindo lombo de salmão, frango de churrasco e laranjas do Algarve.`
- `Ofertas de frutas e legumes frescos no Lidl, com descontos em pera vermelha, tomate chucha e cogumelos marron.`

### Example useful `keyWords`

Examples found in tested page data:

- `Tomate Cherry Pera Nacional`
- `Cenoura Nacional`
- `Laranja`
- `Maçã Golden`
- `Cebola`
- `Mistura Legumes Sopa`
- `Saqueta Fruta`
- `pera`
- `tomate`
- `uva`
- `cogumelos`

### Practical meaning

Even when the API does not expose structured products, page text seems good enough to:

- identify likely fruit and vegetable pages
- rank pages for OCR first
- skip clearly irrelevant pages
- reduce total OCR cost and runtime

## Products field status

This is the most important limitation discovered so far.

### Current finding

The tested leaflet payloads included:

- `flyer.products`

But in the tested cases it was empty:

- `flyer.products = []`

### What this means

There is evidence in the frontend code that the app can work with product-level structures in some situations, but the three tested leaflet payloads did not provide usable structured product lists.

So we should not assume that `flyer.products` will contain everything we need.

### Impact on solution design

Do not design the backend around the assumption that:

- every product will already exist in the API
- prices are easily extractable from structured JSON
- screenshots can be created from product bounding boxes delivered by the API

Instead, assume that product extraction may require image/PDF work for at least part of the solution.

## Topics field status

Tested payloads contained:

- `flyer.topics`

But in the tested payloads it was empty.

That means `topics` currently cannot be relied on for category filtering such as `Frutas e Legumes`.

## Separate product detail API in the frontend code

The leaflet frontend bundle also referenced a separate product API:

- base path: `/p/api/`
- detail path shape: `/detail/{productId}/{COUNTRY}/{localePrefix}`

This suggests:

- the leaflet app can fetch richer product detail from a second API
- leaflet-level payloads and product detail payloads are separate concerns

Important limitation:

- in the tested leaflet payloads, we did not get a populated leaflet product list to drive this second API directly

So this product detail API is interesting, but not yet enough to solve the end-to-end extraction problem by itself.

## What the API is good for right now

### Strong use cases

1. discover leaflets
2. filter leaflets by date
3. distinguish weekly vs special leaflets using metadata
4. collect direct leaflet URLs
5. collect direct PDF URLs
6. collect page image URLs
7. prioritize relevant pages using `altText` and `keyWords`
8. expand discovery using `relatedFlyers`

### Weak use cases

1. exact product enumeration
2. exact price extraction
3. exact promo block coordinates
4. exact per-product screenshot generation without extra processing

## Is the API worth using?

Yes.

It is worth using as the backbone of the discovery pipeline because it gives verified access to:

- leaflet IDs
- leaflets dates
- leaflet categorization hints
- page image assets
- related leaflet navigation
- PDF assets
- page text hints

That alone can remove a large amount of brittle website scraping.

But it should not be treated as a complete product extraction API.

## Recommended architecture based on current findings

### Recommended pipeline

1. seed discovery from the public folhetos page or from one known current leaflet ID
2. collect leaflet IDs and URLs
3. call `/v4/flyer` for each candidate leaflet
4. filter by dates:
   - upcoming leaflets only
   - weekly and weekend programs only if possible
5. classify leaflets by `name`, `title`, `category`, `subcategory`
6. inspect `pages[*].altText` and `pages[*].keyWords` to find likely `Frutas e Legumes` pages
7. download page images or PDFs
8. run OCR / image parsing on likely pages only
9. detect product blocks
10. extract:
   - product name
   - price
   - promo dates
   - program type
11. produce per-product screenshots
12. deduplicate across pages and leaflets

### Why this architecture fits the data

Because the current state of the API is:

- strong at the leaflet level
- medium at the page level
- weak at the product structure level

## Implementation notes

### Date handling

There are at least two date ranges to consider:

- `startDate` / `endDate`
- `offerStartDate` / `offerEndDate`

Current interpretation:

- `offerStartDate` / `offerEndDate` are more relevant to promo validity
- `startDate` / `endDate` may describe the leaflet publication/availability window

When filtering upcoming promotions, code should prefer:

- `offerStartDate`
- `offerEndDate`

and only fall back to `startDate` / `endDate` if needed.

### Weekly vs special leaflets

The landing page visually distinguishes:

- `Semanais`
- `Especiais`

The API payload also exposed:

- `subcategory = "Semanais"` for tested weekly promotion leaflets

This is promising for filtering, but should still be treated carefully until more leaflet types are sampled.

### Produce category filtering

The target categories for the business case are:

- Frutas
- Legumes
- Especialidades
- Quarta gama
- Cogumelos
- Frutos secos e desidratados
- Azeitonas e tremoços

The API does not yet expose these as reliable structured category labels in the tested payloads.

So current implementation should likely use:

1. page-level keyword filtering
2. OCR text filtering
3. a controlled dictionary of category/product terms

### Avoiding duplicate work

Because `relatedFlyers` can point to overlapping leaflet sets, dedupe should be done by:

- `flyer.id`
- `flyerUrlAbsolute` or `url`
- `slug` when present on related flyer items

At the product level, dedupe will need stronger logic later.

## Risks and unknowns

### Known risks

1. `flyer.products` may stay empty for the leaflets we care about
2. prices may exist only visually inside page images/PDFs
3. some leaflets may use layouts that make OCR harder
4. page `keyWords` quality may vary between leaflets
5. region or store parameters may matter more in other markets or campaigns

### Current unknowns

1. whether some leaflet types return populated `flyer.products`
2. whether the PDF assets are easier to parse than the page image assets
3. whether weekend programs have different metadata patterns
4. whether the page images already contain enough resolution for stable OCR
5. whether a second hidden list endpoint exists beyond what has been identified so far

## Recommended next investigations

The next highest-value checks are:

1. inspect `pdfUrl` payload quality and determine whether PDF parsing is better than image OCR
2. compare page image OCR vs PDF text extraction on one weekly leaflet
3. test a leaflet known to be rich in `Frutas e Legumes`
4. sample weekend promo leaflets separately
5. check whether some leaflet categories populate `flyer.products`
6. measure whether `altText` + `keyWords` can narrow pages enough to avoid OCR on the full leaflet

## Short decision summary

If implementation started today, the safest design would be:

- API-first for discovery
- PDF/image-first for extraction
- OCR-assisted for exact product data
- Playwright optional, not mandatory for the first backend version

This is currently the best verified path based on the leaflet system behavior observed in Lidl Portugal.
