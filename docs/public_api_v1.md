# Estate MD Public API v1

This is the canonical producer-side public data contract owned by
`real-estate-analytics-md`. `Imobil-Index` is its current Streamlit consumer.
The contract and access boundary were verified against production on
2026-09-10; current row counts and dates must be queried rather than copied
into documentation.

The API exposes only aggregated real estate analytics from Moldova. It does not
expose raw listings, source links, seller data, phone numbers, or internal
Bronze/Silver/Gold tables.

## Base URL

Supabase REST API:

```text
https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1
```

Use the public anon key in the `apikey` and `Authorization` headers. Never use
or publish the `service_role` key in client-side code.

Example headers:

```text
apikey: <SUPABASE_ANON_KEY>
Authorization: Bearer <SUPABASE_ANON_KEY>
```

## Public Tables

| Table | Purpose | Grain |
|---|---|---|
| `api_estate_current` | Current sale market metrics | date + municipality + city + sector |
| `api_estate_daily` | Historical sale market metrics | date + municipality + city + sector |
| `api_estate_segments_current` | Current sale metrics by rooms and area band | date + municipality + city + sector + rooms_group + area_band |
| `api_estate_segments_daily` | Historical sale metrics by rooms and area band | date + municipality + city + sector + rooms_group + area_band |
| `api_estate_housing_type_current` | Current sale metrics by new-build versus resale segment | date + municipality + city + sector + housing_type |
| `api_estate_condition_current` | Current sale metrics by normalized finish and condition | date + municipality + city + sector + condition_group |
| `api_estate_floor_position_current` | Current sale metrics by floor position | date + municipality + city + sector + floor_position |
| `api_rent_current` | Current monthly/daily rent metrics | date + municipality + city + sector + deal_type |
| `api_rent_daily` | Historical monthly/daily rent metrics | date + municipality + city + sector + deal_type |
| `api_rent_yield` | Indicative gross rent-yield metrics | city + sector |

## Contract Matrix

All ten tables use the same access model: `anon` and `authenticated` receive
`SELECT` only, RLS is enabled, and a read policy permits those roles. Public
write access is outside this contract. `service_role` is producer-side only and
must never be shipped with the dashboard or another public client.

| Table | Minimum published group | Freshness | Maintained by |
|---|---|---|---|
| `api_estate_current` | 5 qualifying sale listings per geographic grain | `date` is the snapshot; `refreshed_at` is the copy time | `refresh_gold_estate()` |
| `api_estate_daily` | 5 qualifying sale listings when that daily snapshot was produced | one upserted row per snapshot grain and date | `refresh_gold_estate()` |
| `api_estate_segments_current` | 5 qualifying sale listings per room/area/geographic grain | current replacement; `refreshed_at` is the rebuild time | `refresh_gold_estate()` |
| `api_estate_segments_daily` | 5 qualifying sale listings when that profile snapshot was produced | one upserted row per profile grain and date | `refresh_gold_estate()` |
| `api_estate_housing_type_current` | 5 qualifying sale listings per housing/geographic grain | current replacement | `refresh_gold_estate()` |
| `api_estate_condition_current` | 5 qualifying sale listings per condition/geographic grain | current replacement | `refresh_gold_estate()` |
| `api_estate_floor_position_current` | 5 qualifying sale listings per floor/geographic grain | current replacement | `refresh_gold_estate()` |
| `api_rent_current` | 3 qualifying rent listings per deal-type/geographic grain | `date` is the snapshot; `refreshed_at` is the copy time | `refresh_gold_rent()` |
| `api_rent_daily` | 3 qualifying rent listings when that daily snapshot was produced | one upserted row per snapshot grain and date | `refresh_gold_rent()` |
| `api_rent_yield` | rent inputs require at least 3 listings; sale input requires at least 8 listings per city/sector | current replacement; nullable yields indicate a missing usable rent or sale side | both refresh functions |

The minimums suppress thin groups; they do not guarantee statistical
representativeness. A daily table is pipeline snapshot history, not reconstructed
listing-publication history and not a price-change history for individual ads.

Changing a primary-key grain, removing or renaming a column, changing a unit, or
reinterpreting an existing metric is a breaking contract change and requires a
new API version. Additive nullable columns may remain in v1 after producer and
consumer compatibility review.

## Shared Fields

| Field | Meaning |
|---|---|
| `date` | Market snapshot date. This is the data date, not the request time. |
| `municipality` | Municipality name. Missing source values are published as `Unknown`. |
| `city` | City name. Missing source values are published as `Unknown`. |
| `sector` | City sector/district. Missing source values are published as `Center`. |
| `listings` | Number of listings included in the aggregate. |
| `refreshed_at` | Timestamp when the public API row was refreshed from the internal source layer. |

