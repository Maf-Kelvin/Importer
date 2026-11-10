# Database Reference

PostgreSQL 16. All timestamps are `TIMESTAMPTZ` (timezone-aware UTC). All tables include `id` (BIGSERIAL PK), `created_at`, and `updated_at`. Tables marked **soft-delete** also have `deleted_at`.

---

## Entity Relationship Overview

```
organizations (tenant root)
     │
     ├── users
     │    └── audit_logs
     │    └── notifications
     │    └── orders (created_by)
     │    └── price_records (user_id)
     │
     ├── containers  [soft-delete]
     │    ├── container_expenses
     │    ├── items  [soft-delete]
     │    │    ├── price_records
     │    │    ├── warehouse_inventory
     │    │    │    └── inventory_movements
     │    │    └── sales
     │    ├── tracking_records
     │    ├── shipments
     │    │    └── transport_legs
     │    ├── transport_legs
     │    ├── documents
     │    ├── customs_clearance
     │    └── payments
     │
     ├── warehouses
     │    └── warehouse_inventory
     │
     ├── customers  [soft-delete]
     │    └── orders
     │         ├── order_items
     │         └── payments
     │
     ├── suppliers  [soft-delete]
     │
     ├── exchange_rate_history
     ├── demand_analytics
     └── ports  (global, no tenant)
```

---

## Table Reference

### organizations
Multi-tenant root. Every other table references this via `tenant_id`.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| name | VARCHAR(255) | |
| slug | VARCHAR(100) UNIQUE | URL-safe identifier |
| description | TEXT | |
| is_active | BOOLEAN | |
| plan | VARCHAR(50) | starter / professional / enterprise |
| max_users | INTEGER | Plan limit |
| max_containers | INTEGER | Plan limit |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `slug` (unique)

---

### users

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| email | VARCHAR(255) UNIQUE | |
| username | VARCHAR(100) UNIQUE | |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| hashed_password | VARCHAR(255) | bcrypt |
| is_active | BOOLEAN | |
| is_superuser | BOOLEAN | |
| role | ENUM | admin / manager / clerk / viewer |
| last_login | TIMESTAMPTZ | Updated on every successful login |
| failed_login_attempts | INTEGER | Reset on successful login |
| locked_until | TIMESTAMPTZ | Set after MAX_LOGIN_ATTEMPTS failures |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `email` (unique), `username` (unique), `(tenant_id, email)` composite

---

### containers *(soft-delete)*

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| owner_id | BIGINT FK → users | |
| name | VARCHAR(255) | |
| container_type | ENUM | 20ft / 40ft |
| msc_container_number | VARCHAR(50) UNIQUE | MSC tracking number |
| allocation_method | ENUM | weight_based / value_based |
| allocation_override | BOOLEAN | |
| is_sealed | BOOLEAN | No new items after seal |
| is_shipped | BOOLEAN | |
| notes | TEXT | |
| extra_data | JSONB | Extensible metadata, notification settings |
| deleted_at | TIMESTAMPTZ | Soft delete |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `msc_container_number` (unique), `(tenant_id, owner_id)`, `(tenant_id, is_shipped)`

---

### container_expenses

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | |
| expense_type | ENUM | loading_fee / shipping_fee / clearing_fee / offloading_fee / warehouse_fee / security_fee / extra_fee |
| amount | NUMERIC | In original currency |
| currency | CHAR(3) | ISO 4217 |
| description | TEXT | |
| fx_rate_to_usd | NUMERIC | Rate at time of entry |
| amount_usd | NUMERIC | Converted amount |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `container_id`, `tenant_id`

---

### items *(soft-delete)*

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | |
| name | VARCHAR(255) | |
| description | TEXT | |
| category | ENUM | electronics / vehicles / engines / appliances / food_items / laptops / other |
| condition | ENUM | new / tokunbo / used |
| purchase_price | NUMERIC | In original currency |
| purchase_currency | CHAR(3) | |
| purchase_date | DATE | Fixed from String |
| fx_rate_to_usd | NUMERIC | |
| purchase_price_usd | NUMERIC | |
| weight | NUMERIC | kg |
| volume | NUMERIC | m³ (optional) |
| allocated_cost | NUMERIC | Set by cost allocation |
| landed_cost | NUMERIC | purchase_price_usd + allocated_cost |
| recommended_price | NUMERIC | Set by pricing engine |
| selling_price | NUMERIC | Actual sold price |
| sold | BOOLEAN | |
| sold_date | DATE | Fixed from String |
| extra_data | JSONB | |
| deleted_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `(tenant_id, category)`, `(tenant_id, sold)`, `container_id`

