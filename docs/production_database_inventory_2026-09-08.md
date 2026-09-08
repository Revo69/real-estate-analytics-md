# Production Database Inventory — 2026-09-08

This is a read-only snapshot of the `public` schema in the Supabase project
`estate-md` (`tfwfvdbatsdncyoibzxp`, PostgreSQL 17.6). It is evidence for the
public API ownership migration, not an executable migration and not a promise
that row counts remain current.

No schema, data, RLS, grant, policy, index, or function change was made while
collecting this inventory.

## Object inventory

Estimated row counts are the values reported by PostgreSQL/Supabase at the time
of inspection.

| Object | Kind | Estimated rows | Primary key | RLS | Public policy |
|---|---|---:|---|---|---|
| `raw_links` | table | 51,161 | `id` | on | none |
| `bronze_estate` | table | 48,807 | `id` | on | none |
| `silver_estate` | table | 48,337 | `id` | on | none |
| `pipeline_runs` | table | 57 | `run_id` | on | none |
| `gold_estate_current` | materialized view | 86 | none | n/a | none |
| `gold_estate_daily` | table | 6,786 | `(date, municipality, city, sector)` | on | none |
| `gold_rent_current` | materialized view | 49 | none | n/a | none |
| `gold_rent_daily` | table | 4,075 | `(date, municipality, city, sector, deal_type)` | on | none |
| `gold_rent_yield` | view | n/a | none | n/a | none |
| `api_estate_current` | table | 86 | `(date, municipality, city, sector)` | on | read: `anon, authenticated` |
| `api_estate_daily` | table | 6,786 | `(date, municipality, city, sector)` | on | read: `anon, authenticated` |
| `api_rent_current` | table | 49 | `(date, municipality, city, sector, deal_type)` | on | read: `anon, authenticated` |
| `api_rent_daily` | table | 3,893 | `(date, municipality, city, sector, deal_type)` | on | read: `anon, authenticated` |
| `api_rent_yield` | table | 70 | `(city, sector)` | on | read: `anon, authenticated` |
| `api_estate_segments_current` | table | 213 | `(date, municipality, city, sector, rooms_group, area_band)` | on | read: `anon, authenticated` |
| `api_estate_segments_daily` | table | 10,605 | `(date, municipality, city, sector, rooms_group, area_band)` | on | read: `anon, authenticated` |
| `api_estate_housing_type_current` | table | 112 | `(date, municipality, city, sector, housing_type)` | on | read: `anon, authenticated` |
| `api_estate_condition_current` | table | 108 | `(date, municipality, city, sector, condition_group)` | on | read: `anon, authenticated` |
| `api_estate_floor_position_current` | table | 126 | `(date, municipality, city, sector, floor_position)` | on | read: `anon, authenticated` |

## Production column signatures

`not null` is shown only where PostgreSQL currently enforces it.

- `raw_links`: `id uuid not null`, `url text not null`, `status text`,
  `attempts integer`, `created_at timestamptz`, `updated_at timestamptz`.
- `bronze_estate`: `id uuid not null`, `url text not null`, `ad_id text`,
  `status text`, `publication_date text`, `user_login text`, `deal_type text`,
  `region text`, `description text`, `price_json jsonb`,
  `main_features_json jsonb`, `additional_features_json jsonb`,
  `created_at timestamptz`.
- `pipeline_runs`: `run_id text not null`, `pipeline_name text not null`,
  `status text not null`, `current_stage text`, `failed_stage text`,
  `started_at timestamptz not null`, `finished_at timestamptz`,
  `links_discovered integer not null`, `new_links integer not null`,
  `bronze_loaded integer not null`, `silver_success integer not null`,
  `silver_partial integer not null`, `silver_failed integer not null`,
  `rejected_count integer not null`, `gold_refreshed boolean not null`,
  `error_message text`, `git_sha text`, `github_run_id bigint`,
  `github_run_attempt integer`.
