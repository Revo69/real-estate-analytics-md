-- Health-check for the Imobil.Index public API layer.
--
-- Run this in Supabase SQL Editor after a pipeline run or security change.
-- Read the status column:
-- - OK: expected state.
-- - CHECK: investigate before treating the public API as healthy.

-- 1. Row counts, snapshot dates, and refresh timestamps.
with table_stats as (
    select
        'gold_estate_current'::text as object_name,
        count(*)::bigint as rows_count,
        max(date)::date as max_date,
        null::timestamptz as max_refreshed_at
    from public.gold_estate_current
    union all
    select
        'api_estate_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_current
    union all
    select
        'gold_estate_daily',
        count(*)::bigint,
        max(date)::date,
        null::timestamptz
    from public.gold_estate_daily
    union all
    select
        'api_estate_daily',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_daily
    union all
    select
        'api_estate_segments_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_segments_current
    union all
    select
        'api_estate_segments_daily',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_segments_daily
    union all
    select
        'api_estate_housing_type_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_housing_type_current
    union all
    select
        'api_estate_condition_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_condition_current
    union all
    select
        'api_estate_floor_position_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_estate_floor_position_current
    union all
    select
        'gold_rent_current',
        count(*)::bigint,
        max(date)::date,
        null::timestamptz
    from public.gold_rent_current
    union all
    select
        'api_rent_current',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_rent_current
    union all
    select
        'gold_rent_daily',
        count(*)::bigint,
        max(date)::date,
        null::timestamptz
    from public.gold_rent_daily
    union all
    select
        'api_rent_daily',
        count(*)::bigint,
        max(date)::date,
        max(refreshed_at)
    from public.api_rent_daily
    union all
    select
        'gold_rent_yield',
        count(*)::bigint,
        null::date,
        null::timestamptz
    from public.gold_rent_yield
    union all
    select
        'api_rent_yield',
        count(*)::bigint,
        null::date,
        max(refreshed_at)
    from public.api_rent_yield
)
select
    object_name,
    rows_count,
    max_date,
    max_refreshed_at
from table_stats
order by object_name;

-- 2. Gold vs API freshness and row parity.
with table_stats as (
    select
        'gold_estate_current'::text as object_name,
        count(*)::bigint as rows_count,
        max(date)::date as max_date
    from public.gold_estate_current
    union all
    select 'api_estate_current', count(*)::bigint, max(date)::date
    from public.api_estate_current
    union all
    select 'gold_estate_daily', count(*)::bigint, max(date)::date
    from public.gold_estate_daily
    union all
    select 'api_estate_daily', count(*)::bigint, max(date)::date
    from public.api_estate_daily
    union all
    select 'api_estate_segments_current', count(*)::bigint, max(date)::date
    from public.api_estate_segments_current
    union all
    select 'api_estate_segments_daily', count(*)::bigint, max(date)::date
    from public.api_estate_segments_daily
    union all
    select 'api_estate_housing_type_current', count(*)::bigint, max(date)::date
    from public.api_estate_housing_type_current
    union all
    select 'api_estate_condition_current', count(*)::bigint, max(date)::date
    from public.api_estate_condition_current
    union all
    select 'api_estate_floor_position_current', count(*)::bigint, max(date)::date
    from public.api_estate_floor_position_current
    union all
    select 'gold_rent_current', count(*)::bigint, max(date)::date
    from public.gold_rent_current
    union all
    select 'api_rent_current', count(*)::bigint, max(date)::date
    from public.api_rent_current
    union all
    select 'gold_rent_daily', count(*)::bigint, max(date)::date
    from public.gold_rent_daily
    union all
    select 'api_rent_daily', count(*)::bigint, max(date)::date
    from public.api_rent_daily
    union all
    select 'gold_rent_yield', count(*)::bigint, null::date
    from public.gold_rent_yield
    union all
    select 'api_rent_yield', count(*)::bigint, null::date
    from public.api_rent_yield
)
select
    check_name,
    case when passed then 'OK' else 'CHECK' end as status,
    details
