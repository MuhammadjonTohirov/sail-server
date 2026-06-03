# Backend Deployment Readiness Report — sail.uz via Coolify

Task: t_0b39cf16 (Backend) · Repo: /Users/muhammad/Development/Personal/sailuz/server
Stack: Django 4.2.28 + DRF + SimpleJWT + Celery 5.6 + OpenSearch + WhiteNoise + gunicorn
Settings module: config.settings · WSGI: config.wsgi:application · ASGI: config.asgi:application

## Verdict: READY to deploy (no code blockers). Production config is sound and self-validating.

`DJANGO_DEBUG=0 manage.py check --deploy` passes with no security.W* warnings
(the only flagged item was a deliberately short dummy SECRET_KEY used for the test;
all the drf_spectacular W001/W002 messages are OpenAPI-doc noise, not deploy blockers).

----------------------------------------------------------------
## 1. Settings inspection (config/settings.py)

DEBUG          -> os.environ DJANGO_DEBUG, defaults False (safe).
SECRET_KEY     -> DJANGO_SECRET_KEY required; refuses to boot in prod if left as default.
ALLOWED_HOSTS  -> DJANGO_ALLOWED_HOSTS (comma list); refuses to boot in prod if empty.
CORS           -> CORS_ALLOWED_ORIGINS (comma list) required in prod; CORS_ALLOW_CREDENTIALS=True.
CSRF           -> CSRF_TRUSTED_ORIGINS = copy of CORS_ALLOWED_ORIGINS (good).
DATABASE       -> Postgres auto-selected when POSTGRES_HOST is set, else SQLite (dev only).
Static/media   -> WhiteNoise (CompressedManifestStaticFilesStorage), STATIC_ROOT=staticfiles,
                  MEDIA_ROOT=media (local disk).
Security (prod)-> SSL redirect, HSTS 1yr+preload+subdomains, secure+httponly session/CSRF
                  cookies, nosniff, XSS filter, X-Frame DENY — all auto-on when DEBUG=0.
Throttling     -> enabled in prod (otp 3/min, login 5/min, anon 100/hr).

## 2. Required env vars for Coolify (domain sail.uz)

REQUIRED (app refuses to boot without these in prod):
  DJANGO_DEBUG=0
  DJANGO_SECRET_KEY=<50+ char random>            # openssl rand -hex 32 or longer
  DJANGO_ALLOWED_HOSTS=sail.uz,www.sail.uz
  CORS_ALLOWED_ORIGINS=https://sail.uz,https://www.sail.uz
  TELEGRAM_BOT_TOKEN=<bot token>                 # hard-required in prod (settings line 268)
  CELERY_BROKER_URL=<redis url>  (or REDIS_URL)  # hard-required in prod (celery.py line 30)

DATABASE (Postgres — set all to leave SQLite behind):
  POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT

RECOMMENDED / optional:
  OPENSEARCH_URL, OPENSEARCH_INDEX_PREFIX, OPENSEARCH_INDEX_VERSION
  TELEGRAM_WEBHOOK_SECRET_TOKEN (openssl rand -hex 32), TELEGRAM_LOGIN_MAX_AGE
  WEB_BASE_URL=https://sail.uz   (already defaults to this)
  LANGUAGE_CODE=ru, TIME_ZONE=Asia/Tashkent
  SECURE_SSL_REDIRECT (defaults True in prod), SECURE_HSTS_SECONDS
  CHAT_MAX_ATTACHMENTS_PER_MESSAGE, CHAT_ATTACHMENT_ALLOWED_URL_PREFIXES

(Secrets reported by NAME only — no values inspected/exposed.)

## 3. Production start command

Web:    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3
        (gunicorn 25.1.0 already in requirements.txt; WSGI module confirmed.)
Build:  ./build.sh  (pip install -r requirements.txt; collectstatic --no-input; migrate)
Worker: celery -A config worker -l info        (separate Coolify service)
Beat:   celery -A config beat -l info          (separate service; daily 9:00 notifications)

Note: with ASGI also available, gunicorn+WSGI is the right default (no channels/websockets in deps).

## 4. Health endpoints (for Coolify healthcheck)

GET /healthz/        -> 200 {"status":"ok"}     <- liveness, no auth, no DB. USE THIS.
GET /api/v1/health   -> 200 {success,data:{status:ok,...}}  (DRF-wrapped, also fine)

Recommend Coolify healthcheck path = /healthz/ (cheapest, no DB dependency).

## 5. Static files / collectstatic

WhiteNoise is wired (middleware + CompressedManifestStaticFilesStorage).
build.sh already runs `collectstatic --no-input`. STATIC_ROOT=staticfiles.
No CDN/object-store dependency for static. OK.
Caveat: MEDIA is local disk (MEDIA_ROOT=media) and served via Django only in DEBUG
(urls.py line 28). In prod, user-uploaded media needs a persistent volume mounted at
./media AND a reverse-proxy/WhiteNoise rule to serve /media/ — see blockers below.

----------------------------------------------------------------
## 6. Blockers & recommended changes

BLOCKERS (must resolve before/at deploy — config, not code):
  B1. Provision Postgres + set POSTGRES_* envs. SQLite is not production-safe.
  B2. Provision Redis + set CELERY_BROKER_URL/REDIS_URL (app won't boot in prod otherwise).
  B3. Set TELEGRAM_BOT_TOKEN (app won't boot in prod otherwise).
  B4. Media persistence: /media/ is only served by Django in DEBUG. In prod either
      (a) mount a persistent volume at ./media and add a WhiteNoise/Nginx rule for /media/, or
      (b) move uploads to S3/object storage. Without this, uploads break or are ephemeral.

NON-BLOCKING recommendations (propose as follow-up card, do NOT implement without PM approval):
  R1. CSRF_TRUSTED_ORIGINS auto-appends 'https://*.onrender.com' (settings lines 156-157)
      — leftover from the old Render host. Harmless but should be removed for sail.uz.
  R2. Duplicate production-security block (lines 162-174 AND 301-311). The second block
      hardcodes SECURE_SSL_REDIRECT=True, silently overriding the env-configurable value
      from line 164. De-duplicate so SECURE_SSL_REDIRECT stays env-controllable.
  R3. No Dockerfile / nixpacks / Procfile present. Coolify can use Nixpacks auto-detect
      (Django + gunicorn) or a Dockerfile — DevOps to decide build strategy in t_510a75f9.
  R4. Add a Postgres-aware readiness probe (current /healthz/ is liveness-only). Optional.
  R5. `uploads` app and its URLs are commented out (settings line 46, urls line 19) —
      confirm with PM whether S3 uploads are in scope for v1.

## 7. Handoff to DevOps (t_c38a5e6e gate)

No backend code changes are required to go live; remaining work is env/infra provisioning
(B1-B4) plus build-strategy choice (R3). R1/R2 are quality cleanups — recommend a separate
follow-up card pending PM approval before any edit (task rules forbid implementing here).
