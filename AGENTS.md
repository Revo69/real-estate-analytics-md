# AGENTS.md

Project guide for AI-assisted work on `real-estate-analytics-md`.

## Project snapshot

- Purpose: daily data pipeline for Moldova real-estate listings from 999.md.
- Runtime: Python 3.11 in GitHub Actions.
- Storage: Supabase/PostgreSQL.
- Flow: `raw_links -> bronze_estate -> silver_estate -> Gold -> api_*`.
- Consumer: the separate `Imobil-Index` Streamlit dashboard.
- Orchestrator: `.github/workflows/pipeline.yml`.
- Durable work log: `PROGRESS.md`.

## Working style

1. Read `AGENTS.md`, `PROGRESS.md`, `README.md`, and the relevant code before
   proposing a change.
2. Check `git status` before and after editing; preserve unrelated user work.
3. Inspect current code, workflow runs, database metadata, and logs before
   treating an old note as current fact.
4. Make one focused, reversible change at a time.
5. Run the smallest relevant check, then broader checks proportional to risk.
6. Update `PROGRESS.md` only when verified project state changes materially.
7. Report unavailable checks and environment limitations explicitly.
8. Do not commit, push, deploy, or modify production data without explicit user
   authorization.

## Repository ownership

This repository owns:

- acquisition and parser behavior;
- Bronze, Silver, and Gold transformations;
- pipeline operational metadata and alerts;
- versioned database SQL and refresh functions;
- the producer-side `api_*` contract.

`Imobil-Index` owns Streamlit layout, filters, charts, display transformations,
and public-data consumption. New dashboard features must consume aggregated
`api_*` data rather than internal Raw, Bronze, Silver, or Gold objects.

## Data and product invariants

- Acquisition remains append-only unless the user explicitly approves a new
  listing-history model.
- Do not claim price cuts, delistings, time-on-market, or exact current inventory
  from the current acquisition model.
- Bronze preserves source-shaped text and JSON where normalization would lose
  evidence.
- Silver owns typed normalization and `quality_score`/`normalization_status`.
- Gold and `api_*` grains must be stated before changing an aggregate.
- Dashboard market averages that claim market-wide meaning remain weighted by
  listing count.
- Rent yield remains an indicative gross-yield estimate, not net investment
  return.

## Secrets and Supabase safety

- Never print, commit, or expose `SUPABASE_KEY`, Telegram tokens, or other secret
  values.
- The pipeline uses a server-side Supabase key because it writes internal
  tables. Never copy that key into `Imobil-Index` or another public client.
- RLS alone does not grant or deny table-level Data API access. Verify RLS,
  policies, grants, and revokes together.
- Public roles may read only the intended aggregated `api_*` tables and may not
  write them.
- Internal Raw, Bronze, Silver, Gold, `pipeline_runs`, and future operational
  tables remain unavailable to public roles.
- Before changing production SQL, inspect the live definition and relevant
  Supabase documentation. Verify the applied result and database advisors.
- Keep privileged functions' `search_path` fixed and review function execution
  grants; do not add `SECURITY DEFINER` merely to bypass a permission problem.
- For intentional full-table deletes inside maintained PostgreSQL functions,
  use an explicit `DELETE ... WHERE TRUE`; retain specific predicates for
  conditional deletes.

## Pipeline reliability rules

- Preserve the job chain `collect-links -> parse-bronze -> silver -> gold`.
- Keep `concurrency.group: real-estate-pipeline` with
  `cancel-in-progress: false` unless a different interruption policy is designed.
- A critical stage failure must make the workflow non-zero.
- If `continue-on-error: true` is required to upload diagnostics, validate
  `steps.<id>.outcome`, not `conclusion`, afterward.
- Silver and Gold exceptions must propagate to GitHub Actions.
- Set `gold_refreshed=true` only after both Gold refresh RPCs succeed.
- Preserve `if: always()` on diagnostic artifact uploads.
- Keep Telegram alerts concise and free of secrets or raw listing data.

## 999.md parser rules

- Wait for numeric listing paths matching `AD_HREF_RE`; generic `/ru/` links can
  be navigation rather than listings.
- Preserve timeout diagnostics: page number, title, URL, HTML length, and failed
  page screenshot.
- Keep bounded retry and failure thresholds. Do not turn a source outage into a
  green partial collection silently.
- Do not blame browser-version mismatch without comparative logs from working
  and failing runs.
- A wait for the first listing link does not prove that all cards loaded. Add a
  stable-count wait only after diagnostics demonstrate partial page capture.

## Preferred checks

Use the project environment when it exists. Current baseline commands are:

```powershell
python -m pytest -q
git diff --check
```

The pytest/dev dependency setup and CI test workflow are planned but not yet
implemented. Until then, do not interpret an unavailable pytest command as a
passing suite.

For SQL or API work, also run the relevant schema/access checks and the public
API health check from `Imobil-Index`. A successful HTTP read does not prove
write denial, internal-object closure, function safety, or advisor cleanliness.

## Documentation rules

- `README.md` explains the project publicly.
- `ARCHITECTURE.md` describes the current system and ownership boundaries.
- `PROGRESS.md` records verified state, priorities, and the current next task.
- `docs/operations.md` is the operational runbook.
- `docs/public_api_v1.md` will be the canonical detailed public API contract.
- Avoid copying pipeline implementation details into dashboard documentation.
- Mark historical counts and dates as snapshots; do not present them as current.
