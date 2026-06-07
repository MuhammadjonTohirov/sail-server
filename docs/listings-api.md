# Listings API Guide

This document covers the end-to-end listings flow in Sail:

- taxonomy data needed before creating a listing
- listing create and update endpoints
- media upload, reorder, delete, refresh, activate, deactivate, delete, share
- public and owner listing fetch endpoints
- contact reveal flow
- listing search

Base URL examples below use `http://localhost:8080/api/v1`.

## Response Format

Every API response is wrapped in the standard envelope:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "code": 200
}
```

For paginated DRF list endpoints such as `GET /my/listings` and `GET /users/<user_id>/listings`, `data` contains:

```json
{
  "results": [],
  "count": 0,
  "page": 1,
  "per_page": 20,
  "next": null,
  "previous": null
}
```

Search uses a custom payload shape inside `data`:

```json
{
  "results": [],
  "total": 0,
  "page": 1,
  "per_page": 20,
  "facets": {}
}
```

## Auth Rules

- Public endpoints: category tree, category attributes, locations, listing detail, user listings, search, interest, reveal-contact.
- Authenticated endpoints: create, update, media upload/delete/reorder, refresh, activate, deactivate, delete, share, my listings.
- Owner-only listing mutations always require `Authorization: Bearer <access>`.

## Localization

Taxonomy and listing serialization support `?lang=ru` and `?lang=uz`.

- Default is Russian.
- Categories, attribute labels, and location names are localized through this query parameter.

## Listing Lifecycle Summary

1. Fetch categories.
2. Fetch attributes for the chosen category.
3. Fetch regions, districts, or cities for the chosen location.
4. Create the listing.
5. Upload media.
6. Reorder media if needed.
7. Fetch the public listing or owner listings.
8. Use reveal-contact when a user explicitly asks to see seller contact info.

## Data Needed Before Create

### Categories

`GET /categories`

Returns the full category tree. Optional query parameter:

- `parent_id`: return only the direct children of a category as a flat list

Example:

```http
GET /api/v1/categories?lang=ru
```

Response item:

```json
{
  "id": 1,
  "name": "Электроника",
  "slug": "electronics",
  "icon": "electronics",
  "icon_url": "/media/category_icons/electronics.png",
  "is_leaf": false,
  "order": 0,
  "children": []
}
```

### Category Attributes

`GET /categories/<category_id>/attributes`

Returns attributes for the selected category, including inherited attributes from parent categories.

Example:

```http
GET /api/v1/categories/12/attributes?lang=ru
```

Response item:

```json
{
  "id": 21,
  "key": "brand",
  "label": "Бренд",
  "type": "select",
  "unit": null,
  "options": ["apple", "samsung", "xiaomi"],
  "is_indexed": true,
  "is_required": true,
  "min_number": null,
  "max_number": null
}
```

Supported attribute types:

- `text`
- `number`
- `boolean`
- `select`
- `multiselect`
- `range`

### Locations

`GET /locations`

Optional query parameter:

- `parent_id`: return children for a location

Important behavior:

- if there is exactly one country root, `GET /locations` returns that country's direct children instead of the country itself
- in the current Uzbekistan seed, the root call returns regions

Example:

```http
GET /api/v1/locations?lang=ru
GET /api/v1/locations?parent_id=241&lang=ru
```

Response item:

```json
{
  "id": 242,
  "name": "Ташкентская область",
  "name_ru": "Ташкентская область",
  "name_uz": "Toshkent вилояти",
  "slug": "tashkent-region",
  "kind": "REGION",
  "lat": null,
  "lon": null,
  "has_children": true,
  "parent": 241
}
```

## Listing Object

Typical listing response fields:

- `id`
- `title`
- `description`
- `price_amount`
- `price_currency`
- `price_normalized`
- `is_price_negotiable`
- `condition`
- `deal_type`
- `seller_type`
- `status`
- `category`
- `category_name`
- `category_slug`
- `location`
- `location_name`
- `location_slug`
- `created_at`
- `refreshed_at`
- `expires_at`
- `quality_score`
- `contact_phone_masked`
- `contact_name`
- `contact_email`
- `contact_phone`
- `lat`
- `lon`
- `media`
- `attributes`
- `seller`
- `view_count`
- `favorite_count`
- `interest_count`
- `share_url` — absolute URL of the public share/preview page (see [Link Previews](#link-previews-opengraph)). Use this when sharing a listing in chats/social apps so it unfurls into a rich card.

### Visibility Rules

- Public listing detail returns only `active` listings.
- Owners can fetch their own non-active listings.
- Public listing fetches never expose raw `contact_phone` or `contact_email`.
- Public listing fetches return only `contact_phone_masked`.
- Raw seller contact must be fetched through `POST /listings/<id>/reveal-contact`.

### Listing Status Values

- `draft`
- `pending_review`
- `active`
- `paused`
- `closed`
- `expired`

### Condition Values

- `new`
- `used`

### Deal Type Values

- `sell`
- `exchange`
- `free`

### Seller Type Values

- `person`
- `business`

## Create Listing

### Serializer-Based Create

`POST /listings`

Authenticated.

Request body:

```json
{
  "title": "iPhone 15 128GB",
  "description": "Clean, lightly used",
  "price_amount": "9500000",
  "price_currency": "UZS",
  "is_price_negotiable": true,
  "condition": "used",
  "deal_type": "sell",
  "seller_type": "person",
  "category": 12,
  "location": 254,
  "lat": 41.3111,
  "lon": 69.2797,
  "contact_name": "Ali",
  "contact_email": "ali@example.com",
  "contact_phone": "+998901112233",
  "attributes": [
    { "attribute": 21, "value": "apple" },
    { "attribute": 22, "value": 2023 },
    { "attribute": 23, "value": ["128gb"] }
  ]
}
```

Notes:

- `title`, `category`, and `location` are mandatory in practice.
- If `contact_name`, `contact_email`, or `contact_phone` are missing, the API falls back to the authenticated user's profile when possible.
- `contact_phone_masked` is generated automatically.
- If `STRICT_ATTRIBUTES=1`, missing required attributes cause validation errors.
- If `STRICT_ATTRIBUTES` is disabled, valid provided attributes are saved and missing required attributes are tolerated.

### Raw Create

`POST /listings/raw`

Authenticated.

Use this when the client wants a simple direct JSON shape without serializer-level validation. It still validates:

- `title`, `category`, `location`
- enum values
- numeric coercion
- category and location existence

It also supports:

- `contact_name`
- `contact_email`
- `contact_phone`
- `attributes`

## Update Listing

### Serializer-Based Update

`PATCH /listings/<id>/edit`

Authenticated and owner-only.

Supports partial updates for:

- `title`
- `description`
- `price_amount`
- `price_currency`
- `is_price_negotiable`
- `condition`
- `deal_type`
- `seller_type`
- `category`
- `location`
- `lat`
- `lon`
- `contact_name`
- `contact_email`
- `contact_phone`
- `attributes`

If `attributes` are provided, they replace the existing `ListingAttributeValue` rows for that listing.

### Raw Update

`PATCH /listings/<id>/edit/raw`

Authenticated and owner-only.

Supports the same common fields with simpler request handling.

Important behavior:

- changing `contact_phone` automatically recalculates `contact_phone_masked`
- if `attributes` is sent, existing attribute rows are replaced with the new set

## Listing Media

### Upload Media

`POST /listings/<id>/media`

Authenticated and owner-only.

Request:

- content type: `multipart/form-data`
- field name: `file`

Response item:

```json
{
  "id": 15,
  "type": "photo",
  "image": "/media/listings/352/photo.jpg",
  "image_url": "/media/listings/352/photo.jpg",
  "width": 500,
  "height": 500,
  "order": 0,
  "uploaded_at": "2026-03-12T12:00:00Z"
}
```

### Delete Media

`DELETE /listings/<listing_id>/media/<media_id>`

Authenticated and owner-only.

Returns:

```json
{
  "status": "deleted"
}
```

### Reorder Media

`POST /listings/<id>/media/reorder`

Authenticated and owner-only.

Request body:

```json
{
  "media_ids": [3, 1, 2]
}
```

Returns the updated ordered media list.

## Fetch Listings

### Listing Detail

`GET /listings/<id>`

Public for active listings. Owner can also fetch their own non-active listings.

Public response behavior:

- `contact_phone` is `""`
- `contact_email` is `""`
- `contact_phone_masked` is available

Owner response behavior:

- full contact info is returned

### My Listings

`GET /my/listings`

Authenticated.

Returns all listings owned by the current user. This endpoint is paginated by default.

Supported pagination query parameters:

- `page`
- `per_page`

### User Listings

`GET /users/<user_id>/listings`

Public.

Returns only active listings for the requested user.

Optional query parameters:

- `category`: filter by category slug
- `sort`: `newest`, `oldest`, `price_asc`, `price_desc`
- `page`
- `per_page`

## Contact Reveal and Interest Tracking

### Reveal Contact

`POST /listings/<id>/reveal-contact`

Public.

Returns seller contact details for active listings:

```json
{
  "contact_name": "Seller Contact",
  "contact_phone": "+998901112233",
  "contact_email": "seller@example.com",
  "tracked": true
}
```

Behavior:

- increments `interest_count` for non-owner viewers
- does not increment `interest_count` when the owner reveals their own listing contact
- returns `404` if the listing is not active
- returns `404` if seller contact is unavailable

### Interest Only

`POST /listings/<id>/interest`

Public.

Use this if the client wants to track interest without returning contact data.

Behavior:

- increments `interest_count` for non-owner viewers
- returns `{ "tracked": false }` for owners

## Listing State and Utility Actions

### Refresh

`POST /listings/<id>/refresh`

Authenticated and owner-only.

Updates `refreshed_at`, which affects newest ordering and search freshness.

### Deactivate

`POST /listings/<id>/deactivate`

Authenticated and owner-only.

Sets status to `paused`.

### Activate

`POST /listings/<id>/activate`

Authenticated and owner-only.

Allowed only for `paused` and `closed` listings. Sets status to `active` and updates `refreshed_at`.

### Delete

`DELETE /listings/<id>/delete`

Authenticated and owner-only.

Permanently deletes the listing.

### Share to Telegram

`POST /listings/<id>/share`

Authenticated and owner-only.

Request body:

```json
{
  "telegram_chat_ids": [-1001111111111, -1002222222222]
}
```

Behavior:

- validates that the chat IDs belong to the current user
- only active Telegram chat configs are accepted
- starts async Telegram sharing

## Link Previews (OpenGraph)

When a listing link is pasted into Telegram, WhatsApp, Facebook, X, etc., those
crawlers fetch the URL and build a preview card from the page's OpenGraph and
Twitter Card meta tags. The SPA at `WEB_BASE_URL` is client-rendered and exposes
no tags to crawlers, so the backend serves a dedicated, server-rendered preview
page:

`GET /l/<id>` (note: site root, **not** under `/api/v1`)

- Public, unauthenticated, active listings only (404 otherwise).
- Returns HTML carrying `og:title`, `og:description`, `og:image` (absolute),
  `og:site_name`, `og:url`, `product:price:*`, and `twitter:card` tags.
- The card title mirrors marketplace convention: `"<title>: <price> - <category>, <location>"`.
- Real browsers are redirected to the SPA listing screen (`WEB_BASE_URL/l/<id>`);
  crawlers keep the meta tags.

Clients should share the `share_url` field returned on the listing object — it
points to this page, so the link unfurls into a rich card.

### Serving the preview on the main domain

`share_url` resolves to the **backend** host (e.g. `https://api.sail.uz/l/<id>`),
which works out of the box. To unfurl the prettier main-domain URL
(`https://sail.uz/l/<id>`) like OLX, route it to this endpoint via one of:

