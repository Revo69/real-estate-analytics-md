-- Public API layer for Imobil.Index.
--
-- Goal:
-- - expose only aggregated, dashboard-safe data to anon/authenticated API users;
-- - keep raw/bronze/silver/internal Gold objects private from public clients;
-- - avoid exposing materialized views directly through the Supabase Data API.
--
-- Apply this file manually in Supabase SQL Editor.
-- Recommended order:
-- 1. Run section 1 and verify the new api_* tables.
-- 2. Update the Streamlit app to read api_* tables.
-- 3. Run section 2 to revoke public SELECT from internal objects.

begin;

-- =========================================================
-- 1. Public API tables
-- =========================================================

create table if not exists public.api_estate_current (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    listings bigint not null,
    avg_price_eur numeric,
    median_price_eur double precision,
    avg_per_m2_eur numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (date, municipality, city, sector)
);

create table if not exists public.api_rent_current (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    deal_type text not null,
    listings bigint not null,
    avg_price_eur numeric,
    median_price_eur numeric,
    avg_price_per_m2_eur numeric,
    median_price_per_m2_eur numeric,
    avg_area_m2 numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (date, municipality, city, sector, deal_type)
);

create table if not exists public.api_rent_yield (
    city text not null,
    sector text not null,
    yield_monthly_percent numeric,
    yield_daily_percent numeric,
    annual_rent_monthly numeric,
    annual_rent_daily_60pct numeric,
    avg_sale_price_eur numeric,
    total_rent_listings numeric,
    sale_listings numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (city, sector)
);

create table if not exists public.api_estate_daily (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    listings integer,
    avg_price_eur numeric,
    median_price_eur numeric,
    avg_per_m2_eur numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (date, municipality, city, sector)
);

create table if not exists public.api_rent_daily (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    deal_type text not null,
    listings integer,
    avg_price_eur numeric,
    median_price_eur numeric,
    avg_price_per_m2_eur numeric,
    median_price_per_m2_eur numeric,
    avg_area_m2 numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (date, municipality, city, sector, deal_type)
);

create index if not exists api_estate_current_city_idx
    on public.api_estate_current (city);

create index if not exists api_rent_current_city_deal_type_idx
    on public.api_rent_current (city, deal_type);

create index if not exists api_rent_yield_daily_idx
    on public.api_rent_yield (yield_daily_percent desc nulls last);

create index if not exists api_estate_daily_date_city_idx
    on public.api_estate_daily (date desc, city);

create index if not exists api_rent_daily_date_city_deal_type_idx
    on public.api_rent_daily (date desc, city, deal_type);

alter table public.api_estate_current enable row level security;
alter table public.api_rent_current enable row level security;
alter table public.api_rent_yield enable row level security;
alter table public.api_estate_daily enable row level security;
alter table public.api_rent_daily enable row level security;

drop policy if exists "Public can read estate current API data"
    on public.api_estate_current;
create policy "Public can read estate current API data"
    on public.api_estate_current
    for select
    to anon, authenticated
    using (true);

drop policy if exists "Public can read rent current API data"
    on public.api_rent_current;
create policy "Public can read rent current API data"
    on public.api_rent_current
    for select
    to anon, authenticated
    using (true);

drop policy if exists "Public can read rent yield API data"
    on public.api_rent_yield;
create policy "Public can read rent yield API data"
    on public.api_rent_yield
    for select
    to anon, authenticated
    using (true);

drop policy if exists "Public can read estate daily API data"
    on public.api_estate_daily;
create policy "Public can read estate daily API data"
    on public.api_estate_daily
    for select
    to anon, authenticated
    using (true);

drop policy if exists "Public can read rent daily API data"
    on public.api_rent_daily;
create policy "Public can read rent daily API data"
    on public.api_rent_daily
    for select
    to anon, authenticated
    using (true);

grant select on public.api_estate_current to anon, authenticated;
grant select on public.api_rent_current to anon, authenticated;
grant select on public.api_rent_yield to anon, authenticated;
grant select on public.api_estate_daily to anon, authenticated;
grant select on public.api_rent_daily to anon, authenticated;

grant select, insert, update, delete on public.api_estate_current to service_role;
grant select, insert, update, delete on public.api_rent_current to service_role;
grant select, insert, update, delete on public.api_rent_yield to service_role;
grant select, insert, update, delete on public.api_estate_daily to service_role;
grant select, insert, update, delete on public.api_rent_daily to service_role;

revoke insert, update, delete, truncate, references, trigger
    on public.api_estate_current from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger
    on public.api_rent_current from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger
    on public.api_rent_yield from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger
    on public.api_estate_daily from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger
    on public.api_rent_daily from anon, authenticated;

