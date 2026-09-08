-- Close public access to internal Imobil.Index objects after app.py cutover.
--
-- Prerequisites:
-- - Streamlit dashboard has been verified on api_* tables.
-- - api_* tables are readable by anon/authenticated.
-- - pipeline uses service_role or another private role for internal objects.

begin;

revoke select on public.gold_estate_current from anon, authenticated;
revoke select on public.gold_rent_current from anon, authenticated;
revoke select on public.gold_rent_yield from anon, authenticated;

revoke select on public.raw_links from anon, authenticated;
revoke select on public.bronze_estate from anon, authenticated;
revoke select on public.silver_estate from anon, authenticated;
revoke select on public.gold_estate_daily from anon, authenticated;
revoke select on public.gold_rent_daily from anon, authenticated;

commit;

-- Verification:
--
-- select object_name,
--        has_table_privilege('anon', object_name, 'select') as anon_select,
--        has_table_privilege(
--            'authenticated', object_name, 'select'
--        ) as authenticated_select,
--        has_table_privilege('service_role', object_name, 'select') as service_select
-- from (values
--   ('public.raw_links'),
--   ('public.bronze_estate'),
--   ('public.silver_estate'),
--   ('public.gold_estate_daily'),
--   ('public.gold_rent_daily'),
--   ('public.gold_estate_current'),
--   ('public.gold_rent_current'),
--   ('public.gold_rent_yield'),
--   ('public.api_estate_current'),
--   ('public.api_estate_daily'),
--   ('public.api_rent_current'),
--   ('public.api_rent_daily'),
--   ('public.api_rent_yield')
-- ) as objects(object_name)
-- order by object_name;