- **Edge proxy (recommended):** at the `sail.uz` reverse proxy/CDN, proxy
  `GET /l/<id>` to the backend's `/l/<id>` for crawler user-agents
  (`Telegrambot`, `facebookexternalhit`, `WhatsApp`, `Twitterbot`, …) while
  humans continue to the SPA.
- **Frontend SSR:** have the SPA server-render the same OpenGraph tags.

## Search Listings

`GET /search/listings`

Public.

Only active listings are searchable.

### Text Search

`q` is tokenized and matched using:

- normal full-text match
- phrase-prefix match
- fuzzy match
- wildcard infix fallback for longer tokens

This allows queries like `phone` to match `iPhone`.

### Search Query Parameters

- `q`
- `currency`
- `min_price`
- `max_price`
- `category_slug`
- `location_slug`
- `condition`
- `user_id`
- `sort`: `relevance`, `newest`, `price_asc`, `price_desc`
- `page`
- `per_page`

### Attribute Filters

Use `attrs.<attribute_key>` for exact matching:

```http
GET /api/v1/search/listings?attrs.brand=apple
GET /api/v1/search/listings?attrs.storage=128gb,256gb
GET /api/v1/search/listings?attrs.dual_sim=true
```

Use `attrs.<attribute_key>_min` and `attrs.<attribute_key>_max` for numeric filters:

