-- Least-privilege hardening for the Estate MD producer boundary.
--
-- Apply manually in the Supabase SQL Editor as the postgres owner only after
-- reviewing the production metadata. This script changes ACLs only: it does
-- not refresh, insert, update, delete, or truncate application data.
--
-- Preconditions:
-- - the dashboard reads only the ten public.api_* tables;
-- - the pipeline uses service_role for internal writes and refresh RPCs;
-- - public.refresh_gold_estate() and public.refresh_gold_rent() exist with no
--   arguments.

begin;

-- Existing internal relations. RLS remains defense in depth, but public roles
-- should not retain redundant table privileges.
revoke all privileges on table public.raw_links
    from anon, authenticated;
revoke all privileges on table public.bronze_estate
    from anon, authenticated;
revoke all privileges on table public.silver_estate
    from anon, authenticated;
revoke all privileges on table public.gold_estate_daily
    from anon, authenticated;
revoke all privileges on table public.gold_rent_daily
    from anon, authenticated;
revoke all privileges on table public.gold_estate_current
    from anon, authenticated;
revoke all privileges on table public.gold_rent_current
    from anon, authenticated;
revoke all privileges on table public.gold_rent_yield
    from anon, authenticated;
revoke all privileges on table public.pipeline_runs
    from anon, authenticated;

-- Refresh functions are producer operations, not public API endpoints.
revoke execute on function public.refresh_gold_estate()
    from public, anon, authenticated;
revoke execute on function public.refresh_gold_rent()
    from public, anon, authenticated;

grant execute on function public.refresh_gold_estate() to service_role;
grant execute on function public.refresh_gold_rent() to service_role;

-- Future objects created by the project's postgres owner start private.
-- Public api_* objects must receive explicit SELECT grants and RLS policies in
-- their reviewed rollout scripts. Supabase-managed supabase_admin defaults are
-- intentionally not changed here.
alter default privileges for role postgres in schema public
    revoke all privileges on tables from anon, authenticated;
alter default privileges for role postgres in schema public
    revoke all privileges on sequences from anon, authenticated;
alter default privileges for role postgres in schema public
    revoke execute on functions from public, anon, authenticated;

commit;

-- Verification after application:
-- 1. Run sql/api/check_public_api_layer.sql; every access status must be OK.
-- 2. Run Imobil-Index/scripts/check_api_health.py with its anon credential.
-- 3. Confirm direct anon reads of internal objects still fail with 42501.
-- 4. Run Supabase security and performance advisors.
