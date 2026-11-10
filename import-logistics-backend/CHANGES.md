# Production-hardening changes

Each item says what was wrong, what changed, and how it was verified.
"Run here" = executed in the sandbox. "Compiled only" = syntax-checked but needs your
environment (PostgreSQL, Redis, installed packages) to run.

## Critical fixes
| # | Problem | Fix | Verification |
|---|---------|-----|--------------|
| 1 | `transaction()` called `session.begin()`, which fails ("transaction already begun") after any earlier query, so most write paths would error | `app/core/database.py`: helper detects an open transaction and commits/rolls back it | Compiled only; covered by the PostgreSQL integration test |
| 2 | Alembic migration created 6 tables, no `tenant_id`, no `organizations`: it could not produce the schema the models need | Stale file moved to `alembic/obsolete_do_not_use/`; `scripts/generate_baseline_migration.sh` regenerates and verifies a real baseline; CI runs `alembic upgrade head` + `alembic check`; `/ready` fails if the schema is missing | **You must run the script once** (needs Docker) |
| 3 | Money stored and calculated as float; allocated shares did not sum to the total | `NUMERIC` columns, `Decimal` maths, `app/utils/money.py` with largest-remainder allocation, Pydantic `Money/Rate/Weight` types | **Run here: 16 tests pass** |
| 4 | Idempotency: user id never set (all users shared an "anon" namespace), check-then-act race, no body check, no ownership on completion | Rewritten as pure-ASGI middleware + store (`app/core/idempotency.py`): atomic claim, per-user key from verified JWT, request fingerprint, 409/422, release on failure | **Run here: 9 state-machine tests pass**; HTTP tests written, need your environment |
| 5 | Production Redis had `requirepass` but `REDIS_URL` had no password (app could not connect); one Redis with `allkeys-lru` held broker, locks, idempotency keys and revoked tokens | Two Redis instances: durable `noeviction` state + disposable LRU cache; URLs include the password; shared per-loop clients | Compiled only |
| 6 | Nothing ran migrations on deploy | One-shot `migrate` service; `web` waits for it | Compiled only (YAML edited by script, review once) |
| 7 | CORS added first = innermost, so 409/422/503 and replays had no CORS headers and no logging | Middleware order fixed in `main.py` | Compiled only |
| 8 | `scripts/init_db.py` and `create_admin.py` imported names that do not exist and ignored `tenant_id` | Rewritten against real models; creates the organisation and superuser | Compiled only |

## Second round (upgrades)
| # | Problem / gap | Change | Verification |
|---|---------------|--------|--------------|
| 9 | **Cross-tenant user access:** any tenant admin could list, read, edit (including role) and deactivate users of EVERY organisation (no tenant filter in `routers/users.py`) | All user endpoints filtered by the caller's `tenant_id`; other tenants' users return 404 | Compiled only; covered by `scripts/smoke_test.py` |
| 10 | `audit_logs` table existed but nothing wrote to it | Audit trail: `AuditService` stages rows in the same transaction as each change (containers, expenses, items, sales, allocation, user changes, organisation creation); `GET /audit-logs/` for admins; passwords/tokens redacted; IP from `X-Real-IP` only when `TRUST_PROXY_HEADERS=true` | **Run here: 6 tests** for diff/redaction/JSON-safety; rest compiled only |
| 11 | No way to create a new tenant except a script | `POST /organizations/` (platform administrator only) creates organisation + first admin atomically; `GET /organizations/me` | Compiled only; smoke test |
| 12 | No single check that the whole system works | `scripts/smoke_test.py`: ~40 end-to-end checks (roles, tenant isolation, idempotency replay/mismatch, exact allocation, audit trail) | Compiled only; **you run it** |
| 13 | CI did not exercise the real stack | `e2e` job boots Docker Compose and runs the smoke test | YAML parsed; compose files validated by script; first CI run may need small tweaks |

## Third round: full tenant-isolation audit and known limits
**The app could not have started.** `routers/reports.py` and `schemas/__init__.py` imported `app.schemas.reports`, but the file was named `report.py` (ImportError at startup). `py_compile` cannot catch this, so two static checkers were added (`scripts/check_imports.py`, `scripts/check_names.py`; no packages needed; both now run in CI). They found exactly that bug and nothing else.