from (
    select
        'estate current matches Gold'::text as check_name,
        api.max_date = gold.max_date
            and api.rows_count = gold.rows_count as passed,
        format(
            'gold date=%s rows=%s; api date=%s rows=%s',
            gold.max_date,
            gold.rows_count,
            api.max_date,
            api.rows_count
        ) as details
    from table_stats gold
    join table_stats api on api.object_name = 'api_estate_current'
    where gold.object_name = 'gold_estate_current'

    union all
    select
        'estate daily matches Gold',
        api.max_date = gold.max_date
            and api.rows_count = gold.rows_count,
        format(
            'gold date=%s rows=%s; api date=%s rows=%s',
            gold.max_date,
            gold.rows_count,
            api.max_date,
            api.rows_count
        )
    from table_stats gold
    join table_stats api on api.object_name = 'api_estate_daily'
    where gold.object_name = 'gold_estate_daily'

    union all
    select
        'estate segments are current',
        api.max_date = gold.max_date
            and api.rows_count > 0,
        format(
            'gold date=%s; api date=%s rows=%s',
            gold.max_date,
            api.max_date,
            api.rows_count
        )
    from table_stats api
    join table_stats gold on gold.object_name = 'gold_estate_current'
    where api.object_name = 'api_estate_segments_current'

    union all
    select
        'estate segment history has latest snapshot',
        api.max_date = gold.max_date
            and api.rows_count > 0,
        format(
            'gold date=%s; api date=%s rows=%s',
            gold.max_date,
            api.max_date,
            api.rows_count
        )
    from table_stats api
    join table_stats gold on gold.object_name = 'gold_estate_current'
    where api.object_name = 'api_estate_segments_daily'

    union all
    select
        'estate housing types are current',
        api.max_date = gold.max_date
            and api.rows_count > 0,
        format(
            'gold date=%s; api date=%s rows=%s',
            gold.max_date,
            api.max_date,
            api.rows_count
        )
    from table_stats api
    join table_stats gold on gold.object_name = 'gold_estate_current'
    where api.object_name = 'api_estate_housing_type_current'

    union all
    select
        'estate conditions are current',
        api.max_date = gold.max_date
            and api.rows_count > 0,
        format(
            'gold date=%s; api date=%s rows=%s',
            gold.max_date,
            api.max_date,
            api.rows_count
        )
    from table_stats api
    join table_stats gold on gold.object_name = 'gold_estate_current'
    where api.object_name = 'api_estate_condition_current'

    union all
    select
        'estate floor positions are current',
        api.max_date = gold.max_date
            and api.rows_count > 0,
        format(
            'gold date=%s; api date=%s rows=%s',
            gold.max_date,
            api.max_date,
            api.rows_count
        )
    from table_stats api
    join table_stats gold on gold.object_name = 'gold_estate_current'
    where api.object_name = 'api_estate_floor_position_current'

    union all
    select
        'rent current matches Gold',
        api.max_date = gold.max_date
            and api.rows_count = gold.rows_count,
        format(
            'gold date=%s rows=%s; api date=%s rows=%s',
            gold.max_date,
            gold.rows_count,
            api.max_date,
            api.rows_count
        )
    from table_stats gold
    join table_stats api on api.object_name = 'api_rent_current'
    where gold.object_name = 'gold_rent_current'

    union all
    select
        'rent daily matches Gold',
        api.max_date = gold.max_date
            and api.rows_count = gold.rows_count,
        format(
            'gold date=%s rows=%s; api date=%s rows=%s',
            gold.max_date,
            gold.rows_count,
            api.max_date,
            api.rows_count
        )
    from table_stats gold
    join table_stats api on api.object_name = 'api_rent_daily'
    where gold.object_name = 'gold_rent_daily'

    union all
    select
        'rent yield row count matches Gold',
        api.rows_count = gold.rows_count,
        format(
            'gold rows=%s; api rows=%s',
            gold.rows_count,
            api.rows_count
        )
    from table_stats gold
    join table_stats api on api.object_name = 'api_rent_yield'
    where gold.object_name = 'gold_rent_yield'
) checks
order by check_name;

