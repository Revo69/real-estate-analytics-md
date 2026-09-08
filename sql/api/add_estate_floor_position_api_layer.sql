-- Add the current floor-position comparison to the public API.
--
-- This table exposes only aggregated sale metrics. It never publishes raw
-- listings, source URLs, seller data, descriptions, or listing identifiers.
--
-- After applying, run:
--
--     select public.refresh_gold_estate();

begin;

create table if not exists public.api_estate_floor_position_current (
    date date not null,
    municipality text not null,
    city text not null,
    sector text not null,
    floor_position text not null check (
        floor_position in ('Ground floor', 'Middle floor', 'Top floor')
    ),
    listings bigint not null,
    avg_price_eur numeric,
    median_price_eur numeric,
    avg_per_m2_eur numeric,
    refreshed_at timestamp with time zone not null default now(),
    primary key (date, municipality, city, sector, floor_position)
);

create index if not exists api_estate_floor_position_city_idx
    on public.api_estate_floor_position_current (city, floor_position);

alter table public.api_estate_floor_position_current enable row level security;

drop policy if exists "Public can read estate floor position API data"
    on public.api_estate_floor_position_current;
create policy "Public can read estate floor position API data"
    on public.api_estate_floor_position_current
    for select
    to anon, authenticated
    using (true);

grant select on public.api_estate_floor_position_current to anon, authenticated;
grant select, insert, update, delete
    on public.api_estate_floor_position_current to service_role;

revoke insert, update, delete, truncate, references, trigger
    on public.api_estate_floor_position_current from anon, authenticated;

comment on table public.api_estate_floor_position_current is
    'Public API table with aggregated current sale metrics by floor position.';

-- Keep the existing refresh function intact and insert one narrowly scoped
-- block before its yield refresh. The guards make this migration idempotent
-- and fail loudly if the expected function shape has changed.
do $migration$
declare
    function_definition text;
    refresh_block text := $floor_refresh$
    delete from public.api_estate_floor_position_current;
    insert into public.api_estate_floor_position_current (
        date,
        municipality,
        city,
        sector,
        floor_position,
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
            when floor = 1 then 'Ground floor'
            when floor = total_floors then 'Top floor'
            else 'Middle floor'
        end as floor_position,
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
      and floor is not null
      and total_floors is not null
      and floor >= 1
      and total_floors >= floor
    group by municipality, city, sector, floor_position
    having count(*) >= 5;

$floor_refresh$;
begin
    select pg_get_functiondef(p.oid)
    into function_definition
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'refresh_gold_estate'
      and pg_get_function_identity_arguments(p.oid) = '';

    if function_definition is null then
        raise exception 'public.refresh_gold_estate() was not found';
    end if;

    if position('api_estate_floor_position_current' in function_definition) > 0 then
        return;
    end if;

    if position('    delete from public.api_rent_yield;' in function_definition) = 0 then
        raise exception 'refresh_gold_estate() does not contain the expected yield refresh marker';
    end if;

    function_definition := replace(
        function_definition,
        '    delete from public.api_rent_yield;',
        refresh_block || '    delete from public.api_rent_yield;'
    );
    execute function_definition;
end;
$migration$;

commit;
