-- Estate MD Gold bootstrap schema.
--
-- Creates the five internal Gold objects and states the required API rollout.
-- This is a clean-environment bootstrap file, not an in-place migration:
-- CREATE ... IF NOT EXISTS does not reconcile an older existing definition.
-- Inspect production metadata before changing an existing project.
--
-- Prerequisites: public.silver_estate exists and is populated; the executing
-- owner can create objects in public; service_role can read silver_estate.

begin;

-- Daily Gold snapshot tables.

create table if not exists public.gold_estate_daily (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    listings integer,
    avg_price_eur numeric(10, 2),
    median_price_eur numeric(12, 2),
    avg_per_m2_eur numeric(10, 2),
    created_at timestamp without time zone default now(),
    primary key (date, municipality, city, sector)
);

create table if not exists public.gold_rent_daily (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    deal_type text not null,
    listings integer,
    avg_price_eur numeric(10, 2),
    median_price_eur numeric(10, 2),
    avg_price_per_m2_eur numeric(8, 2),
    median_price_per_m2_eur numeric(8, 2),
    avg_area_m2 numeric(8, 1),
    created_at timestamp without time zone default now(),
    primary key (date, municipality, city, sector, deal_type)
);

create index if not exists gold_estate_daily_date_idx
    on public.gold_estate_daily (date);
create index if not exists gold_estate_daily_sector_idx
    on public.gold_estate_daily (sector);
create index if not exists gold_rent_daily_city_idx
    on public.gold_rent_daily (city);
create index if not exists gold_rent_daily_date_idx
    on public.gold_rent_daily (date);

-- Current sale and rent aggregates.

create materialized view if not exists public.gold_estate_current as
select
    current_date as date,
    municipality,
    city,
    sector,
    count(*) as listings,
    round(avg(price_eur)) as avg_price_eur,
    round(
        percentile_cont(0.5) within group (
            order by price_eur::double precision
        )
    ) as median_price_eur,
    round(avg(price_eur / nullif(total_area_m2, 0))) as avg_per_m2_eur
from public.silver_estate
where status = 'success'
  and deal_type = 'Продам'
  and price_eur >= 1000
  and total_area_m2 >= 20
  and total_area_m2 <= 400
  and publication_date >= (current_date - interval '60 days')
  and (price_eur / nullif(total_area_m2, 0)) >= 180
  and (price_eur / nullif(total_area_m2, 0)) <= 10000
group by municipality, city, sector
having count(*) >= 5
with no data;

create materialized view if not exists public.gold_rent_current as
select
    current_date as date,
    municipality,
    city,
    sector,
    deal_type,
    count(*) as listings,
    round(avg(price_eur), 2) as avg_price_eur,
    round(
        percentile_cont(0.5) within group (
            order by price_eur::double precision
        )::numeric,
        2
    ) as median_price_eur,
    round(avg(price_eur / nullif(total_area_m2, 0)), 2)
        as avg_price_per_m2_eur,
    round(
        percentile_cont(0.5) within group (
            order by (
                price_eur / nullif(total_area_m2, 0)
            )::double precision
        )::numeric,
        2
    ) as median_price_per_m2_eur,
    round(avg(total_area_m2), 1) as avg_area_m2
from public.silver_estate
where deal_type in ('Сдаю помесячно', 'Сдаю посуточно')
  and price_eur is not null
  and price_eur >= 10
  and price_eur <= 5000
  and total_area_m2 >= 15
  and total_area_m2 <= 300
  and publication_date >= (current_date - interval '30 days')
  and city is not null
  and sector is not null
group by municipality, city, sector, deal_type
having count(*) >= 3
with no data;

create index if not exists gold_rent_current_city_idx
    on public.gold_rent_current (city);
create index if not exists gold_rent_current_sector_idx
    on public.gold_rent_current (sector);

-- Indicative gross-yield view. Daily rent assumes 60% occupancy.