## Segment Fields

| Field | Meaning |
|---|---|
| `rooms_group` | Room-count group. Current values are `1`, `2`, `3`, and `4+`. |
| `area_band` | Total-area group. Current values are `<40 m2`, `40-59 m2`, `60-79 m2`, `80-119 m2`, and `120+ m2`. |
| `housing_type` | Sale-market segment. Current values are `Новострой` and `Вторичный`. |
| `condition_group` | Normalized finish and condition segment. Current values are `Euro renovation`, `White finish`, `Cosmetic renovation`, `Individual design`, and `Needs renovation`. |
| `floor_position` | Position in the building. Current values are `Ground floor`, `Middle floor`, and `Top floor`. |

## `api_estate_current`

Current sale-market aggregate by date, municipality, city, and sector.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `listings` | bigint | no | Sale listings in this group. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | double precision | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_daily`

Historical sale-market aggregate with the same business meaning as
`api_estate_current`.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `listings` | integer | yes | Sale listings in this group. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_segments_current`

Current sale-market aggregate by rooms and area band. It uses the same sale
market filters as `gold_estate_current`, plus `number_of_rooms is not null`.
Only groups with at least 5 listings are published.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `rooms_group` | text | no | Room-count group. |
| `area_band` | text | no | Total-area group. |
| `listings` | bigint | no | Sale listings in this segment. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_segments_daily`

Historical sale-market snapshots by rooms and area band. It uses the same
business meaning as `api_estate_segments_current`, but stores one row per
snapshot date so profile-level trends can be queried over time.

This history starts when
`sql/api/add_estate_segments_daily_api_layer.sql` is
applied. Older profile snapshots are not backfilled from `publication_date`
because that would change the meaning from market snapshot history to listing
publication history.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `rooms_group` | text | no | Room-count group. |
| `area_band` | text | no | Total-area group. |
| `listings` | bigint | no | Sale listings in this segment. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_housing_type_current`

Current sale-market aggregate by new-build versus resale segment. It uses the
same sale-market quality filters as the existing public sale-profile API.
Only groups with at least 5 listings are published.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `housing_type` | text | no | `Новострой` or `Вторичный`. |
| `listings` | bigint | no | Sale listings in this segment. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_condition_current`

Current sale-market aggregate by normalized finish and condition. It uses the
same sale-market quality filters as the existing public sale-profile API.
Only groups with at least 5 listings are published.

The raw source field also contains construction-stage statuses and a few
Latin/Cyrillic lookalike typos. Those values are not published in this first
release. The published groups are a comparison signal, not a causal estimate of
the price effect of a renovation.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `condition_group` | text | no | One of the five normalized finish and condition groups. |
| `listings` | bigint | no | Sale listings in this segment. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_estate_floor_position_current`

Current sale-market aggregate by position within the building. It uses the same
sale-market quality filters as the existing public sale-profile API, plus valid
positive `floor` and `total_floors` values. Only groups with at least 5
listings are published.

This is a comparison signal, not a causal estimate of a floor premium. Building
height, location, condition, housing type, and listing mix can also affect the
visible price differences.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `floor_position` | text | no | `Ground floor`, `Middle floor`, or `Top floor`. |
| `listings` | bigint | no | Sale listings in this segment. |
| `avg_price_eur` | numeric | yes | Average sale listing price in EUR. |
| `median_price_eur` | numeric | yes | Median sale listing price in EUR. |
| `avg_per_m2_eur` | numeric | yes | Average sale price per square meter in EUR. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_rent_current`

Current rent-market aggregate by date, municipality, city, sector, and deal
type.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `deal_type` | text | no | Rent market type, for example monthly or daily rent. |
| `listings` | bigint | no | Rent listings in this group. |
| `avg_price_eur` | numeric | yes | Average rent price in EUR. |
| `median_price_eur` | numeric | yes | Median rent price in EUR. |
| `avg_price_per_m2_eur` | numeric | yes | Average rent price per square meter in EUR. |
| `median_price_per_m2_eur` | numeric | yes | Median rent price per square meter in EUR. |
| `avg_area_m2` | numeric | yes | Average listing area in square meters. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_rent_daily`

Historical rent-market aggregate with the same business meaning as
`api_rent_current`.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `date` | date | no | Snapshot date. |
| `municipality` | text | no | Municipality. |
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `deal_type` | text | no | Rent market type. |
| `listings` | integer | yes | Rent listings in this group. |
| `avg_price_eur` | numeric | yes | Average rent price in EUR. |
| `median_price_eur` | numeric | yes | Median rent price in EUR. |
| `avg_price_per_m2_eur` | numeric | yes | Average rent price per square meter in EUR. |
| `median_price_per_m2_eur` | numeric | yes | Median rent price per square meter in EUR. |
| `avg_area_m2` | numeric | yes | Average listing area in square meters. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## `api_rent_yield`

