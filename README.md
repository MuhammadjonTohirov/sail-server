# Server (Django)

This repository is the Django API server for Sail.

## Local Development

### Requirements

- Python 3.11+
- `pip`
- A Docker-compatible daemon only if you want OpenSearch-backed search endpoints

`build.sh` is not a starter script. It installs dependencies, collects static files, and runs migrations for build/deploy use. For local development, use the steps below.

### Quick Start

Run everything from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_taxonomy  # optional sample categories/locations
python manage.py runserver 0.0.0.0:8080
```

The copied `.env` enables `DJANGO_DEBUG=1`, so the server boots locally without extra production-only settings.

### Optional Local Services

#### OpenSearch for search endpoints

Search endpoints depend on OpenSearch. The app defaults to `http://localhost:9200`.

```bash
./scripts/opensearch_up.sh
python manage.py search_init_index
python manage.py search_check
```

Notes:

- The helper script expects `docker` to be available in `PATH`.
- The first image pull is large and can take a few minutes.
- If OpenSearch is not running, the core API can still start, but search endpoints will not work.
- Run `python manage.py search_reindex` after you already have listing data that should be searchable.

#### Redis for Celery

Redis is optional in local development.

- Without `REDIS_URL` or `CELERY_BROKER_URL`, Celery falls back to `memory://` in debug mode and tasks run eagerly.
- With Redis running, set one of those variables and start workers:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Health Checks

- Liveness: `http://localhost:8080/healthz/`
- API health: `http://localhost:8080/api/v1/health`
- Language: `GET` or `POST http://localhost:8080/api/v1/i18n`

## Configuration

Copy `.env.example` to `.env` for local work. The example file is shell-compatible and documents the main settings.

### Required for local development

- `DJANGO_DEBUG=1`

### Required when `DJANGO_DEBUG=0`

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `TELEGRAM_BOT_TOKEN`
- `CELERY_BROKER_URL` or `REDIS_URL`

### Common settings

- Database:
  - SQLite is the default.
  - Set `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and optionally `POSTGRES_PORT` to use Postgres.
- Search:
  - `OPENSEARCH_URL` defaults to `http://localhost:9200`
  - `OPENSEARCH_VERIFY_CERTS` defaults to `false`
  - `OPENSEARCH_INDEX_PREFIX` defaults to `sail`
  - `OPENSEARCH_INDEX_VERSION` defaults to `2`
- Localization:
  - `LANGUAGE_CODE` defaults to `ru`
  - `TIME_ZONE` defaults to `Asia/Tashkent`
- Telegram/web:
  - `WEB_BASE_URL` defaults to `https://sail.uz`
  - `TELEGRAM_WEBHOOK_SECRET_TOKEN` should be set in production
- Admin bootstrap:
  - `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`

## Auth (OTP)

- Request code:
  - `POST http://localhost:8080/api/v1/auth/otp/request`
  - Body: `{"phone": "+998901112233"}`
- Verify code:
  - `POST http://localhost:8080/api/v1/auth/otp/verify`
  - Body: `{"phone": "+998901112233", "code": "000000"}`
- Me:
  - `GET http://localhost:8080/api/v1/me`
  - Header: `Authorization: Bearer <access>`

In debug mode the OTP request response includes `debug_code`. If `OTP_DEV_CODE` is set, that fixed value is returned; otherwise a random debug code is generated and returned.

### OTP throttling

- In all modes, the OTP request view enforces at most 3 codes per 10 minutes per phone number.
- When `DJANGO_DEBUG=0`, DRF throttles are also enabled:
  - `otp`: `3/minute`
  - `login`: `5/minute`
  - `anon`: `100/hour`

## Admin (dev)

Create a superuser with the management command:

```bash
python manage.py create_admin
```

Defaults come from `.env` or fall back to:

- username: `admin`
- email: `admin@example.com`
- password: `admin123`

Admin UI: `http://localhost:8080/admin/`

## Taxonomy

- Categories tree: `http://localhost:8080/api/v1/categories`
- Category attributes: `http://localhost:8080/api/v1/categories/1/attributes`
- Locations root: `http://localhost:8080/api/v1/locations`
- Locations children: `http://localhost:8080/api/v1/locations?parent_id=1`
- Localization: append `?lang=ru|uz`

## Listings

- Full listings API reference: [docs/listings-api.md](docs/listings-api.md)
- Create listing: `POST http://localhost:8080/api/v1/listings`
- My listings: `GET http://localhost:8080/api/v1/my/listings`
- Listing detail: `GET http://localhost:8080/api/v1/listings/<id>`
- Update listing: `PATCH http://localhost:8080/api/v1/listings/<id>/edit`
- Bump listing: `POST http://localhost:8080/api/v1/listings/<id>/refresh`
- Upload photo: `POST http://localhost:8080/api/v1/listings/<id>/media`

Example create payload:

```json
{
  "title": "iPhone 13 128GB",
  "description": "Good condition",
  "price_amount": "4500000",
  "price_currency": "UZS",
  "condition": "used",
  "category": 1,
  "location": 1,
  "lat": 41.31,
  "lon": 69.27,
  "attributes": [
    { "attribute": 1, "value": "Apple" },
    { "attribute": 2, "value": 2021 },
    { "attribute": 3, "value": ["128"] }
  ]
}
```

## Search

- Search endpoint: `GET http://localhost:8080/api/v1/search/listings?q=iphone&sort=newest&per_page=10`
- Common filters:
  - `category_slug=phones`
  - `location_slug=tashkent`
  - `min_price=100000`
  - `max_price=10000000`
  - `attrs.brand=Apple`
  - `attrs.storage=128`

Useful management commands:

```bash
python manage.py search_check
python manage.py search_init_index
python manage.py search_reindex
```

## Saved Searches

- Create/list: `POST` or `GET http://localhost:8080/api/v1/saved-searches`
- Run now: `POST http://localhost:8080/api/v1/saved-searches/<id>/run`
- Dev runner: `python manage.py savedsearches_run`

Example body:

```json
{
  "title": "Cheap iPhones",
  "query": {
    "params": {
      "q": "iphone",
      "max_price": 5000000
    }
  },
  "frequency": "daily"
}
```

## Moderation

- Report listing: `POST http://localhost:8080/api/v1/reports`
- Staff queue: `GET http://localhost:8080/api/v1/moderation/queue`

Example report body:

```json
{
  "listing": 1,
  "reason_code": "spam",
  "notes": "optional"
}
```

## API Docs

- OpenAPI schema: `GET http://localhost:8080/api/schema/`
- Swagger UI: `GET http://localhost:8080/api/docs/`

## Current Limitations

- The standalone `POST /api/v1/uploads/presign` endpoint is not enabled in this repository. Do not rely on that route.
- Development media uploads are served from `MEDIA_ROOT` under `/media/`.
