-- Add profile-level sale history to the public API layer.
--
-- This table stores daily snapshots of aggregated sale metrics by rooms and
-- area band. It does not expose listing-level data, URLs, descriptions,
-- authors, or source IDs.
--
-- Requires:
-- - public.api_estate_segments_current already exists;
-- - public.refresh_gold_estate() is maintained from this project.

begin;

create table if not exists public.api_estate_segments_daily (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    rooms_group text not null,
    area_band text not null,
    listings bigint not null,
    avg_price_eur numeric,
    median_price_eur numeric,
    avg_per_m2_eur numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (
        date,
        municipality,
        city,
        sector,
        rooms_group,
        area_band
    )
);

create index if not exists api_estate_segments_daily_date_city_idx
    on public.api_estate_segments_daily (date desc, city);

create index if not exists api_estate_segments_daily_profile_idx
    on public.api_estate_segments_daily (rooms_group, area_band);

alter table public.api_estate_segments_daily enable row level security;

drop policy if exists "Public can read estate segment history API data"
    on public.api_estate_segments_daily;
create policy "Public can read estate segment history API data"
    on public.api_estate_segments_daily
    for select
    to anon, authenticated
    using (true);

grant select on public.api_estate_segments_daily to anon, authenticated;
grant select, insert, update, delete
    on public.api_estate_segments_daily to service_role;

revoke insert, update, delete, truncate, references, trigger
    on public.api_estate_segments_daily from anon, authenticated;

comment on table public.api_estate_segments_daily is
    'Public API table with aggregated sale-profile history by rooms and area band.';

-- Seed the history table with the current profile snapshot, if it already
-- exists. Older profile snapshots cannot be reconstructed honestly from the
-- current public layer.
insert into public.api_estate_segments_daily (
    date,
    municipality,
    city,
    sector,
    rooms_group,
    area_band,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    refreshed_at
)
select
    date,
    municipality,
    city,
    sector,
    rooms_group,
    area_band,
    listings,
    avg_price_eur,
    median_price_eur,
    avg_per_m2_eur,
    now()
from public.api_estate_segments_current
on conflict (date, municipality, city, sector, rooms_group, area_band)
do update set
    listings = excluded.listings,
    avg_price_eur = excluded.avg_price_eur,
    median_price_eur = excluded.median_price_eur,
    avg_per_m2_eur = excluded.avg_per_m2_eur,
    refreshed_at = excluded.refreshed_at;

create or replace function public.refresh_gold_estate()
returns void
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
declare
    snapshot_date date;
begin
    refresh materialized view public.gold_estate_current;

    select coalesce(max(date), current_date)
    into snapshot_date
    from public.gold_estate_current;

    insert into public.gold_estate_daily (
        date,
        municipality,
        city,
        sector,
        listings,
        avg_price_eur,
        median_price_eur,
        avg_per_m2_eur
    )
    select
        date,
        municipality,
        city,
        sector,
        listings,
        avg_price_eur,
        median_price_eur,
        avg_per_m2_eur
    from public.gold_estate_current
    on conflict (date, municipality, city, sector)
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_per_m2_eur = excluded.avg_per_m2_eur;

    delete from public.api_estate_current;
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
    from public.gold_estate_current
    on conflict (date, municipality, city, sector)
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_per_m2_eur = excluded.avg_per_m2_eur,
        refreshed_at = excluded.refreshed_at;

    delete from public.api_estate_segments_current;
    insert into public.api_estate_segments_current (
        date,
        municipality,
        city,
        sector,
        rooms_group,
        area_band,
        listings,
        avg_price_eur,
        median_price_eur,
        avg_per_m2_eur,
        refreshed_at
    )
    select
        snapshot_date,
        coalesce(municipality, 'Unknown'),
        coalesce(city, 'Unknown'),
        coalesce(sector, 'Center'),
        case
            when number_of_rooms >= 4 then '4+'
            else number_of_rooms::text
        end as rooms_group,
        case
            when total_area_m2 < 40 then '<40 m2'
            when total_area_m2 < 60 then '40-59 m2'
            when total_area_m2 < 80 then '60-79 m2'
            when total_area_m2 < 120 then '80-119 m2'
            else '120+ m2'
        end as area_band,
        count(*)::bigint as listings,
        round(avg(price_eur)) as avg_price_eur,
        round(
            percentile_cont(0.5) within group (
                order by price_eur::double precision
            )::numeric
        ) as median_price_eur,
        round(avg(price_eur / nullif(total_area_m2, 0))) as avg_per_m2_eur,
        now()
    from public.silver_estate
    where status = 'success'
      and deal_type = 'Продам'
      and price_eur >= 1000
      and total_area_m2 >= 20
      and total_area_m2 <= 400
      and publication_date >= (snapshot_date - interval '60 days')
      and (price_eur / nullif(total_area_m2, 0)) >= 180
      and (price_eur / nullif(total_area_m2, 0)) <= 10000
      and number_of_rooms is not null
      and number_of_rooms >= 1
    group by
        municipality,
        city,
        sector,
        rooms_group,
        area_band
    having count(*) >= 5;

    insert into public.api_estate_segments_daily (
        date,
        municipality,
        city,
        sector,
        rooms_group,
        area_band,
        listings,
        avg_price_eur,
        median_price_eur,
        avg_per_m2_eur,
        refreshed_at
    )
    select
        date,
        municipality,
        city,
        sector,
        rooms_group,
        area_band,
        listings,
        avg_price_eur,
        median_price_eur,
        avg_per_m2_eur,
        now()
    from public.api_estate_segments_current
    on conflict (date, municipality, city, sector, rooms_group, area_band)
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_per_m2_eur = excluded.avg_per_m2_eur,
        refreshed_at = excluded.refreshed_at;

    delete from public.api_rent_yield;
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
end;
$function$;

commit;

-- Refresh once after applying:
--
-- select public.refresh_gold_estate();