---

### price_records

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| item_id | BIGINT FK → items | |
| user_id | BIGINT FK → users | |
| method | ENUM | cost_based / market_based / last_sold |
| source | ENUM | jiji / ebay / mobile_de / autoscout24 / bazos_cz |
| price | NUMERIC | |
| currency | CHAR(3) | |
| source_url | TEXT | |
| source_data | JSONB | Raw scraper response |
| confidence_score | NUMERIC | 0.0 – 1.0 |
| margin_percentage | NUMERIC | For cost-based records |
| notes | TEXT | |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `(item_id, is_active)`, `tenant_id`

---

### tracking_records

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | |
| status | ENUM | booked / gate_in / loaded / departed / in_transit / arrived / discharged / gate_out / delivered / unknown |
| location | VARCHAR(255) | |
| vessel_name | VARCHAR(255) | |
| voyage_number | VARCHAR(100) | |
| status_date | TIMESTAMPTZ | |
| estimated_arrival | TIMESTAMPTZ | |
| actual_arrival | TIMESTAMPTZ | |
| raw_data | JSONB | Full MSC API response |
| notification_sent | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `(container_id, status)` composite, `tenant_id`

---

### shipments

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | |
| shipment_number | VARCHAR(100) UNIQUE | |
| carrier | VARCHAR(100) | |
| tracking_number | VARCHAR(100) | |
| origin_port | VARCHAR(100) | |
| destination_port | VARCHAR(100) | |
| departure_date | TIMESTAMPTZ | |
| arrival_date | TIMESTAMPTZ | |
| eta | TIMESTAMPTZ | |
| status | ENUM | booked / in_transit / arrived / delivered / delayed |
| extra_data | JSONB | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### ports *(global — no tenant)*

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| port_name | VARCHAR(255) | |
| country | VARCHAR(100) | |
| port_code | VARCHAR(10) UNIQUE | UN/LOCODE |
| latitude | NUMERIC | |
| longitude | NUMERIC | |
| is_active | BOOLEAN | |

---

### transport_legs

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| container_id | BIGINT FK → containers | |
| shipment_id | BIGINT FK → shipments | optional |
| from_port | VARCHAR(100) | |
| to_port | VARCHAR(100) | |
| transport_type | ENUM | sea / air / road / rail |
| departure_time | TIMESTAMPTZ | |
| arrival_time | TIMESTAMPTZ | |
| carrier | VARCHAR(100) | |
| notes | TEXT | |

---

### documents

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | optional |
| uploaded_by | BIGINT FK → users | |
| document_type | ENUM | bill_of_lading / customs_form / invoice / inspection_report / packing_list / insurance / other |
| file_name | VARCHAR(255) | |
| file_url | TEXT | S3 / R2 / local URL |
| file_size | INTEGER | bytes |
| mime_type | VARCHAR(100) | |
| notes | TEXT | |

**Indexes:** `(tenant_id, container_id)`

---

### customs_clearance

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | |
| clearance_status | ENUM | pending / in_review / cleared / held / rejected |
| tax_paid | NUMERIC | |
| currency | CHAR(3) | |
| clearance_date | TIMESTAMPTZ | |
| agent_name | VARCHAR(255) | |
| agent_contact | VARCHAR(255) | |
| notes | TEXT | |
| extra_data | JSONB | |

---

### warehouses

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| name | VARCHAR(255) | |
| location | TEXT | |
| capacity | NUMERIC | m³ |
| manager | VARCHAR(255) | |
| is_active | BOOLEAN | |

---

### warehouse_inventory

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| warehouse_id | BIGINT FK → warehouses | |
| item_id | BIGINT FK → items | |
| quantity | INTEGER | |
| min_quantity | INTEGER | Low stock threshold |
| shelf_location | VARCHAR(100) | |

**Indexes:** `(warehouse_id, item_id)` unique composite

---

### inventory_movements

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| inventory_id | BIGINT FK → warehouse_inventory | |
| performed_by | BIGINT FK → users | |
| movement_type | ENUM | in / out / transfer / adjust |
| quantity | INTEGER | |
| reference | VARCHAR(255) | Order ID, container ID, etc. |
| notes | TEXT | |

---

### customers *(soft-delete)*

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| name | VARCHAR(255) | |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| address | TEXT | |
| notes | TEXT | |
| deleted_at | TIMESTAMPTZ | |

---

