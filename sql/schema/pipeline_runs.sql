create table if not exists public.pipeline_runs (
    run_id text primary key,
    pipeline_name text not null default 'real-estate-pipeline',

    status text not null default 'running'
        check (status in ('running', 'succeeded', 'failed')),
    current_stage text,
    failed_stage text,

    started_at timestamptz not null default now(),
    finished_at timestamptz,

    links_discovered integer not null default 0
        check (links_discovered >= 0),
    new_links integer not null default 0
        check (new_links >= 0),
    bronze_loaded integer not null default 0
        check (bronze_loaded >= 0),
    silver_success integer not null default 0
        check (silver_success >= 0),
    silver_partial integer not null default 0
        check (silver_partial >= 0),
    silver_failed integer not null default 0
        check (silver_failed >= 0),
    rejected_count integer not null default 0
        check (rejected_count >= 0),

    gold_refreshed boolean not null default false,
    error_message text,

    git_sha text,
    github_run_id bigint,
    github_run_attempt integer,

    constraint pipeline_runs_completion_check check (
        (status = 'running' and finished_at is null)
        or
        (status in ('succeeded', 'failed') and finished_at is not null)
    )
);

create index if not exists pipeline_runs_started_at_idx
    on public.pipeline_runs (started_at desc);

alter table public.pipeline_runs enable row level security;

revoke all on table public.pipeline_runs from anon, authenticated;

grant select, insert, update on table public.pipeline_runs to service_role;

comment on table public.pipeline_runs is
    'Operational metadata for end-to-end real-estate pipeline executions.';