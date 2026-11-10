# Integration Guide

Everything Importer talks to outside its own database. For each integration: what it is used for,
how to enable it, how failures are handled, and how to test it.
Status legend: **Verified** = exercised in tests or code-reviewed end to end; **Unverified** = implemented but never run against the real service.

| Integration | Purpose | Status | Needs |
|-------------|---------|--------|-------|
| Exchange-rate API | Convert expenses and purchase prices to USD | Implemented, parsing unit-testable; live call unverified | Internet; optional key |
| Carrier tracking (MSC) | Shipment status updates | **Unverified** (mock data in development) | `MSC_API_KEY` |
| Market-price scraping | Price benchmarks for pricing recommendations | Implemented, fragile by nature | `SCRAPING_ENABLED`, Playwright for two sources |
| Email (SMTP / SendGrid / Mailgun) | Tracking notifications | Implemented, **unverified** | Provider credentials |
| Object storage (local / S3 / R2) | Item photos and documents | Local verified by design; S3/R2 **unverified** | Bucket + keys |
| Sentry, Prometheus, OpenTelemetry | Errors, metrics, traces | Wired in | DSN / endpoint |

---

## 1. Exchange rates

* **Used by:** expense and item creation/update (`FXService.get_fx_rate`) and the hourly `update_fx_rates` task, which stores rates in `exchange_rate_history`.
* **Flow:** cache Redis (1 h) -> live API (`EXCHANGERATE_API_URL` + base currency) -> fallback.
* **Currencies:** USD, EUR, CZK, NGN.
* **Failure policy (important):** outside production a small hard-coded table is used with a loud warning. In **production** the fallback is off:
  the API returns `503` with `Retry-After` rather than booking money at a made-up rate. Set `FX_ALLOW_FALLBACK=true` only if you accept stale rates.
* **Precision:** rates are parsed as `Decimal` and stored as `NUMERIC(18,8)`.
* **Test it:** `docker compose exec web python -c "import asyncio; from app.services.fx_service import FXService; print(asyncio.run(FXService().get_fx_rate('EUR','USD')))"`.
* **Upgrade path:** use a paid provider with an SLA, store the rate and its source/timestamp on each expense (already stored as `fx_rate_to_usd`), and alert when the hourly task fails.

## 2. Carrier tracking (MSC)

* **Used by:** `TrackingService`, hourly `update_all_tracking` Celery task, and `POST /tracking/{id}/update`.
* **Enable:** set `MSC_API_KEY` (and `MSC_API_URL` if different). Each container needs `msc_container_number`.
* **Status mapping:** provider events are mapped to `tracking_records.status` (`booked`, `gate_in`, `loaded`, `departed`, `in_transit`, `arrived`, `discharged`, `gate_out`, `delivered`, `unknown`). Unknown events map to `unknown` and are never treated as success.
* **Without a key:** development returns deterministic **mock** data (logged as a warning); **production returns "unavailable"** instead of fake data.
* **Unverified:** the real request/response shape has not been tested against the live carrier API. Treat the first real run as integration testing: capture a real response, add it as a test fixture, and adjust the mapping.
* **Rate limit:** 20 requests/minute on tracking endpoints.

## 3. Market-price scraping

* **Used by:** `fetch_market_prices` task (`POST /pricing/refresh-market/{item_id}`); results are saved as `price_records`.
* **Sources:** `jiji`, `ebay`, `bazos_cz` (HTTP + BeautifulSoup) and `mobile_de`, `autoscout24` (Playwright browser, heavier).
* **Switch:** `SCRAPING_ENABLED=false` disables all scraping; set `SCRAPING_USER_AGENT` to identify your bot honestly.
* **Failure behaviour:** a failing source returns no prices and is logged; other sources still run.
* **Risks you must own:** check each site's terms of service and robots.txt, respect rate limits, and expect CSS selectors to break when sites change. Scraped prices are estimates, which is why they are stored as floats with a confidence score.
* **Upgrade path:** prefer official APIs (eBay Browse API) where available; add a per-source success metric and alert when a source returns nothing for days.