| # | Problem | Fix | Verification |
|---|---------|-----|--------------|
| 14 | **Tracking:** `POST /tracking/{id}/update` let ANY user (even a viewer) queue updates for ANY tenant's container; the Celery call also passed `queue` as a task argument, so it always failed | Permission check first (clerk+, same tenant, clerks own only); `queue=` as an `apply_async` option; tenant id passed to and re-checked by the worker | Static checks; smoke test |
| 15 | **Pricing:** market-price scraping and price records could be started for / attached to another tenant's item; "last sold" read other tenants' sale prices | Every pricing endpoint resolves the item through a tenant- and owner-scoped lookup before acting; worker re-checks tenant; sales query is tenant-scoped | Smoke test |
| 16 | **Files:** `DELETE /files/{key}` allowed path traversal (could delete any file the process could reach) and any user could delete any file; uploads read fully into memory; extension taken from the client filename; files publicly served by Nginx | Strict key pattern `<tenant>/<user>/<random>.<ext>`; tenant/owner checks; chunked size-limited read; extension from detected type; authenticated download (signed URL for S3/R2); boto3 calls moved off the event loop; Nginx no longer exposes `/uploads/` or `/metrics` | Smoke test (traversal, cross-tenant) |
| 17 | **Reports:** dashboard low-stock count included every tenant's warehouses; container report joined expenses and items together, multiplying totals; profit subtracted the cost of UNSOLD stock from sales revenue | Tenant-scoped join; expenses and items aggregated separately; profit = revenue - cost of SOLD items, unsold stock shown as inventory value, unallocated expenses shown | **Run here: 5 tests** for the maths; smoke test checks exact numbers |
| 18 | **Sales:** a sale could reference another organisation's customer; clerks could edit/delete expenses of containers they do not own | Customer must belong to the tenant (422); expense changes use the container's visibility rule | Smoke test |
| 19 | Customers had no API although sales reference them | Tenant-scoped CRUD with audit (`/customers`) | Static checks; smoke test |
| 20 | Nobody consumed Celery's `default` queue | Added to a worker in both compose files | YAML validated |

### Known limits addressed
| Limit | Change |
|-------|--------|
| Pricing "simple average" | New engine (`app/utils/pricing_math.py`, `docs/PRICING.md`): USD-normalised comparables (the old code averaged NGN, EUR and CZK as one unit), outlier removal, weighted median, recency and source weights, trust-weighted blend with cost-plus, minimum-margin floor, price band, confidence, warnings and `GET /pricing/accuracy`. **Run here: 14 tests** |
| Idempotency relied only on Redis | PostgreSQL store is now the default (`idempotency_keys`, UNIQUE key, `INSERT ... ON CONFLICT DO NOTHING`), nightly purge task. Redis variant kept behind `IDEMPOTENCY_BACKEND=redis`. Remaining window documented |
| Reports converted money to float | Report amounts are `Decimal` end to end (JSON still writes numbers) |
| Customers/other unused tables | Customers implemented. Suppliers, orders, payments, shipments, warehouses and customs remain schema-only on purpose |
| Tracking only ever used mock data | **Cannot be fixed without a real carrier key.** The manual trigger and permissions are fixed; capture a real response and add it as a test fixture |
| Flutter client | **Not changed** (no Dart toolchain here). It must send `Idempotency-Key`, use refresh tokens, and send the `Authorization` header when loading images from `/api/v1/files/...` |

## Fourth round: review feedback (five points checked against the code)
| # | Observation | Verdict | Change |
|---|-------------|---------|--------|
| 21 | Dashboard totals were organisation-wide, unlike the container and item lists | **Correct.** The item and category reports already scoped clerks; the dashboard did not, and `/reports/demand` is precomputed organisation-wide | Policy decided and enforced: a clerk sees only their own containers and the totals built from them; organisation-wide stock alerts show 0 for clerks; `/reports/demand` returns 403 for clerks. Also: items of soft-deleted containers no longer count in the dashboard, item report or category report |
| 22 | Refresh-token check and revocation were separate steps, so two simultaneous refreshes could both succeed | **Correct** | Atomic one-time consume (`SET NX EX`, `app/core/token_rotation.py`); losers get 401 and a reuse warning is logged. **Run here: 4 tests** including 25 simultaneous attempts |
| 23 | `.env.example` listed `localhost:3000`, Vite uses 5173 | **Partly correct.** The bundled setup is same-origin (Vite proxy / Nginx), so CORS is not used; but the example was misleading and the CORS config would have blocked the new `X-Auth-Mode` header if the frontend were ever hosted separately | Example now lists 5173 with an explanation; `X-Auth-Mode` added to allowed headers; `Retry-After`/`Idempotent-Replayed` exposed; production rejects non-https origins; wildcard is impossible (typed as URLs). Documented that the SameSite=Strict cookie requires the frontend and API to share a site |
| 24 | Logout documented as public but handler required authentication; content types unclear | **Correct, and worse than a doc mismatch:** a user whose access token had expired could not sign out at all (the refresh cookie stayed valid) | Logout is now genuinely public: it revokes whichever tokens the caller presents and clears the cookie. Docs now state the credential and content type of each auth endpoint |
| 25 | Some pricing schemas used float | **Partly correct.** Recommendations were estimates, but the price a client submits (`PriceRecordCreate.price`) and every money field in the pricing response were float, and `price_records.price` was a float column | Price record column is `NUMERIC(18,4)`; request and response money fields use the `Money` types; scraped prices are converted to exact decimals and rejected if not positive. Ratios and scores (confidence, margin, MAPE) stay numbers |

