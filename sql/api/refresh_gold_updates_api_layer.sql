-- Keep the public API layer in sync with the regular Gold refresh.
--
-- Apply in Supabase SQL Editor, or through an admin SQL connection.
-- After applying, run:
--
--     select public.refresh_gold_estate();
--     select public.refresh_gold_rent();
--
-- This keeps Gold as the source of truth and mirrors only aggregated,
-- public-safe rows into api_* tables for dashboard/API consumers.

begin;

create or replace function public.refresh_gold_estate()
returns void
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
begin
    refresh materialized view public.gold_estate_current;

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

create or replace function public.refresh_gold_rent()
returns void
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
begin
    refresh materialized view public.gold_rent_current;

    insert into public.gold_rent_daily (
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
        avg_area_m2
    )
    select
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
        avg_area_m2
    from public.gold_rent_current
    on conflict (date, municipality, city, sector, deal_type)
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_price_per_m2_eur = excluded.avg_price_per_m2_eur,
        median_price_per_m2_eur = excluded.median_price_per_m2_eur,
        avg_area_m2 = excluded.avg_area_m2;

    delete from public.api_rent_current;
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
    from public.gold_rent_current
    on conflict (date, municipality, city, sector, deal_type)
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_price_per_m2_eur = excluded.avg_price_per_m2_eur,
        median_price_per_m2_eur = excluded.median_price_per_m2_eur,
        avg_area_m2 = excluded.avg_area_m2,
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