## 4. Email notifications

* **Used by:** `send_tracking_notifications` (hourly) and `NotificationService`.
* **Select provider:** `EMAIL_PROVIDER=smtp|sendgrid|mailgun`.

| Provider | Settings |
|----------|----------|
| SMTP | `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS` |
| SendGrid | `SENDGRID_API_KEY` |
| Mailgun | `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` |

* **Add a provider:** implement `EmailProvider.send()` in `app/services/notification_service.py` and register it in `_get_provider()`.
* **Test it:** point `SMTP_HOST` at a local MailHog/Mailpit container and trigger a tracking update.
* **Production notes:** configure SPF/DKIM for the sending domain; notifications are best-effort (a failed email is logged, not retried indefinitely).

## 5. File storage

* **Used by:** `POST /files/upload`, `DELETE /files/{key}`.
* **Select backend:** `STORAGE_BACKEND=local|s3|r2`.

| Backend | Settings |
|---------|----------|
| `local` | `UPLOAD_DIR` (default `uploads`; mount a persistent volume) |
| `s3` | `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` |
| `r2` (Cloudflare) | `R2_ACCOUNT_ID`, `R2_BUCKET` plus the access keys |

* **Safety checks:** max 10 MB (read in chunks); allowed types JPEG, PNG, WebP, PDF; the real type is detected from the file content and the extension comes from the detected type, never from the client's filename.
* **Access control:** keys are `<tenant>/<user>/<random>.<ext>` and must match a strict pattern (so path traversal is impossible). Files are NOT served statically; `GET /api/v1/files/{key}` checks the tenant (local files are streamed, S3/R2 files get a 5-minute signed URL). Nginx no longer exposes `/uploads/` or `/metrics`.
* **Production:** use `s3` or `r2` (the container filesystem is not durable), keep the bucket private, and serve files through signed URLs.

## 6. Observability

| Tool | How to enable | What you get |
|------|---------------|--------------|
| Prometheus + Grafana | Included in the compose files; scrape `/metrics` | Request rate, latency, errors |
| Sentry | `SENTRY_DSN` | Exceptions with request context (PII sending is off) |
| OpenTelemetry | `OTEL_EXPORTER_OTLP_ENDPOINT` | Distributed traces |
| Flower | Compose service, port 5555 (password required) | Celery queues and task status |
| Logs | `LOG_LEVEL`; JSON in production, with a request ID per request | Searchable, correlated logs |

## 7. Background schedule (Celery beat)

| Task | Queue | Schedule |
|------|-------|----------|
| `update_fx_rates` | `fx_queue` | hourly |
| `update_all_tracking` | `tracking_queue` | hourly |
| `send_tracking_notifications` | `notification_queue` | hourly |
| `refresh_demand_analytics` | `pricing_queue` | every 6 hours |
| `fetch_market_prices` | `scraping_queue` | on demand |

Run **one** beat instance only. Tasks use `acks_late`, so they must be safe to run twice.

## 8. Flutter client

The Flutter app in `../lib` talks to `/api/v1` (base URL in `lib/core/constants/api_constants.dart`, default `http://localhost:8000/api/v1`; use `http://10.0.2.2:8000/api/v1` from an Android emulator).
Client rules: send `Idempotency-Key` on every create, store tokens in secure storage, refresh on `401` once, and treat `409`/`503` with `Retry-After` as "try again shortly".
Amounts arrive as JSON numbers; format them for display with 2 decimals but never do accounting math in floating point on the client.

## 9. Adding a new integration (checklist)

1. Put credentials in settings (`app/core/config.py`) and `.env.example`; never hard-code them.
2. Wrap the external call in a service with a timeout, error classification (temporary vs permanent) and logging that never prints secrets.
3. Run slow or flaky calls in a Celery task on its own queue; make the task safe to repeat.
4. Decide the failure policy explicitly (fail loudly vs degrade) and document it here.
5. Add a test with a recorded response fixture; never test against the live service in CI.
6. Add a metric and an alert for the failure case.
