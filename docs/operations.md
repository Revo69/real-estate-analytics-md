# Operations Runbook

This runbook describes the current production workflow and safe diagnostic
steps. It does not authorize changing live data or database definitions.

## Schedule and execution

- Workflow: `.github/workflows/pipeline.yml`
- Name: `Real Estate Pipeline`
- Schedule: daily at `01:00 UTC`
- Manual trigger: `workflow_dispatch`
- Runtime: Python 3.11 on GitHub-hosted Ubuntu runners

The workflow uses one concurrency group:

```yaml
concurrency:
  group: real-estate-pipeline
  cancel-in-progress: false
```

A new scheduled run waits rather than interrupting an active scrape.

## Job chain

| Job | Current action | Success evidence |
|---|---|---|
| `collect-links` | Scan listing pages 1–30 and insert unseen numeric URLs into `raw_links`. | Step outcome is success; discovered/new counts reach `pipeline_runs`; logs are uploaded. |
| `parse-bronze` | Run six sequential passes over the next 500 pending links. | All six original step outcomes are success; Bronze logs are uploaded. |
| `silver` | Read Bronze, normalize all records, and upsert `silver_estate`. | Command exits zero and the next stage becomes Gold. |
| `gold` | Call sales and rent refresh RPCs and finish the run. | Both RPCs succeed, `gold_refreshed=true`, terminal status is `succeeded`. |
| `notify-on-failure` | Send a Telegram message when any required job fails. | Notification step exits zero; it does not convert a failed pipeline to success. |

The workflow's link-step label still says pages 1–50 while the command currently
uses `--end 30`. Treat the command as the actual behavior until the label is
corrected in a separate workflow change.

## Required secrets

GitHub Actions uses:

- `SUPABASE_URL`;
- `SUPABASE_KEY` — server-side pipeline key;
- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_CHAT_ID`.

Never place values in documentation, logs, screenshots, shell history, issue
text, or the public dashboard repository. When debugging configuration, report
only whether each variable is present.

## Normal successful run

Check these signals together:

1. GitHub Actions shows every required job green.
2. `pipeline_runs.status` is `succeeded`.
3. `finished_at` is set, `current_stage` is null, and `failed_stage` is null.
4. `gold_refreshed` is true.
5. The public `api_*` tables report the expected latest snapshot date.
6. The dashboard renders that snapshot without a data-connection error.

A green HTTP response or green artifact-upload step alone is insufficient.

At the 2026-09-08 audit, the five latest pipeline runs were successful and all
ten public API tables were non-empty and fresh to 2026-09-07. This is a dated
verification snapshot, not a permanent guarantee.

## Run metadata

`public.pipeline_runs` is the operational run ledger. One GitHub workflow
attempt uses:

```text
github-{GITHUB_RUN_ID}-attempt-{GITHUB_RUN_ATTEMPT}
```

Important fields include:

- start/end timestamps and terminal status;
- current or failed stage;
- discovered and newly inserted link counts;
- Bronze and Silver processing counters;
- Gold refresh flag;
- Git SHA and GitHub run identifiers;
- a bounded error message.

Known current limitation: recent successful rows contain useful link counts and
`gold_refreshed=true`, but Bronze/Silver counters remain zero because the loaders
do not update them yet.

## Logs and artifacts

| Area | Local log | Workflow artifact |
|---|---|---|
| Acquisition | `logs/links_loader.log` | `links-loader-logs` |
| Bronze | `logs/bronze_loader.log` | `bronze-loader-logs` |
| Silver | `logs/silver_loader_supabase.log` | Not uploaded separately today. |
| Gold wrapper | `logs/run_gold.log` | `gold-loader-logs` |

Artifacts are retained for seven days. Failed acquisition pages may also write
`logs/links_page_<page>_failed.png`.

For source-loading failures, inspect:

- the failed page number;
- page title and current URL;
- HTML length;
- whether numeric listing links appeared;
- the saved screenshot;
- consecutive and total failed-page counts.

Do not infer CAPTCHA, blocking, or browser mismatch from a timeout alone.

## Failure semantics

The collector and each Bronze iteration use `continue-on-error: true` so their
logs can still be processed and uploaded. A later validation step checks
`steps.<id>.outcome`; if the original command failed, validation exits non-zero.
Do not replace `outcome` with `conclusion`.

Silver has no `continue-on-error`. Gold catches individual RPC failures only to
attempt both refreshes and preserve diagnostics; it then raises when either one
failed. Downstream jobs depend on upstream success.

## Stale `running` records

A manually cancelled or interrupted workflow may stop before Python calls
`finish_run()`. At the 2026-09-08 audit, eight historical rows were still marked
`running`.

Until automated cleanup is implemented:

1. identify the row by `github_run_id` and `github_run_attempt`;
2. open the corresponding GitHub Actions run;
3. confirm that no job is still active and record its terminal GitHub state;
4. do not update the database row merely because it is old;
5. record confirmed abandoned rows for the planned cleanup task.

The planned policy will close rows older than 12 hours at the next acquisition
run while leaving recent active rows untouched. That behavior is not implemented
yet.

## Public API freshness check

The current read-only health script lives in the downstream repository:

```powershell
cd ..\Imobil-Index
.\.venv\Scripts\python.exe -B scripts\check_api_health.py
```

It checks that all ten expected `api_*` tables can be read and reports their row
counts and latest snapshot/refreshed timestamps. It must use public dashboard
credentials, not the pipeline service key.

This smoke check does not prove that public writes are denied or internal tables
are closed. After access or schema changes, separately verify RLS, policies,
grants/revokes, function definitions and `search_path`, plus Supabase Security
and Performance Advisors.

## Local recovery boundaries

- Retry a failed workflow only after identifying whether the cause is source
  instability, code, credentials, runner/browser setup, or Supabase.
- Preserve logs before changing retry counts or timeouts.
- Do not silently mark a failed or cancelled run successful.
- Do not manually set `gold_refreshed=true` without evidence that both refresh
  functions completed.
- Do not weaken RLS or expose internal tables to make the dashboard work.
- Do not deploy SQL based only on the tracked legacy Gold schema; first compare
  it with current production definitions.
