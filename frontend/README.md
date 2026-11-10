# Importer - Web Frontend

React 19, TypeScript (strict), Vite, TanStack Query, React Router, react-hook-form + zod, Tailwind CSS v4, Radix UI.
It is a single-page app that talks to the Importer API through the same origin (`/api`), so there is no CORS.

## Quick start

```bash
cd frontend
cp .env.example .env
npm install
npm run dev            # http://localhost:5173  (proxies /api to VITE_API_PROXY, default http://localhost:8000)
```

| Command | What it does |
|---------|--------------|
| `npm run typecheck` | TypeScript, strict |
| `npm run lint` | ESLint, including the architecture boundary rules |
| `npm test` | Unit and component tests (Vitest) |
| `npm run test:e2e` | Browser tests against a RUNNING backend (Playwright) |
| `npm run build` | Typecheck, then production bundle in `dist/` |
| `npm run api:export` then `npm run check:contract` | Export the backend's OpenAPI spec and prove the hand-written types still match it |

## Status

| Area | State |
|------|-------|
| Sign in / sign out, session refresh across tabs, role-aware navigation | built |
| Dashboard (organisation, or own containers for clerks) | built |
| Containers: list with filters, create, edit, seal, delete, cost allocation | built |
| Items and expenses inside a container: add, edit, delete, mark sold | built |
| Items list with search and filters, settings, dark mode | built |
| Customers: list, search, add, edit, delete; pick a customer when recording a sale | built |
| Pricing recommendation per item: price, range, confidence, warnings, "why this price", market listings, refresh; accuracy card for managers | built |
| Reports with charts: profit by category, by container (managers), by item with filters, demand (not for clerks); every chart has a table with the same numbers | built |
| Admin: team members (add, edit role, deactivate), audit log with filters and "what changed", create organisations (platform admin) | built |
| Admin menu and pages hidden from people without access (the server still enforces it) | built |
| Production image (`import-logistics-backend/docker/nginx/Dockerfile`): builds this app and serves it behind Nginx with TLS, a strict Content-Security-Policy and SPA routing | written, never built |
| CI job (import check, contract check, typecheck, lint, tests, build) | written, never run |

**Never run yet.** The code has passed: a syntax check of every file, an import checker (every `@/` and relative import
resolves, every named import is exported), strict TypeScript on the non-React modules, and 40+ unit tests of the money,
permission and API-client logic. It has NOT been compiled against the real React/Tanstack types, rendered in a browser,
or linted, because those need `npm install`. Your first `npm run typecheck` and `npm run lint` are the real test:
send the errors and they will be fixed.

First run, in this order:

```bash
cd frontend && cp .env.example .env && npm install
npm run api:generate && npm run check:contract   # the committed openapi.json is the real API; this proves the types match
npm run typecheck && npm run lint && npm test
npm run dev                                       # backend must be running on :8000
```

## Project structure

```
frontend/
  e2e/                     Playwright tests (real browser, real backend)
  public/                  static files (favicon)
  scripts/                 check-imports.mjs (every import resolves)
  src/
    main.tsx               entry: mounts <App/>
    App.tsx                providers: QueryClient, Auth, Toasts, Router
    router.tsx             all routes, lazy-loaded per feature
    index.css              Tailwind + light/dark design tokens
    lib/                   pure helpers, no React, no API: money, permissions, utils, idempotency
    api/                   HTTP only: client (refresh, idempotency), errors, types, endpoints, queryKeys
    auth/                  AuthProvider, useAuth, RequireAuth, RequireRole
    components/
      ui/                  design-system primitives: Button, Input, Dialog, Table, Tabs, Badge, Toast ...
      layout/              AppShell, Sidebar, Topbar, ThemeToggle
      shared/              PageHeader, EmptyState, ErrorState, ConfirmDialog, Pagination, MoneyText, FormField
    features/              one folder per business area
      auth/                login page
      dashboard/           KPI cards, charts
      containers/          list, detail, create/edit, seal, allocate costs, tracking
      items/               list, form, mark sold, opens the pricing dialog
      expenses/            expense table + form (used inside a container)
      customers/           list, form, customer picker for sales
      pricing/             price recommendation dialog, accuracy card
      reports/             profit by category / container / item, demand
      admin/               team, audit log, organisations
      settings/            profile, theme, sign out
    test/                  test setup and helpers
```

Every feature folder has the same shape:

```
features/containers/
  index.ts                 the ONLY file other features may import
  api.ts                   React Query hooks (useContainers, useCreateContainer ...)
  schemas.ts               zod schemas for its forms
  components/              pieces used by its pages
  pages/                   route components (ContainerListPage, ContainerDetailPage)
```

## Layers (enforced by ESLint)

```
lib  <-  api  <-  auth  <-  components  <-  features  <-  router/App
```

A layer may import only from layers to its left. `lib` knows nothing about React or the API;
`components` never import a feature; a feature uses another feature only through its `index.ts`.
Inside a feature, use relative imports.

## Rules we follow

1. **Server state lives in React Query.** No Redux/Zustand. Filters and pagination live in the URL, so pages can be bookmarked and the back button works.
2. **Money is a string.** Forms hold decimal strings, requests send strings, sums use scaled integers (`lib/money.ts`). Numbers from the API are formatted for display only.
3. **Every create has an `Idempotency-Key`**, generated once per form open and reused on retry, so a retry can never create a duplicate.
4. **Permissions:** `can(user, 'container.delete')` hides what a user cannot do. The server is the authority; this is convenience. Clerks see only their own containers and the totals built from them; organisation-wide analytics are hidden from them (`canViewOrganisationAnalytics`).
5. **Tokens:** the access token lives in memory; the refresh token is an httpOnly cookie. The client refreshes once on 401 and shares that refresh across requests and browser tabs.
6. **Every screen has four states:** loading (skeleton), empty, error (with retry), data.
7. **Accessibility:** use the primitives in `components/ui` (Radix underneath), label every input, keep focus handling in dialogs.
8. **Tests sit next to the code** (`thing.test.ts`). Pure logic gets unit tests; screens get component tests; the main journeys get e2e tests.
9. **API contract:** hand-written types in `api/types.ts` are checked against the generated OpenAPI types (`npm run check:contract`) in CI, so a backend change fails the frontend build instead of a user.

## Deployment

`npm run build` produces static files in `dist/`. In production Nginx serves them and proxies `/api` to the backend on the
same origin. The Nginx image is built from the repository root: `docker compose -f import-logistics-backend/docker/docker-compose.prod.yml build nginx` (see `docs/SETUP.md`).