New smoke checks cover clerk visibility, logout without an access token, and 8 simultaneous refreshes (exactly one must succeed).

## Fifth round: the migration (three separate reasons it could never have run)
| # | Problem | Fix | Verification |
|---|---------|-----|--------------|
| 26 | **Verified on real PostgreSQL 16.** `alembic/versions/` was empty (the old 6-table migration was removed earlier because it did not match the models) | `001_baseline.py` created: 26 tables, 307 columns, 100 indexes, 17 enum types, check/unique constraints, tables in foreign-key order, downgrade drops tables AND enum types | `scripts/check_migration.py` runs it against stand-in `sa`/`op` modules and compares with the models. **Passes; and was shown to fail** for 4 planted mistakes (missing column, wrong type, undropped enum, missing primary key). **Not yet run on real PostgreSQL** |
| 27 | `alembic/env.py` set a synchronous `postgresql://` URL, then built an ASYNC engine from it, which fails immediately | Migrations use a plain synchronous engine (psycopg2) and prefer the direct `ALEMBIC_DATABASE_URL` over PgBouncer | Read and reasoned; applied when you run `verify_migrations.sh` |
| 28 | `alembic.ini` lived inside `alembic/`, not at the project root, so `alembic upgrade head` (as Compose runs it from `/app`) found no config | Moved to the project root, `script_location = %(here)s/alembic` | ini parses; applied when you run `verify_migrations.sh` |
| 29 | CI checked only `alembic upgrade head` + `check` | CI now also runs `check_migration.py` (no database), downgrade to base, and upgrade again | YAML valid |

`scripts/generate_baseline_migration.sh` was replaced by `scripts/verify_migrations.sh`.

## Other fixes
* **Public registration was open to everyone** (always into tenant 1, and the `REGISTRATION_OPEN` flag mentioned in its docstring did not exist). It is now a real setting, default `false` (403 when off).
* `SECRET_KEY` has no random default in production; production start-up rejects weak keys, default DB credentials and `DEBUG=true`.
* PgBouncer + asyncpg: prepared statements disabled via `DATABASE_PGBOUNCER`.
* FX: Decimal rates, no silent hard-coded fallback in production (HTTP 503 instead), network call moved out of open transactions.
* Cost allocation: tenant check, row lock (`FOR UPDATE`), method validation, business errors map to HTTP 422 (were 200 with an error body).
* Carrier container number unique per tenant (was globally unique across tenants).
* Check constraints on positive amounts, prices and weights.
* Tracking: mock data only outside production.
* `/ready`: no exception text in responses; checks migrated schema; Celery and cache are informational (a worker restart no longer takes the API out of rotation); Celery ping no longer blocks the event loop.
* Token blacklist stores a SHA-256 hash, not the raw token.
* README removed the documented default login (`admin / changethis`).
* `requirements.txt` is production-only; test tools moved to `requirements-dev.txt`.
* CI workflow added.

## Not done / needs you
0. **Flutter token refresh:** the client stores only the access token and just clears it on 401. Do not shorten `ACCESS_TOKEN_EXPIRE_MINUTES` (24 h today) until the client uses refresh tokens.
1. ~~Verify the migration~~ **Done (2026-10-25):** `bash scripts/verify_migrations.sh` passed on PostgreSQL 16 (upgrade, check, downgrade, upgrade, check). Its first real run found duplicate `id` columns, which the offline checker could not see; the checker now detects duplicates.
2. Run the full test suite once in your environment (`pytest`, then with `TEST_DATABASE_URL`).
3. Smoke-test with `docker compose up`, create an expense and an item, run `allocate-costs`.
4. Verify carrier tracking with a real `MSC_API_KEY`.
5. Pin the PgBouncer image version; add a database idempotency table if you add real payments.
6. Pricing/report aggregates still convert to float at the API edge.

