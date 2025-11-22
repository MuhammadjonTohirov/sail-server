# Server (Django) — Local Development

Quick start (no Docker):

1) Create a virtual environment and install deps
```
cd server
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2) Configure env (optional; defaults are fine for dev)
```
cp .env.example .env
```

3) Run migrations and start the dev server
```
python manage.py migrate
python manage.py seed_taxonomy  # optional: add sample categories/locations
python manage.py runserver 0.0.0.0:8080
```

Health checks
- Liveness: http://localhost:8080/healthz/
- API health: http://localhost:8080/api/v1/health
- Language: GET/POST http://localhost:8080/api/v1/i18n (POST {"lang":"ru|uz"} sets cookie)

Internationalization (i18n)
- Default language is Russian (`ru`); Uzbek (`uz`) is enabled.
- Django uses `LocaleMiddleware` and respects `Accept-Language` or user session.
- Frontend (Next.js) uses subpath routing: `/ru/...` (default) and `/uz/...`.
- You can switch locales via the header toggle in the web client.

Taxonomy endpoints
- Categories tree: http://localhost:8080/api/v1/categories
- Category attributes: http://localhost:8080/api/v1/categories/1/attributes
- Locations root: http://localhost:8080/api/v1/locations
- Locations children: http://localhost:8080/api/v1/locations?parent_id=1
- Localization: append `?lang=ru|uz` to taxonomy endpoints (e.g., `/api/v1/categories?lang=uz`). If omitted, defaults to `ru` or uses `Accept-Language`.

Auth (OTP) flow
- Request code:
  - POST http://localhost:8080/api/v1/auth/otp/request
  - Body: {"phone": "+998901112233"}
  - In DEBUG with OTP_DEV_CODE set, response includes {"debug_code":"000000"}
- Verify code:
  - POST http://localhost:8080/api/v1/auth/otp/verify
  - Body: {"phone": "+998901112233", "code": "000000"}
  - Response: { access, refresh, profile }
- Me endpoint:
  - GET http://localhost:8080/api/v1/me with header Authorization: Bearer <access>

Admin (dev)
- Create a superuser quickly (dev defaults: admin/admin123):
  - python manage.py create_admin
  - Visit http://localhost:8080/admin/

Listings
- Create listing (JWT required):
  - POST http://localhost:8080/api/v1/listings
  - Body JSON example (with attributes):
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
        { "attribute": 1, "value": "Apple" },           // select (required)
        { "attribute": 2, "value": 2021 },               // number (min/max enforced if configured)
        { "attribute": 3, "value": ["128"] }            // multiselect example
      ]
    }
- My listings: GET http://localhost:8080/api/v1/my/listings
- Listing detail: GET http://localhost:8080/api/v1/listings/<id>
- Update listing (owner): PATCH http://localhost:8080/api/v1/listings/<id>/edit
  - You can also pass "attributes" array in the same shape as create. Existing values are replaced.
  - If you pass attributes, all required category attributes must be present and valid.
- Bump listing (owner): POST http://localhost:8080/api/v1/listings/<id>/refresh
- Upload photo (owner):
  - POST http://localhost:8080/api/v1/listings/<id>/media with form-data key "file" = image
  - Returns uploaded media with absolute URL

Search & Facets
- Configure OpenSearch URL (default http://localhost:56984) in `.env` as `OPENSEARCH_URL`.
- Ensure index exists:
  - Index is auto-created on first index request; or run a search to trigger create.
- Endpoints:
  - GET http://localhost:8080/api/v1/search/listings?q=iphone&sort=newest&per_page=10
  - Filters via query params:
    - category_slug=phones, location_slug=tashkent, min_price=100000, max_price=10000000
    - Attribute filters: use `attrs.<key>=<value>`, e.g., `attrs.brand=Apple`, `attrs.storage=128`

Saved Searches
- Create/list: POST/GET http://localhost:8080/api/v1/saved-searches (JWT required)
  - Body example: {"title":"Cheap iPhones","query":{"params":{"q":"iphone","max_price":5000000}},"frequency":"daily"}
- Run now: POST http://localhost:8080/api/v1/saved-searches/<id>/run

Moderation
- Report listing: POST http://localhost:8080/api/v1/reports
  - Body: {"listing": <id>, "reason_code": "spam", "notes": "optional"}
- Staff queue: GET http://localhost:8080/api/v1/moderation/queue (admin only)

Uploads (S3 presign)
- Presign: POST http://localhost:8080/api/v1/uploads/presign (JWT)
  - Returns mode: "s3" with presigned POST, or "local" if not configured.
  - Env vars: MEDIA_BUCKET, MEDIA_ENDPOINT, MEDIA_ACCESS_KEY, MEDIA_SECRET_KEY, AWS_REGION

API Docs
- OpenAPI schema: GET http://localhost:8080/api/schema/
- Swagger UI: GET http://localhost:8080/api/docs/

Throttling
- OTP endpoints scoped to 5/min (configurable). Global anon/user limits also applied.

Management commands
- Initialize index: `python manage.py search_init_index`
- Reindex all listings: `python manage.py search_reindex`
- Run saved searches (dev): `python manage.py savedsearches_run`

Background workers (Celery)
- Optional: set a broker (Redis) in `.env` as `REDIS_URL=redis://localhost:6379/0`.
- Without a broker, tasks run eagerly (synchronously) by default in dev.
- With Redis running, start workers:
  - celery -A config worker -l info

Notes
- Uses SQLite by default; set POSTGRES_* envs to switch to Postgres.
- CORS is open in DEBUG. For production, set `CORS_ALLOWED_ORIGINS`.
- Time zone defaults to Asia/Tashkent; override via `TIME_ZONE`.