```http
GET /api/v1/search/listings?attrs.year_min=2020&attrs.year_max=2024
```

### Search Response

Each result comes from the search index and includes fields such as:

- `id`
- `score`
- `title`
- `description`
- `category_path`
- `location_path`
- `location_name_ru`
- `location_name_uz`
- `price`
- `price_normalized`
- `currency`
- `condition`
- `geo`
- `refreshed_at`
- `quality_score`
- `attrs`
- `media_urls`
- `seller_id`
- `seller_name`

`facets` may contain:

- `categories`
- `locations`
- `conditions`
- `price_range`
- `attributes`

## Search Index Notes

- search index updates are triggered automatically when listings, media, or attributes change
- if Celery broker dispatch fails, the app falls back to inline index sync after commit
- non-active listings are removed from the search index

Useful commands:

```bash
python manage.py search_check
python manage.py search_init_index
python manage.py search_reindex --clear --delete-stale
```

## Recommended Client Flow

### Create Listing Flow

1. `GET /categories`
2. `GET /categories/<id>/attributes`
3. `GET /locations` and `GET /locations?parent_id=<id>`
4. `POST /listings`
5. `POST /listings/<id>/media`
6. `POST /listings/<id>/media/reorder`

### Public Browse Flow

1. `GET /search/listings`
2. `GET /users/<user_id>/listings`
3. `GET /listings/<id>`
4. `POST /listings/<id>/reveal-contact` when the user taps "Show contact"

### Owner Management Flow

1. `GET /my/listings`
2. `PATCH /listings/<id>/edit`
3. `POST /listings/<id>/refresh`
4. `POST /listings/<id>/deactivate` or `POST /listings/<id>/activate`
5. `DELETE /listings/<id>/delete`