- `silver_estate`: `id uuid not null`, `url text not null`, `ad_id text`,
  `status text`, `publication_date date`, `user_login text`, `deal_type text`,
  `region_raw text`, `description text`, `price_mdl numeric`,
  `price_eur numeric`, `price_usd numeric`, `listing_author text`,
  `number_of_rooms integer`, `living_room boolean`, `total_area_m2 numeric`,
  `housing_type text`, `floor integer`, `total_floors integer`,
  `developer text`, `building_type text`, `apartment_condition text`,
  `layout text`, `living_area_m2 numeric`, `kitchen_area_m2 numeric`,
  `bathroom_count integer`, `balcony_loggia text`, `ceiling_height_cm numeric`,
  `parking_space text`, `ready_to_move_in boolean`, `extension boolean`,
  `terrace boolean`, `separate_entrance boolean`, `park_area boolean`,
  `furnished boolean`, `with_appliances boolean`, `autonomous_heating boolean`,
  `air_conditioning boolean`, `underfloor_heating boolean`,
  `double_glazing boolean`, `panoramic_windows boolean`, `parquet_floor boolean`,
  `laminate_floor boolean`, `security_door boolean`, `telephone_line boolean`,
  `smart_home boolean`, `intercom boolean`, `internet boolean`,
  `cable_tv boolean`, `alarm_system boolean`, `video_surveillance boolean`,
  `elevator boolean`, `playground boolean`, `created_at timestamp`,
  `quality_score numeric`, `normalization_status text`, `municipality text`,
  `city text`, `sector text`, `street_raw text`, `house text`.
- `gold_estate_current`: `date date`, `municipality text`, `city text`,
  `sector text`, `listings bigint`, `avg_price_eur numeric`,
  `median_price_eur double precision`, `avg_per_m2_eur numeric`.
- `gold_estate_daily`: the same geographic/metric columns, with required key
  columns, `listings integer`, numeric precision constraints, and
  `created_at timestamp`.
- `gold_rent_current`: `date date`, geographic columns, `deal_type text`,
  `listings bigint`, `avg_price_eur numeric`, `median_price_eur numeric`,
  `avg_price_per_m2_eur numeric`, `median_price_per_m2_eur numeric`,
  `avg_area_m2 numeric`.
- `gold_rent_daily`: the same rent columns, with required key columns,
  `listings integer`, numeric precision constraints, and `created_at timestamp`.
- `gold_rent_yield`: `city text`, `sector text`, `yield_monthly_percent numeric`,
  `yield_daily_percent numeric`, `annual_rent_monthly numeric`,
  `annual_rent_daily_60pct numeric`, `avg_sale_price_eur numeric`,
  `total_rent_listings numeric`, `sale_listings numeric`.
- `api_estate_current` and `api_estate_daily`: required `date`, `municipality`,
  `city`, `sector`; `listings` (`bigint` current, `integer` daily),
  `avg_price_eur numeric`, `median_price_eur` (`double precision` current,
  `numeric` daily), `avg_per_m2_eur numeric`, `refreshed_at timestamptz not null`.
- `api_rent_current` and `api_rent_daily`: required `date`, `municipality`,
  `city`, `sector`, `deal_type`; `listings` (`bigint` current, `integer` daily),
  five numeric price/area metrics, and `refreshed_at timestamptz not null`.
- `api_rent_yield`: required `city`, `sector`; seven numeric yield/rent/sale
  measures; `refreshed_at timestamptz not null`.
- `api_estate_segments_current` and `api_estate_segments_daily`: required
  geographic key plus `rooms_group` and `area_band`; `listings bigint not null`,
  three numeric price metrics, `refreshed_at timestamptz not null`.
- `api_estate_housing_type_current`, `api_estate_condition_current`, and
  `api_estate_floor_position_current`: required geographic key plus respectively
  `housing_type`, `condition_group`, or `floor_position`; `listings bigint not
  null`, three numeric price metrics, `refreshed_at timestamptz not null`.