comment on table public.api_estate_current is
    'Public API table with aggregated sale-market metrics only.';
comment on table public.api_rent_current is
    'Public API table with aggregated monthly and daily rent metrics only.';
comment on table public.api_rent_yield is
    'Public API table with indicative gross rent-yield metrics only.';
comment on table public.api_estate_daily is
    'Public API table with aggregated sale-market history only.';
comment on table public.api_rent_daily is
    'Public API table with aggregated rent-market history only.';

-- Initial load from internal Gold objects.
truncate table public.api_estate_current;
insert into public.api_estate_current (
    date,
    municipality,
    city,
    sector,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    refreshed_at
)
select
    date,
    coalesce(municipality, 'Unknown'),
    coalesce(city, 'Unknown'),
    coalesce(sector, 'Center'),
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    now()
from public.gold_estate_current;

truncate table public.api_rent_current;
insert into public.api_rent_current (
    date,
    municipality,
    city,
    sector,
    deal_type,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_price_per_m2_eur,
    median_price_per_m2_eur,
    avg_area_m2,
    refreshed_at
)
select
    date,
    coalesce(municipality, 'Unknown'),
    coalesce(city, 'Unknown'),
    coalesce(sector, 'Center'),
    deal_type,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_price_per_m2_eur,
    median_price_per_m2_eur,
    avg_area_m2,
    now()
from public.gold_rent_current;

truncate table public.api_rent_yield;
insert into public.api_rent_yield (
    city,
    sector,
    yield_monthly_percent,
    yield_daily_percent,
    annual_rent_monthly,
    annual_rent_daily_60pct,
    avg_sale_price_eur,
    total_rent_listings,
    sale_listings,
    refreshed_at
)
select
    coalesce(city, 'Unknown'),
    coalesce(sector, 'Center'),
    yield_monthly_percent,
    yield_daily_percent,
    annual_rent_monthly,
    annual_rent_daily_60pct,
    avg_sale_price_eur,
    total_rent_listings,
    sale_listings,
    now()
from public.gold_rent_yield;

truncate table public.api_estate_daily;
insert into public.api_estate_daily (
    date,
    municipality,
    city,
    sector,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    refreshed_at
)
select
    date,
    coalesce(municipality, 'Unknown'),
    coalesce(city, 'Unknown'),
    coalesce(sector, 'Center'),
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    now()
from public.gold_estate_daily;

truncate table public.api_rent_daily;
insert into public.api_rent_daily (
    date,
    municipality,
    city,
    sector,
    deal_type,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_price_per_m2_eur,
    median_price_per_m2_eur,
    avg_area_m2,
    refreshed_at
)
select
    date,
    coalesce(municipality, 'Unknown'),
    coalesce(city, 'Unknown'),
    coalesce(sector, 'Center'),
    deal_type,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_price_per_m2_eur,
    median_price_per_m2_eur,
    avg_area_m2,
    now()
from public.gold_rent_daily;

commit;

-- Verification after section 1:
--
-- select 'api_estate_current' as table_name, count(*) from public.api_estate_current
-- union all
-- select 'api_rent_current', count(*) from public.api_rent_current
-- union all
-- select 'api_rent_yield', count(*) from public.api_rent_yield
-- union all
-- select 'api_estate_daily', count(*) from public.api_estate_daily
-- union all
-- select 'api_rent_daily', count(*) from public.api_rent_daily;
--
-- select schemaname, tablename, policyname, roles, cmd
-- from pg_policies
-- where schemaname = 'public'
--   and tablename like 'api_%'
-- order by tablename, policyname;

-- =========================================================
-- 2. Cut over internal objects after the app reads api_*.
-- =========================================================
--
-- Run this section only after app.py has been updated and verified with:
-- - api_estate_current instead of gold_estate_current
-- - api_rent_current instead of gold_rent_current
-- - api_rent_yield instead of gold_rent_yield
-- - api_estate_daily instead of gold_estate_daily
-- - api_rent_daily instead of gold_rent_daily, if rent history is used later
--
-- begin;
--
-- revoke select on public.gold_estate_current from anon, authenticated;
-- revoke select on public.gold_rent_current from anon, authenticated;
-- revoke select on public.gold_rent_yield from anon, authenticated;
--
-- Optional but recommended before opening the API broadly:
-- revoke select on public.raw_links from anon, authenticated;
-- revoke select on public.bronze_estate from anon, authenticated;
-- revoke select on public.silver_estate from anon, authenticated;
-- revoke select on public.gold_estate_daily from anon, authenticated;
-- revoke select on public.gold_rent_daily from anon, authenticated;
--
-- commit;