create or replace view public.gold_rent_yield
with (security_invoker = true) as
with rent_stats as (
    select
        city,
        sector,
        deal_type,
        round(avg(avg_price_eur), 2) as avg_price_eur,
        sum(listings) as rent_listings
    from public.gold_rent_current
    where listings >= 3
    group by city, sector, deal_type
),
monthly as (
    select
        city,
        sector,
        round(avg_price_eur * 12, 2) as annual_rent_monthly,
        rent_listings as monthly_listings
    from rent_stats
    where deal_type = 'Сдаю помесячно'
),
daily as (
    select
        city,
        sector,
        round(avg_price_eur * 365 * 0.60, 2) as annual_rent_daily_60pct,
        rent_listings as daily_listings
    from rent_stats
    where deal_type = 'Сдаю посуточно'
),
sale as (
    select
        city,
        sector,
        round(avg(avg_price_eur), 0) as avg_sale_price_eur,
        sum(listings) as sale_listings
    from public.gold_estate_current
    where listings >= 8
    group by city, sector
)
select
    coalesce(m.city, d.city, s.city) as city,
    coalesce(m.sector, d.sector, s.sector) as sector,
    case
        when s.avg_sale_price_eur > 0 and m.annual_rent_monthly > 0
        then round(m.annual_rent_monthly / s.avg_sale_price_eur * 100, 2)
        else null
    end as yield_monthly_percent,
    case
        when s.avg_sale_price_eur > 0 and d.annual_rent_daily_60pct > 0
        then round(d.annual_rent_daily_60pct / s.avg_sale_price_eur * 100, 2)
        else null
    end as yield_daily_percent,
    m.annual_rent_monthly,
    d.annual_rent_daily_60pct,
    s.avg_sale_price_eur,
    coalesce(m.monthly_listings, 0)::numeric
        + coalesce(d.daily_listings, 0)::numeric as total_rent_listings,
    s.sale_listings
from sale s
full join monthly m
    on m.city = s.city
   and m.sector = s.sector
full join daily d
    on d.city = s.city
   and d.sector = s.sector
order by
    yield_daily_percent desc nulls last,
    yield_monthly_percent desc nulls last,
    city,
    sector;

-- Internal access boundary. Public API access is granted only on api_* tables.

alter table public.gold_estate_daily enable row level security;
alter table public.gold_rent_daily enable row level security;

revoke all on table public.gold_estate_daily from anon, authenticated;
revoke all on table public.gold_rent_daily from anon, authenticated;
revoke all on table public.gold_estate_current from anon, authenticated;
revoke all on table public.gold_rent_current from anon, authenticated;
revoke all on table public.gold_rent_yield from anon, authenticated;

grant select, insert, update, delete
    on table public.gold_estate_daily to service_role;
grant select, insert, update, delete
    on table public.gold_rent_daily to service_role;
grant select, maintain
    on table public.gold_estate_current to service_role;
grant select, maintain
    on table public.gold_rent_current to service_role;
grant select on table public.gold_rent_yield to service_role;

commit;

-- Required public API rollout after this file. Do not sort alphabetically:
--
-- 1. sql/api/public_api_layer.sql
-- 2. sql/api/revoke_internal_public_access.sql
-- 3. sql/api/refresh_gold_updates_api_layer.sql
-- 4. sql/api/add_estate_segments_api_layer.sql
-- 5. sql/api/add_estate_segments_daily_api_layer.sql
-- 6. sql/api/add_estate_housing_type_api_layer.sql
-- 7. sql/api/add_estate_condition_api_layer.sql
-- 8. sql/api/add_estate_floor_position_api_layer.sql
-- 9. sql/api/harden_public_boundary.sql
-- 10. sql/api/check_public_api_layer.sql (verification only)
--
-- Required API objects:
-- api_estate_current, api_estate_daily,
-- api_estate_segments_current, api_estate_segments_daily,
-- api_estate_housing_type_current, api_estate_condition_current,
-- api_estate_floor_position_current, api_rent_current, api_rent_daily,
-- api_rent_yield.
--
-- Historical API scripts and known production differences are documented in
-- sql/api/README.md. Function ACL hardening and normalization of intentional
-- full-table DELETE statements remain separate reviewed work.
