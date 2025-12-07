-- Gold layer schema

-- 1. Ежедневная история
create table if not exists gold_estate_daily (
    date date not null,
    municipality text,
    city text,
    sector text,
    listings int,
    avg_price_eur numeric(10,2),
    median_price_eur numeric(12,2),
    avg_per_m2_eur numeric(10,2),
    created_at timestamp default now(),
    primary key (date, municipality, city, sector)
);

-- 2. Актуальная статистика (материализованное представление)
create materialized view if not exists gold_estate_current as
select
    current_date as date,
    municipality,
    city,
    sector,
    count(*) as listings,
    round(avg(price_eur)) as avg_price_eur,
    round(percentile_cont(0.5) within group (order by price_eur)) as median_price_eur,
    round(avg(price_eur / nullif(total_area_m2, 0))) as avg_per_m2_eur
from silver_estate
where 
    status = 'active'
    and deal_type = 'Продам'
    and price_eur >= 1000
    and total_area_m2 between 20 and 400
    and publication_date >= current_date - interval '60 days'
group by municipality, city, sector
having count(*) >= 5;

-- 3. Функция обновления
create or replace function refresh_gold_estate()
returns void as $$
begin
    refresh materialized view gold_estate_current;
    
    insert into gold_estate_daily
    select * from gold_estate_current
    on conflict (date, municipality, city, sector) 
    do update set
        listings = excluded.listings,
        avg_price_eur = excluded.avg_price_eur,
        median_price_eur = excluded.median_price_eur,
        avg_per_m2_eur = excluded.avg_per_m2_eur;
end;
$$ language plpgsql;