-- 3. Public API table access model.
with api_tables(table_name) as (
    values
        ('api_estate_current'),
        ('api_estate_daily'),
        ('api_estate_segments_current'),
        ('api_estate_segments_daily'),
        ('api_estate_housing_type_current'),
        ('api_estate_condition_current'),
        ('api_estate_floor_position_current'),
        ('api_rent_current'),
        ('api_rent_daily'),
        ('api_rent_yield')
),
access_checks as (
    select
        t.table_name,
        c.relrowsecurity as rls_enabled,
        has_table_privilege('anon', 'public.' || t.table_name, 'select')
            as anon_select,
        has_table_privilege('authenticated', 'public.' || t.table_name, 'select')
            as authenticated_select,
        has_table_privilege('anon', 'public.' || t.table_name, 'insert')
            or has_table_privilege('anon', 'public.' || t.table_name, 'update')
            or has_table_privilege('anon', 'public.' || t.table_name, 'delete')
            as anon_write,
        has_table_privilege(
            'authenticated',
            'public.' || t.table_name,
            'insert'
        )
            or has_table_privilege(
                'authenticated',
                'public.' || t.table_name,
                'update'
            )
            or has_table_privilege(
                'authenticated',
                'public.' || t.table_name,
                'delete'
            )
            as authenticated_write,
        exists (
            select 1
            from pg_policies p
            where p.schemaname = 'public'
              and p.tablename = t.table_name
              and p.cmd = 'SELECT'
              and 'anon' = any(p.roles)
              and 'authenticated' = any(p.roles)
        ) as has_public_select_policy
    from api_tables t
    join pg_class c on c.relname = t.table_name
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
)
select
    table_name,
    case
        when rls_enabled
             and anon_select
             and authenticated_select
             and not anon_write
             and not authenticated_write
             and has_public_select_policy
        then 'OK'
        else 'CHECK'
    end as status,
    rls_enabled,
    anon_select,
    authenticated_select,
    anon_write,
    authenticated_write,
    has_public_select_policy
from access_checks
order by table_name;

-- 4. Internal objects should stay closed for public roles.
with internal_objects(object_name) as (
    values
        ('public.raw_links'),
        ('public.bronze_estate'),
        ('public.silver_estate'),
        ('public.gold_estate_daily'),
        ('public.gold_rent_daily'),
        ('public.gold_estate_current'),
        ('public.gold_rent_current'),
        ('public.gold_rent_yield'),
        ('public.pipeline_runs')
),
access_checks as (
    select
        object_name,
        has_table_privilege('anon', object_name, 'select') as anon_select,
        has_table_privilege(
            'authenticated',
            object_name,
            'select'
        ) as authenticated_select,
        has_table_privilege('service_role', object_name, 'select')
            as service_select,
        has_table_privilege('anon', object_name, 'insert')
            or has_table_privilege('anon', object_name, 'update')
            or has_table_privilege('anon', object_name, 'delete')
            or has_table_privilege('anon', object_name, 'truncate')
            or has_table_privilege('anon', object_name, 'references')
            or has_table_privilege('anon', object_name, 'trigger')
            or has_table_privilege('anon', object_name, 'maintain')
            as anon_non_select,
        has_table_privilege('authenticated', object_name, 'insert')
            or has_table_privilege('authenticated', object_name, 'update')
            or has_table_privilege('authenticated', object_name, 'delete')
            or has_table_privilege('authenticated', object_name, 'truncate')
            or has_table_privilege('authenticated', object_name, 'references')
            or has_table_privilege('authenticated', object_name, 'trigger')
            or has_table_privilege('authenticated', object_name, 'maintain')
            as authenticated_non_select
    from internal_objects
)
select
    object_name,
    case
        when not anon_select
             and not authenticated_select
             and not anon_non_select
             and not authenticated_non_select
             and service_select
        then 'OK'
        else 'CHECK'
    end as status,
    anon_select,
    authenticated_select,
    anon_non_select,
    authenticated_non_select,
    service_select