## Gold definition fingerprints

The complete definitions were read with `pg_get_viewdef`; these fingerprints
anchor the reconciliation with the versioned SQL in Task 2.

| Object | Definition MD5 | Current core filters/logic |
|---|---|---|
| `gold_estate_current` | `d9b5889d0f68ca10e5928ed784b7006d` | successful sale listings; EUR price >= 1,000; area 20–400 m²; latest 60 days; EUR/m² 180–10,000; group count >= 5 |
| `gold_rent_current` | `b78079db35616cd97754360a4c4f27d6` | monthly/daily rent; EUR price 10–5,000; area 15–300 m²; latest 30 days; city/sector present; group count >= 3 |
| `gold_rent_yield` | `db81025bf52e234908750b8ae4aa149a` | monthly annualization ×12; daily annualization ×365×0.60; sale groups >= 8; indicative gross yield |

## Refresh function inventory

Both functions are `SECURITY INVOKER`, return `void`, and have the fixed setting
`search_path = public, pg_temp`.

| Function | Definition MD5 | Maintains |
|---|---|---|
| `refresh_gold_estate()` | `f0e05b3f2f6a210ae0749af4a0d9ba65` | refreshes sale MV/history; current and daily sale API; current/daily room-area segments; housing type, condition, floor-position profiles; rebuilds yield API |
| `refresh_gold_rent()` | `8d5ed5e136c60173a84ee5b595f17798` | refreshes rent MV/history; current and daily rent API; rebuilds yield API |

The exact `pg_get_functiondef` bodies were compared during capture and will be
stored as executable producer SQL under `sql/api/` in Task 2 Step 2. Current ACL
for both functions grants `EXECUTE` to `PUBLIC`, `anon`, `authenticated`, and
`service_role` (plus the owner). That is broader than the intended producer-only
refresh boundary and must be handled by an explicit reviewed migration.

## Grants, RLS, and policies

- Every `api_*` table has RLS enabled, one unconditional `SELECT` policy for
  `anon, authenticated`, explicit `SELECT` grants for those roles, and full
  table privileges for `service_role`.
- `pipeline_runs` has RLS enabled, no policies, no `anon/authenticated` grants,
  and full table privileges for `service_role`.