## Documentation added
`docs/API.md` (53 endpoints, generated from the routers), `docs/DATABASE.md` (26 tables, generated from the models), `docs/INTEGRATIONS.md`, `docs/SETUP.md`, `docs/PRICING.md`, `docs/README.md` (index). Old documents moved to `docs/archive/` because they were not generated from the code.

## Frontend (new, `frontend/`)
React 19 + strict TypeScript + Vite + TanStack Query + React Router + react-hook-form/zod + Tailwind 4 + Radix. Built: sign-in with
httpOnly-cookie sessions and cross-tab refresh, role-aware shell, dashboard, containers (list, create, edit, seal, delete, cost
allocation), items and expenses (add, edit, delete, sell), settings, dark mode. Types were compared field-by-field with the real
`openapi.json`: 3 differences found and fixed (`total_*` on container detail, optional `allocation_method`, `owner_id` filter), and
`src/api/contract.ts` now fails the build if the API drifts. **Never run in a browser**: see `frontend/README.md` "Status".
Not built yet: customers, pricing, reports/charts, admin screens, Dockerfile/Nginx.

### Frontend: customers and pricing
Customers (list, search, add, edit, delete, picker on the sale form) and the pricing screen (recommended price, range,
confidence bar, warnings, "why this price", market listings with refresh, accuracy card for managers). New types were
compared field by field with `openapi.json`: all matched.
**Backend change found while building it:** `POST /pricing/generate` and `POST /pricing/refresh-market` were open to any
signed-in user, including read-only viewers, although generating SAVES the recommended price on the item and refreshing starts
scraping external sites. Both now require clerk or higher (docs updated, 2 smoke checks added: 403 for a viewer).

### Frontend: administration, and four backend fixes found while building it
Team management (add, edit role/status/password, deactivate), the audit log (filters, expandable "what changed" with old and new
values) and organisation creation for platform administrators, with role-aware navigation and a clear "no access" page.
The new types match `openapi.json` field for field. **Re-export the spec** (`npm run api:export`) because these backend
changes alter it slightly (password length, the `PUT /users/me` request type).

Backend fixes found while reading the user endpoints:
| Problem | Fix |
|---------|-----|
| An admin could demote or deactivate **themselves**, possibly leaving the organisation with no admin | Refused (409). Another admin can still do it, so one always remains |
| Renaming a user to an existing email/username crashed with a 500 | Clean `409` with a message |
| Admin-created users could have a one-character password (organisation admins already needed 12) | 12 to 128 characters everywhere |
| `PUT /users/me` was documented as accepting `role` and `is_active` (the handler ignored them, so no escalation, but the contract was misleading) | Request type is now `UserUpdate`; smoke test confirms a viewer cannot promote themselves |

Smoke test: 5 new checks (weak password, self-demotion, self-deactivation, duplicate username, no self-promotion).

### Frontend: reports and the production image
**Reports** (`/reports`): profit by category, by container (managers), by item with filters, and demand (not for clerks), each
with a bar chart AND a table of the same numbers; a warning when a container still has expenses that are not allocated.
Types compared with `openapi.json`: all four report schemas match.

**Production image.** Two defects in the existing setup were found and fixed:
| Problem | Fix |
|---------|-----|
| `docker-compose.prod.yml` builds the nginx service from `docker/nginx/Dockerfile`, **which did not exist**: `docker compose build` would fail before anything started | Dockerfile written; it also builds the frontend and bundles `nginx.conf` |
| Nginx answered rate-limited requests with 503 (looks like an outage) | `limit_req_status 429`; API limit raised from 100 to 300 requests a minute (burst 60) because a single-page app makes several calls per screen |

Also: single-page-app routing with a year-long cache for hashed assets and `no-cache` for `index.html`; a strict
Content-Security-Policy (scripts from our own origin only, which is why the theme script moved out of `index.html`); security
headers in one shared snippet (nginx does not inherit `add_header` into locations that set their own); uploads are no longer
served statically; a root `.dockerignore`; CI job `images` builds the image.

A unit test caught a real bug in the chart-axis helper (`$950.0` instead of `$950`); fixed.
**Never run:** the nginx config has not been loaded by nginx and the image has never been built.