### suppliers *(soft-delete)*

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| supplier_name | VARCHAR(255) | |
| country | VARCHAR(100) | |
| contact_info | TEXT | |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| rating | NUMERIC | 0.0 – 5.0 |
| is_active | BOOLEAN | |
| extra_data | JSONB | |

---

### orders

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| customer_id | BIGINT FK → customers | |
| created_by_id | BIGINT FK → users | |
| status | ENUM | pending / confirmed / fulfilled / canceled |
| total | NUMERIC | |
| currency | CHAR(3) | |
| notes | TEXT | |

**Indexes:** `(tenant_id, customer_id)`, `(tenant_id, status)`

---

### order_items

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| order_id | BIGINT FK → orders | |
| item_id | BIGINT FK → items | |
| quantity | INTEGER | |
| price | NUMERIC | Price at time of order |
| currency | CHAR(3) | |

---

### payments

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| container_id | BIGINT FK → containers | optional |
| order_id | BIGINT FK → orders | optional |
| amount | NUMERIC | |
| currency | CHAR(3) | |
| payment_method | ENUM | cash / bank_transfer / card / stripe / other |
| paid_at | TIMESTAMPTZ | |
| reference | VARCHAR(255) | |
| notes | TEXT | |

---

### sales

Dedicated sale record per item. Replaces the `sold` boolean pattern with a full entity.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| item_id | BIGINT FK → items UNIQUE | One sale per item |
| customer_id | BIGINT FK → customers | optional |
| sold_by | BIGINT FK → users | |
| sale_price | NUMERIC | |
| currency | CHAR(3) | |
| sold_at | TIMESTAMPTZ | |
| notes | TEXT | |

**Indexes:** `(tenant_id, sold_at)`

---

### exchange_rate_history

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| from_currency | CHAR(3) | |
| to_currency | CHAR(3) | |
| rate | NUMERIC(18,8) | |
| date | DATE | |
| source | VARCHAR(50) | e.g. exchangerate-api |

**Constraints:** UNIQUE `(from_currency, to_currency, date)`
**Indexes:** `(from_currency, to_currency, date)`

---

### notifications

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| user_id | BIGINT FK → users | |
| notification_type | ENUM | tracking_update / price_change / low_stock / container_arrived / payment_received / system |
| title | VARCHAR(255) | |
| message | TEXT | |
| read | BOOLEAN | |
| data | JSONB | Extra context payload |

**Indexes:** `(user_id, read)`

---

### audit_logs

Append-only. Never updated or deleted.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| user_id | BIGINT FK → users | nullable (system actions) |
| action | VARCHAR(100) | e.g. `item.sold`, `role.changed` |
| entity_type | VARCHAR(100) | e.g. `Item`, `User` |
| entity_id | BIGINT | |
| ip_address | VARCHAR(45) | |
| user_agent | VARCHAR(512) | |
| extra_data | JSONB | Before/after values for sensitive changes |

**Indexes:** `(tenant_id, action)`, `(tenant_id, entity_type, entity_id)`, `created_at`

---

### demand_analytics

Refreshed every 6 hours by `refresh_demand_analytics` Celery task.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| tenant_id | BIGINT FK → organizations | |
| item_category | VARCHAR(100) | |
| avg_market_price | NUMERIC | From price_records |
| avg_sale_price | NUMERIC | From sales |
| avg_margin | NUMERIC | Average profit margin |
| demand_score | NUMERIC | 0 – 100 |
| units_sold_30d | INTEGER | |
| units_sold_90d | INTEGER | |
| updated_at_calc | TIMESTAMPTZ | Last recalculation |
| extra_data | JSONB | |

**Constraints:** UNIQUE `(tenant_id, item_category)`

---

## Soft Delete Pattern

Tables marked soft-delete use `deleted_at TIMESTAMPTZ`. All service queries filter with:

```sql
WHERE deleted_at IS NULL
```

To query deleted records (admin/audit use only):

```sql
WHERE deleted_at IS NOT NULL
```

To restore a record, set `deleted_at = NULL`.

---

## Migration Workflow

```bash
# After modifying a model file:
alembic revision --autogenerate -m "add supplier_rating column"

# Review the generated migration in alembic/versions/

# Apply to development database:
alembic upgrade head

# Apply to production (in CI/CD or deploy script):
docker-compose exec web alembic upgrade head
```

> Alembic detects: new tables, dropped tables, column additions, column type changes, new indexes, and server_default changes.
> It does **not** detect: column renames (treat as drop + add), constraint name changes.