Indicative gross yield by city and sector. Yield values are calculated before
full operating costs such as utilities, maintenance, vacancy, cleaning, taxes,
platform fees, and management costs.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `city` | text | no | City. |
| `sector` | text | no | Sector or district. |
| `yield_monthly_percent` | numeric | yes | Indicative gross annual yield from monthly rent. |
| `yield_daily_percent` | numeric | yes | Indicative gross annual yield from daily rent at the current model assumption. |
| `annual_rent_monthly` | numeric | yes | Estimated annual rent from monthly rent. |
| `annual_rent_daily_60pct` | numeric | yes | Estimated annual rent from daily rent at 60% occupancy. |
| `avg_sale_price_eur` | numeric | yes | Average sale price used in the yield calculation. |
| `total_rent_listings` | numeric | yes | Rent listing count used in the calculation. |
| `sale_listings` | numeric | yes | Sale listing count used in the calculation. |
| `refreshed_at` | timestamptz | no | API refresh timestamp. |

## Example Requests

Current sale metrics for Chisinau:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_current?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&select=date,city,sector,listings,avg_per_m2_eur" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

Top daily-rent yield sectors:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_rent_yield?select=city,sector,yield_daily_percent,sale_listings,total_rent_listings&order=yield_daily_percent.desc.nullslast&limit=10" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

Current sale prices by rooms and area band:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_segments_current?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&rooms_group=eq.2&select=date,city,sector,rooms_group,area_band,listings,avg_per_m2_eur&order=listings.desc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

Current new-build versus resale sale metrics:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_housing_type_current?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&select=date,city,sector,housing_type,listings,avg_per_m2_eur&order=listings.desc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

Current sale metrics by finish and condition:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_condition_current?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&select=date,city,sector,condition_group,listings,avg_per_m2_eur&order=listings.desc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

Current sale metrics by floor position:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_floor_position_current?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&select=date,city,sector,floor_position,listings,avg_per_m2_eur&order=listings.desc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

90-day sale price history for one city:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_daily?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&select=date,sector,avg_per_m2_eur,listings&order=date.asc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

90-day sale price history for one room/area profile:

```bash
curl "https://tfwfvdbatsdncyoibzxp.supabase.co/rest/v1/api_estate_segments_daily?city=eq.%D0%9A%D0%B8%D1%88%D0%B8%D0%BD%D1%91%D0%B2&rooms_group=eq.2&area_band=eq.60-79%20m2&select=date,sector,rooms_group,area_band,listings,avg_per_m2_eur&order=date.asc" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>"
```

## Refresh Contract

Gold remains the source of truth. The public API layer is refreshed by the same
database functions used by the upstream pipeline:

| Function | Public tables maintained |
|---|---|
| `refresh_gold_estate()` | `api_estate_current`, `api_estate_daily`, `api_estate_segments_current`, `api_estate_segments_daily`, `api_estate_housing_type_current`, `api_estate_condition_current`, `api_estate_floor_position_current`, `api_rent_yield` |
| `refresh_gold_rent()` | `api_rent_current`, `api_rent_daily`, `api_rent_yield` |

After a normal pipeline run, `api_estate_current`, `api_estate_daily`,
`api_estate_segments_current`, `api_estate_segments_daily`,
`api_estate_housing_type_current`, `api_estate_condition_current`,
`api_estate_floor_position_current`, `api_rent_current`, and `api_rent_daily`
should have the latest snapshot date.

The functions are an internal producer interface, not a public dashboard API.
They must remain `SECURITY INVOKER`, use a fixed `search_path`, and be executable
only by the pipeline's private producer role. This execution boundary was
hardened and verified on 2026-09-10.

## Access Rules

- `anon` and `authenticated` can only read the `api_*` tables.
- Public roles cannot insert, update, delete, or truncate API tables.
- Internal `raw_*`, `bronze_*`, `silver_*`, and Gold objects stay private.
- Row-level security is enabled on public API tables, with read-only SELECT
  policies for `anon` and `authenticated`.

The least-privilege boundary was applied and verified on 2026-09-10 with
[`sql/api/harden_public_boundary.sql`](../sql/api/harden_public_boundary.sql).
The earlier
[`production_database_inventory_2026-09-08.md`](production_database_inventory_2026-09-08.md)
remains a dated pre-hardening snapshot.

Run [`sql/api/check_public_api_layer.sql`](../sql/api/check_public_api_layer.sql)
after pipeline or security changes. It verifies public table grants/RLS,
internal relation privileges, refresh-function execution and security mode,
and defaults for new producer-owned objects.