from access_checks
order by object_name;

-- 5. Refresh functions should stay private, use invoker rights, sync API
-- tables, and keep a fixed search_path.
with functions(function_name, expected_api_marker) as (
    values
        ('refresh_gold_estate', 'api_estate_current'),
        ('refresh_gold_rent', 'api_rent_current')
),
function_checks as (
    select
        f.function_name,
        p.oid,
        not p.prosecdef as security_invoker,
        p.proconfig,
        lower(pg_get_functiondef(p.oid)) as function_definition,
        f.expected_api_marker,
        has_function_privilege('anon', p.oid, 'execute') as anon_execute,
        has_function_privilege('authenticated', p.oid, 'execute')
            as authenticated_execute,
        has_function_privilege('service_role', p.oid, 'execute')
            as service_execute
    from functions f
    join pg_proc p on p.proname = f.function_name
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
)
select
    function_name,
    case
        when security_invoker
             and not anon_execute
             and not authenticated_execute
             and service_execute
             and proconfig @> array['search_path=public, pg_temp']
             and position(expected_api_marker in function_definition) > 0
             and position('api_rent_yield' in function_definition) > 0
             and (
                 function_name <> 'refresh_gold_estate'
                 or position(
                     'api_estate_segments_current' in function_definition
                 ) > 0
             )
             and (
                 function_name <> 'refresh_gold_estate'
                 or position(
                     'api_estate_segments_daily' in function_definition
                 ) > 0
             )
             and (
                 function_name <> 'refresh_gold_estate'
                 or position(
                     'api_estate_housing_type_current' in function_definition
                 ) > 0
             )
             and (
                 function_name <> 'refresh_gold_estate'
                 or position(
                     'api_estate_condition_current' in function_definition
                 ) > 0
             )
             and (
                 function_name <> 'refresh_gold_estate'
                 or position(
                     'api_estate_floor_position_current' in function_definition
                 ) > 0
             )
             and position('truncate table' in function_definition) = 0
        then 'OK'
        else 'CHECK'
    end as status,
    security_invoker,
    anon_execute,
    authenticated_execute,
    service_execute,
    proconfig,
    position(expected_api_marker in function_definition) > 0 as updates_main_api,
    position('api_estate_segments_current' in function_definition) > 0
        as updates_estate_segments_api,
    position('api_estate_segments_daily' in function_definition) > 0
        as updates_estate_segment_history_api,
    position('api_estate_housing_type_current' in function_definition) > 0
        as updates_estate_housing_type_api,
    position('api_estate_condition_current' in function_definition) > 0
        as updates_estate_condition_api,
    position('api_estate_floor_position_current' in function_definition) > 0
        as updates_estate_floor_position_api,
    position('api_rent_yield' in function_definition) > 0 as updates_yield_api,
    position('truncate table' in function_definition) > 0 as uses_truncate
from function_checks
order by function_name;

-- 6. New producer-owned objects should not inherit public access. Supabase
-- platform objects owned by supabase_admin are outside this repository's ACL.
with expected_defaults(object_type, object_label) as (
    values
        ('r'::"char", 'tables'),
        ('S'::"char", 'sequences'),
        ('f'::"char", 'functions')
),
default_access_checks as (
    select
        e.object_label,
        exists (
            select 1
            from pg_default_acl d
            join pg_roles owner_role on owner_role.oid = d.defaclrole
            join pg_namespace n on n.oid = d.defaclnamespace
            cross join lateral aclexplode(d.defaclacl) a
            left join pg_roles grantee_role on grantee_role.oid = a.grantee
            where owner_role.rolname = 'postgres'
              and n.nspname = 'public'
              and d.defaclobjtype = e.object_type
              and (
                  a.grantee = 0
                  or grantee_role.rolname in ('anon', 'authenticated')
              )
        ) as has_public_default
    from expected_defaults e
)
select
    object_label,
    case when not has_public_default then 'OK' else 'CHECK' end as status,
    has_public_default
from default_access_checks
order by object_label;