- `raw_links`, `bronze_estate`, `silver_estate`, `gold_estate_daily`, and
  `gold_rent_daily` have RLS enabled with no policies, so direct public access is
  denied by RLS. However, `anon` and `authenticated` still retain non-SELECT
  table grants (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`,
  `TRIGGER`). These grants should be revoked as defense in depth.
- `gold_estate_current` and `gold_rent_current` expose no grants to the three
  inspected roles. `gold_rent_yield` still reports the same legacy non-SELECT
  grants for `anon/authenticated`; its view updatability does not make those
  privileges appropriate.

RLS and SQL grants are separate controls. The canonical SQL must keep both the
positive public-read grants on `api_*` and explicit revocations on producer
objects.

## Index inventory and advisor findings

Primary/unique indexes enforce the keys listed above. The remaining production
index names captured in this snapshot are:

- `raw_links`: `raw_links_attempts_idx`, `raw_links_status_key`,
  `raw_links_url_key`; `bronze_estate`: `bronze_estate_created_at_idx`,
  `bronze_estate_publication_date_idx`, `bronze_estate_status_idx`,
  `bronze_estate_url_key`.
- `silver_estate`: `idx_silver_active_valid`, `idx_silver_city`,
  `idx_silver_estate_current_analysis`, `idx_silver_municipality`,
  `idx_silver_price_m2`, `idx_silver_publication`, `idx_silver_sector`,
  `silver_estate_deal_type_idx`, `silver_estate_elevator_idx`,
  `silver_estate_playground_idx`, `silver_estate_price_eur_idx`,
  `silver_estate_total_area_m2_idx`, `silver_estate_url_key`.
- `pipeline_runs`: `pipeline_runs_started_at_idx`; `gold_estate_daily`:
  `gold_estate_daily_date_idx`, `gold_estate_daily_sector_idx`;
  `gold_rent_current`: `gold_rent_current_city_idx`,
  `gold_rent_current_sector_idx`; `gold_rent_daily`:
  `gold_rent_daily_city_idx`, `gold_rent_daily_date_idx`.
- `gold_estate_current` and `gold_rent_yield`: no indexes beyond none/primary
  key; materialized `gold_rent_current` has the two indexes listed above.
- `api_estate_current`: indexes on `avg_per_m2_eur`, `avg_price_eur`, `city`,
  `date` (three copies), `listings`, `median_price_eur`, `refreshed_at` (two
  copies), and `sector`.
- `api_estate_daily`: `api_estate_daily_date_city_idx` plus four `date` copies.
- `api_rent_current`: indexes on the five price/area metrics,
  `(city, deal_type)`, `date` (three copies), and `refreshed_at` (two copies).
- `api_rent_daily`: `api_rent_daily_date_city_deal_type_idx` plus four `date`
  copies.
- `api_rent_yield`: indexes on both yield measures, both annual-rent measures,
  sale price, total rent listings, `refreshed_at` (three copies), and
  `sale_listings` (two copies).
- `api_estate_segments_current`: indexes on `(city, sector)`, `date`, and
  `(rooms_group, area_band)`; `api_estate_segments_daily`: indexes on
  `(date desc, city)`, `date`, and `(rooms_group, area_band)`.
- Each current profile table has one secondary `(city, profile_dimension)`
  index: `api_estate_housing_type_city_type_idx`,
  `api_estate_condition_city_group_idx`, and
  `api_estate_floor_position_city_idx`.

The Performance Advisor reported 32
[unused-index](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index)
notices and these
[duplicate-index](https://supabase.com/docs/guides/database/database-linter?lint=0009_duplicate_index)
groups:

- `api_estate_current(date)`: `..._date_idx`, `..._date_idx1`, `..._date_idx2`.
- `api_estate_current(refreshed_at)`: `..._refreshed_at_idx`, `..._idx1`.
- `api_estate_daily(date)`: `..._date_idx` through `..._date_idx3`.
- `api_rent_current(date)`: `..._date_idx`, `..._date_idx1`, `..._date_idx2`.
- `api_rent_current(refreshed_at)`: `..._refreshed_at_idx`, `..._idx1`.
- `api_rent_daily(date)`: `..._date_idx` through `..._date_idx3`.
- `api_rent_yield(refreshed_at)`: `..._refreshed_at_idx` through `..._idx2`.
- `api_rent_yield(sale_listings)`: `..._sale_listings_idx`, `..._idx1`.

No index is removed by this documentation task. Unused-index notices require
workload evidence; exact duplicate indexes can be consolidated later in a
separate reversible migration after verifying dependencies and query plans.

The Security Advisor reported
[`rls_enabled_no_policy`](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
information notices for
the six private tables (`raw_links`, `bronze_estate`, `silver_estate`,
`gold_estate_daily`, `gold_rent_daily`, `pipeline_runs`). In this architecture,
no-policy RLS is intentional for private client access, but grants should still
be minimized.

## Reconciliation decisions for the next step

1. Copy the dashboard producer SQL upstream before deleting anything downstream.
2. Compare executable definitions against the fingerprints above.
3. Preserve public `SELECT` on the ten `api_*` tables and remove public writes.
4. Add explicit function `EXECUTE` revocation for `PUBLIC`, `anon`, and
   `authenticated`, subject to a separate review before production application.
5. Treat duplicate-index cleanup as its own change, not part of documentation
   ownership migration.

The byte-for-byte upstream copies and per-script reconciliation are recorded in
[`sql/api/README.md`](../sql/api/README.md).
