# Estate MD Reliability and Documentation Implementation Plan

> **For agentic workers:** Execute this plan one task at a time. Before every task, inspect the current checkout and database state; after every task, update the checkboxes and verification evidence in this file. Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` only when the user explicitly chooses that execution mode.

**Goal:** Make `real-estate-analytics-md` the reproducible, observable source-of-truth repository for the Moldova real-estate pipeline while keeping `Imobil-Index` a focused Streamlit consumer of the public aggregated API.

**Architecture:** `real-estate-analytics-md` owns acquisition, Bronze, Silver, Gold, operational metadata, database SQL, and the `api_*` producer contract. `Imobil-Index` owns Streamlit presentation and consumes only the aggregated `api_*` contract. Improvements remain incremental: reliability and documentation first, then tests and observability, then data-quality gates; new tools are introduced only when they solve a demonstrated problem.

**Tech Stack:** Python 3.11, Selenium, Supabase/PostgreSQL 17, GitHub Actions, pytest, Streamlit in the downstream repository.

**Spec:** Consolidated from the three user-supplied engineering handoffs, the current checkouts of `real-estate-analytics-md` and `Imobil-Index`, and the repository-ownership decision approved in the 2026-09-07 Codex task.

## Global Constraints

- Keep acquisition append-only: process new listing URLs; do not add price-history, removal tracking, time-on-market, or price-cut claims.
- Keep GitHub Actions as the orchestrator. Do not add Airflow at the current scale.
- Never expose the Supabase `service_role`/secret key to `Imobil-Index` or another public client.
- `Imobil-Index` must continue to read aggregated `api_*` objects only.
- Preserve current Gold and dashboard business semantics, including listing-weighted market calculations and indicative gross-yield wording.
- Make one small, reversible change at a time and verify it before starting the next task.
- Do not change production schema, RLS, grants, refresh functions, or live data from documentation alone; inspect current production metadata first.
- Keep the documentation set small and assign one canonical owner to each fact.

---

## Verified Baseline — 2026-09-08

### Repository and runtime

- [x] `real-estate-analytics-md` is clean on `main` and matches `origin/main` at `3f78223`.
- [x] `Imobil-Index` is clean on `main` and matches `origin/main` at `fd00f13`; the experimental reference redesign was reverted.
- [x] The five most recent public `Real Estate Pipeline` workflow runs completed successfully.
- [x] The ten public `api_*` tables are non-empty and fresh to 2026-09-07.
- [x] The 27 tracked Python files in the pipeline pass an AST syntax parse.
- [x] The dashboard passes 15 unit tests and Ruff.
- [x] Exact pytest/Ruff dev tooling is declared and the local suite passes 64 tests without Supabase credentials.
- [ ] The new test workflow has not yet been verified by a real GitHub Actions run.

### Work already implemented — do not redo

- [x] Workflow dependency chain: `collect-links -> parse-bronze -> silver -> gold`.
- [x] Top-level workflow concurrency with `cancel-in-progress: false`.
- [x] Workflow permission reduced to `contents: read`.
- [x] `continue-on-error` validation uses `steps.<id>.outcome` for link collection and all six Bronze iterations.
- [x] Link and Gold logs are uploaded with `if: always()`.
- [x] Gold refresh exceptions are collected and re-raised as a failing job.
- [x] Successful Gold runs set `gold_refreshed=true` before finishing.
- [x] `pipeline_runs` table and Python start/update/finish helpers exist.
- [x] Telegram failure notification exists.
- [x] Link collection waits for numeric listing URLs, handles stale DOM elements, saves diagnostics/screenshots, and fails after repeated or excessive page failures.
- [x] Parser regression fixtures cover the current stable class-name suffix selectors.
- [x] The public API layer has ten aggregated tables, explicit public read access, no public writes, and current health checks in `Imobil-Index`.
- [x] Direct runtime dependencies are pinned to verified releases; the unused `webdriver-manager` dependency has been removed.

### Confirmed open problems

- [ ] `bronze_loaded`, `silver_success`, `silver_partial`, `silver_failed`, and `rejected_count` remain zero in recent successful `pipeline_runs` rows because loaders never update them.
- [ ] Eight old runs from 2026-08-04 through 2026-08-18 remain incorrectly marked `running`.
- [ ] The pipeline repository does not contain the complete production `api_*` SQL/refresh contract; its current copies live under `Imobil-Index/sql`.
- [x] The pipeline now has canonical root documentation and an operations runbook; detailed API/SQL ownership remains Task 2.
- [ ] Pipeline parser/normalizer tests are not run on push or pull request.
- [x] Silver transformation, normalizer, quality-score, and status-threshold contracts now have deterministic regression coverage.
- [ ] `calculate_quality_score()` reads a missing `region` key while Silver transformation emits `region_raw` plus parsed address fields; fully populated transformed rows therefore currently top out at `0.875`. Any correction requires an explicit Silver data-semantics change and regression update.
- [x] `pipeline/gold/schema.sql` now bootstraps the five current Gold objects and identifies the complete ordered API rollout; existing-database migration and API security remediation remain separate reviewed work.
- [ ] `pipeline/silver/loader.py` re-reads and upserts all Bronze rows each day. This is acceptable at the present scale but is not truly incremental.
- [ ] The link-page wait proves that at least one listing loaded, not that the page reached a stable listing count.
- [ ] Python 3.12+ removes `distutils`, while `undetected-chromedriver 3.5.5` imports it at runtime. Keep production on Python 3.11 until the browser layer passes an isolated import check and a no-write 999.md page smoke test on Python 3.14.

### Runtime and dependency audit — 2026-09-08

- [x] Python 3.14.7 is the current stable CPython release; Python 3.15 is still a release candidate.
- [x] `Imobil-Index` tests on Python 3.13 and reports local development on Python 3.14, but it does not use the pipeline's browser dependency.
- [x] The pipeline's local Python 3.14.6 environment passes all 11 parser tests and imports every direct runtime dependency except `undetected-chromedriver`.
- [x] A clean dependency resolver dry-run accepts all six exact direct pins in `requirements.txt`.
- [x] `webdriver-manager` has no imports or other runtime use in the repository and was removed.
- [ ] Full scraper compatibility on Python 3.14 remains unverified and currently fails at import because `undetected-chromedriver 3.5.5` requires `distutils`.

---

## Target Minimal Documentation Structure

### `real-estate-analytics-md` — canonical producer documentation

```text
README.md                 # public overview, setup, flow, commands, dashboard link
AGENTS.md                 # safe working rules and verification requirements
PROGRESS.md               # this living plan, evidence, and current next step
ARCHITECTURE.md           # current end-to-end architecture and ownership boundaries
docs/
  public_api_v1.md        # canonical api_* contract and grains
  operations.md           # schedule, run metadata, logs, alerts, failure recovery
```

### `Imobil-Index` — consumer documentation

```text
README.md                 # dashboard product and local setup
AGENTS.md                 # Streamlit, UX, data-semantics, and verification rules
PROGRESS.md               # dashboard-only work and parking lot
ARCHITECTURE.md           # Streamlit modules and api_* consumption
```

The dashboard may summarize the input contract, but it must link to the pipeline's canonical `docs/public_api_v1.md` rather than duplicate producer SQL, RLS, refresh, or database-operational documentation.

---

## Priority and Scope Decisions

### Implement now

1. Documentation ownership and reproducible database/API sources.
2. Pipeline dev dependencies and pull-request CI.
3. Unit tests for Silver normalizers, quality thresholds, Gold failure propagation, and run-metadata helpers.
4. Accurate Bronze/Silver counters in `pipeline_runs`.
5. Cleanup policy for abandoned `running` records.
6. A small, evidence-based Data Quality v1 gate before Gold.

### Implement only after an evidence gate

- Stable-listing-count wait: add only after per-page diagnostics demonstrate partial page capture, not merely daily count variation.
- Incremental Silver: add when row count or runtime becomes material, or when row-level lineage is required.
- Additional Silver `CHECK`/`NOT NULL` constraints: add only after profiling current values and proving the invariant.
- `data_quality_results`: add after the initial checks and thresholds have run reliably without excessive false positives.
- dbt: adopt only when at least one real SQL transformation and its tests move under dbt ownership; do not add an empty skeleton for résumé value.
- Telegram warning notifications: add after Data Quality warning thresholds are stable. Keep routine success notifications off unless the user requests them.
- Python 3.14 production runtime: adopt only after the browser dependency no longer relies on removed `distutils` behavior and link discovery passes a no-write CI smoke test. Dashboard runtime compatibility does not prove scraper compatibility.

### Do not spend time on now

- Airflow or another orchestration platform.
- Polars for the current tens-of-thousands-row workload; Selenium/network I/O is the dominant cost.
- DuckDB without a concrete local reconciliation workflow or exported Parquet/CSV artifacts.
- Moving Raw/Bronze/Silver/Gold into separate PostgreSQL schemas; table prefixes are adequate and a schema migration would risk Data API and dashboard access.
- Splitting the wide `silver_estate` table into feature/attribute tables without query or storage evidence.
- PostgreSQL ENUM types for mutable source categories; use `CHECK` constraints only for truly stable values.
- Predictive models, AI-generated insights, or additional dashboard metrics before reliability and data quality are complete.
- Listing price history, removal tracking, time-on-market, or price-cut analytics under the current append-only acquisition decision.

---

### Task 1: Establish canonical project documentation

**Files:**

- Create: `README.md`
- Create: `AGENTS.md`
- Rename and rewrite: `docs/architecture.md` -> `ARCHITECTURE.md`
- Create: `docs/operations.md`
- Modify: `docs/README.md`
- Modify: `PROGRESS.md`

**Produces:** A beginner-friendly, current source of truth for repository purpose, ownership, operation, and next steps.

- [x] **Step 1: Write the root README from current behavior**

  Document the actual flow `999.md -> raw_links -> bronze_estate -> silver_estate -> Gold -> api_* -> Imobil-Index`, Python 3.11 runtime, 01:00 UTC schedule, exact local commands, test command, and explicit append-only limitations. Do not claim predictive models, direct Silver dashboard reads, or price-change history.

- [x] **Step 2: Write repository working rules**

  In `AGENTS.md`, require current-code/log inspection, one focused change, secret protection, service-role backend-only use, `steps.<id>.outcome`, numeric listing-link waits, failure diagnostics, production SQL verification, and honest reporting of checks not run.

- [x] **Step 3: Replace the empty architecture document**

  Move the canonical architecture to root `ARCHITECTURE.md`. Define each layer's grain and responsibility, the `pipeline_runs` control plane, the public `api_*` boundary, and the downstream dashboard dependency. Clearly distinguish current architecture from possible future work.

- [x] **Step 4: Add the operations runbook**

  `docs/operations.md` must explain the workflow schedule and jobs, normal success evidence, artifact locations, Telegram failure alerts, how to inspect `pipeline_runs`, how to handle a stale run, and how to verify public API freshness without exposing keys.

- [x] **Step 5: Retire stale duplicate prose safely**

  Replace `docs/README.md` with a short index pointing to the four canonical root documents and `docs/operations.md`. Do not leave two competing project overviews.

- [x] **Step 6: Verify documentation references**

  Run:

  ```powershell
  rg -n "02:00 UTC|silver/transformers.py|Dashboards.*Silver" README.md AGENTS.md ARCHITECTURE.md docs
  rg -n "SUPABASE_KEY|service_role" README.md AGENTS.md ARCHITECTURE.md docs
  git diff --check
  ```

  Expected: the first command finds no stale claims; secret references explain policy but contain no value; `git diff --check` passes.

  Verified 2026-09-08: the stale-claim search returned no matches; secret-name
  matches contain policy or placeholders only; all relative Markdown file links
  resolve; tracked and new documentation contains no trailing whitespace.

- [ ] **Step 7: Commit the documentation baseline**

  ```powershell
  git add README.md AGENTS.md ARCHITECTURE.md PROGRESS.md docs/README.md docs/operations.md
  git commit -m "docs: establish pipeline project source of truth"
  ```

---

### Task 2: Move public API ownership to the pipeline repository

**Files:**

- Create: `docs/public_api_v1.md`
- Create: `sql/api/*.sql` from the currently deployed scripts in `Imobil-Index/sql`
- Modify: `pipeline/gold/schema.sql`
- Modify downstream: `../Imobil-Index/README.md`, `../Imobil-Index/AGENTS.md`, `../Imobil-Index/PROGRESS.md`, `../Imobil-Index/ARCHITECTURE.md`
- Remove downstream only after parity: `../Imobil-Index/docs/public_api_v1.md`, producer-oriented API design documents, and `../Imobil-Index/sql/*.sql`

**Consumes:** The deployed `api_*` table list and refresh-function behavior.

**Produces:** One versioned producer-side database/API contract; the dashboard retains only consumer documentation.

- [x] **Step 1: Capture current production metadata before moving files**

  Record table/view kinds, columns, primary keys, indexes, RLS status, policies, grants, function definitions, fixed `search_path`, and Security/Performance Advisor results for every internal and `api_*` object. Treat old Markdown row counts as historical snapshots, not current truth.

  Verified read-only on 2026-09-08 against Supabase project `estate-md`
  (`tfwfvdbatsdncyoibzxp`, PostgreSQL 17.6). The dated evidence is in
  `docs/production_database_inventory_2026-09-08.md`. No database state was
  changed. The snapshot also records legacy internal write grants, public
  refresh-function execution, and duplicate indexes as separate remediation
  work; none was silently changed during documentation migration.

- [x] **Step 2: Copy, then reconcile, the deployed API SQL**

  Copy the dashboard SQL scripts into `sql/api/` without deleting the originals. Compare each script against current production definitions. Consolidate only after differences are understood; preserve explicit `GRANT SELECT`, RLS read policies, public-write revocation, and private internal objects.

  Verified 2026-09-08: all nine dashboard SQL files were copied byte-for-byte
  into `sql/api/`; source/target SHA-256 hashes match and are recorded in
  `sql/api/README.md`. The originals remain in `Imobil-Index/sql`. Reconciliation
  identified the chronological function-replacement chain, production's
  explicit `DELETE ... WHERE TRUE`, incomplete internal privilege revocation,
  public refresh-function execution, health-check coverage gaps, and duplicate
  indexes. No SQL was applied to production and no historical script was
  rewritten or consolidated in this step.

- [x] **Step 3: Create the canonical API contract**

  Move the current contract to `docs/public_api_v1.md`. For each of the ten tables document grain, columns, freshness field, minimum-listing threshold, read permissions, and the refresh function that maintains it.

  Verified 2026-09-08: `docs/public_api_v1.md` is now the producer-owned v1
  contract. It documents all ten production tables, exact grains and columns,
  snapshot versus refresh semantics, per-table minimum group sizes, public
  read-only access, refresh ownership, breaking-change rules, and the current
  security-remediation caveat. Production category values and the example city
  filter were checked against aggregated `api_*` rows. No database or dashboard
  file was changed.

- [x] **Step 4: Make the base Gold schema reproducible**

  Rewrite `pipeline/gold/schema.sql` so it no longer suggests that the current system contains only the sales materialized view. It may reference ordered scripts under `sql/api/`, but a clean operator must be able to identify every required Gold/API object and execution order.

  Verified 2026-09-08: `pipeline/gold/schema.sql` now bootstraps both daily
  tables, both current materialized views, the security-invoker gross-yield
  view, production filters/thresholds, Gold indexes, RLS, and explicit internal
  grants. It lists all ten required public API objects and the non-alphabetical
  SQL execution order. Existing environments still require metadata comparison;
  `IF NOT EXISTS` is not presented as a migration mechanism. No SQL was applied
  to production. Static object/filter/access checks and `git diff --check`
  passed. DDL execution remains unverified because this checkout has no local
  PostgreSQL/`psql`; production was not used as a test database.

- [x] **Step 5: Cut dashboard documentation to consumer scope**

  Correct the dashboard's `AGENTS.md` and `PROGRESS.md` statements that it reads Gold directly. Keep a short `api_*` consumption summary and link to the upstream canonical contract.

  Verified 2026-09-10 in `Imobil-Index`: `README.md`, `AGENTS.md`,
  `PROGRESS.md`, and `ARCHITECTURE.md` now describe the dashboard as an
  `api_*` consumer and link to this repository's canonical contract. Current
  Gold-read and producer-ownership claims were removed; legacy SQL/API files
  remain explicitly marked for the separate parity/removal step. All 15
  dashboard unit tests pass, documented Ruff scope (`app.py`) passes with
  `--no-cache`, and `git diff --check` passes. Full-repository Ruff still finds
  the pre-existing broad `Exception` catch in `wake_streamlit.py`; it was not
  changed during this documentation-only step.

- [x] **Step 6: Verify the public boundary**

  Run the existing API health script from `Imobil-Index`, then verify with anon credentials that all ten `api_*` tables are readable and internal Raw/Bronze/Silver/Gold objects and public writes remain unavailable. Run database advisors after any SQL change.

  Partial verification on 2026-09-10 against production `estate-md`:

  - the dashboard credential is an `anon` key; its health check read all ten
    non-empty `api_*` tables, with the latest snapshot dated 2026-09-09;
  - all ten API tables have RLS, public SELECT grants and SELECT policies, and
    no INSERT/UPDATE/DELETE/TRUNCATE privileges for `anon` or `authenticated`;
  - direct anon REST reads of Raw, Bronze, Silver, Gold, and `pipeline_runs`
    were all rejected with PostgreSQL code `42501`; service-role SELECT remains
    available;
  - the boundary is not yet least-privilege: `anon` and `authenticated` retain
    broad non-SELECT table privileges on Raw/Bronze/Silver and several Gold
    objects. RLS with no policies blocks Data API row writes today, but the
    redundant grants should still be revoked;
  - `refresh_gold_estate()` and `refresh_gold_rent()` are security-invoker
    functions with a fixed `search_path`, but `anon` and `authenticated` still
    have EXECUTE. Do not expose pipeline refresh RPCs publicly;
  - default privileges for both `postgres` and `supabase_admin` still grant
    broad table, sequence, and function access to public roles, so future
    objects can inherit the same problem;
  - the security advisor reported only six informational
    `rls_enabled_no_policy` findings for intentionally closed internal tables.
    The performance advisor reported eight duplicate-index groups plus unused
    indexes; treat index cleanup as a separate reviewed task.

  No SQL, grants, functions, or production data were changed during this
  initial verification. Step 6 stayed open until a versioned least-privilege
  hardening script was reviewed, applied manually, and the checks were rerun.

  Repository remediation prepared on 2026-09-10, not applied to production:
  `sql/api/harden_public_boundary.sql` revokes the verified redundant ACLs and
  hardens defaults for future postgres-owned objects. The canonical
  `check_public_api_layer.sql` now also checks internal non-SELECT privileges,
  `pipeline_runs`, refresh-function execution/security mode, and producer-owned
  default privileges. Its new checks correctly report the current production
  state before hardening as `CHECK`; Step 6 remained open at that point.

  Applied manually and verified on 2026-09-10:

  - all ten API tables pass the RLS, SELECT-policy, read-grant, and public-write
    denial checks;
  - all nine internal objects have no `anon`/`authenticated` table privileges,
    retain service-role SELECT, and reject direct anon REST reads with `42501`;
  - both refresh functions remain security-invoker with a fixed `search_path`,
    reject public execution, and retain service-role execution;
  - table, sequence, and function defaults for new postgres-owned objects no
    longer grant access to public roles;
  - the anon health check reads all ten non-empty API tables, with current
    snapshots dated 2026-09-10;
  - the security advisor has no warning/error findings. Its six INFO notices
    are the expected no-policy state for closed internal RLS tables;
  - the performance advisor still reports 32 unused-index notices and eight
    duplicate-index groups. That cleanup remains a separate reviewed task.

  Step 6 is complete. No application data or API contract changed during the
  hardening.

- [x] **Step 7: Remove duplicate producer files from the dashboard**

  Delete dashboard SQL/API design duplicates only after the upstream copy, links, and production parity checks pass. The deletion must be a separate reviewable commit so rollback is simple.

  Verified and removed on 2026-09-10 in `Imobil-Index`:

  - all nine dashboard SQL files had upstream copies; eight were byte-for-byte
    identical, while the original checker hash remains recorded upstream and
    its canonical producer copy now contains the additional hardening checks;
  - the dashboard API document was a subset of the canonical upstream contract;
  - housing-type, condition, and floor-position producer rules remain in the
    upstream contract and versioned SQL, while their implemented UI behavior
    remains in dashboard code and its historical progress log;
  - removed four producer/API documents and nine SQL files from the dashboard;
    retained the dashboard-specific design plan under `docs/superpowers/`;
  - updated dashboard `ARCHITECTURE.md` and `PROGRESS.md`; root documentation
    continues to link to the canonical upstream API contract;
  - all 15 dashboard unit tests, compilation of the active Python modules,
    focused Ruff checks, and `git diff --check` pass.

  The pipeline contract and SQL provenance document were also updated to
  describe the verified 2026-09-10 hardening state. No Streamlit behavior,
  public API contract, or production database object changed in Step 7.

- [x] **Step 8: Commit producer and consumer changes separately**

  Suggested commits:

  ```text
  docs(db): make pipeline the public API source of truth
  docs(dashboard): link to upstream API contract
  chore(dashboard): remove duplicated producer SQL documentation
  ```

  Verified on 2026-09-10: the producer-side ownership, hardening, and progress
  changes are committed in this repository at `fbc1ee3`; the dashboard cleanup
  is committed separately in `Imobil-Index` at `9dbeadc`. Both working trees
  were clean after the commits, and the dashboard's consumer-side
  `scripts/check_api_health.py` remains tracked.

---

### Task 3: Add a real pipeline test environment and CI gate

**Files:**

- Create: `requirements-dev.txt`
- Create: `ruff.toml`
- Create: `.github/workflows/test.yml`
- Modify: `tests/test_transformer.py`
- Create: `tests/test_normalizers.py`
- Create: `tests/test_gold_failure.py`
- Create: `tests/test_pipeline_runs.py`
- Modify: `PROGRESS.md`

**Produces:** A deterministic pull-request gate that does not require Supabase secrets or a live browser.

- [x] **Step 1: Declare minimal dev tooling**

  Add only:

  ```text
  pytest
  ruff
  ```

  Keep runtime dependencies in `requirements.txt`; do not add dbt, Polars, or DuckDB.

  Verified 2026-09-10: `requirements-dev.txt` contains only the current exact
  PyPI releases `pytest==9.1.1` and `ruff==0.16.6`. Both support Python 3.11;
  runtime dependencies remain unchanged in `requirements.txt`. A no-install
  resolver check for the new file passed with
  `python -m pip install --dry-run --ignore-installed --python-version 3.11
  --only-binary=:all: -r requirements-dev.txt`. The local machine has Python
  3.14.6 but no `py` launcher or Python 3.11 interpreter, so execution of the
  test suite under 3.11 remains part of the planned CI verification.

- [x] **Step 2: Add normalizer and quality tests**

  Cover valid, null, malformed, and boundary inputs for every function in `pipeline/silver/normalizers.py`; assert the current `quality_score` and `assign_status` boundaries at `0.55` and `0.85`. Use fixed dates rather than the current clock.

  Verified 2026-09-10: `tests/test_normalizers.py` adds 48 deterministic
  cases across all ten normalizers, including missing, malformed, decimal,
  partial-address, and fixed date/datetime inputs. It also verifies the eight
  quality fields, zero-value treatment, and exact status boundaries below and
  at `0.55` and `0.85`. The focused file passes `48 passed`; the full suite
  passes `59 passed`; Ruff passes for the new file. Production normalization
  behavior was not changed.

- [x] **Step 3: Test Silver transformation contracts**

  Fill `tests/test_transformer.py` with representative Bronze dictionaries and assert typed Silver fields, preservation of `region_raw`, empty JSON handling, and normalization status. Mock no transformation logic.

  Verified 2026-09-10: `tests/test_transformer.py` exercises a representative
  Bronze tuple through the real `transform_record()` function and covers typed
  dates, prices, dimensions, address fields, features, `region_raw`, quality
  score, and normalization status. A second case verifies empty/null JSON
  handling and the `failed` result. Only `supabase.create_client` is patched
  during module import so the tests require no credentials or network; no
  transformation function is mocked. The focused file passes `2 passed`, the
  full suite passes `61 passed`, and Ruff passes for the changed test file.

- [x] **Step 4: Test failure propagation and metadata without network**

  Mock only the Supabase client boundary. Assert that one failed Gold RPC raises `RuntimeError`, a successful Gold refresh sets `gold_refreshed=True`, and `finish_run` records the correct terminal fields.

  Verified 2026-09-10 with empty Supabase credentials:
  `tests/test_gold_failure.py` proves that one failed RPC produces a
  `RuntimeError` while the other refresh is still attempted, and that a
  successful Gold loader records `gold_refreshed=True` before finishing the
  run as succeeded. `tests/test_pipeline_runs.py` verifies the failed terminal
  payload, cleared `current_stage`, diagnostic fields, UTC `finished_at`, run
  filter, and execution through a mocked Supabase client boundary. The three
  focused tests pass, the full suite passes `64 passed`, and Ruff passes for
  both new files. Production code was not changed.

- [x] **Step 5: Add the PR workflow**

  Trigger on `push` to `main`, `pull_request`, and `workflow_dispatch`. Use Python 3.11, install runtime plus dev requirements, run Ruff, compile tracked Python modules, and execute `pytest -q`. Do not provide Supabase or Telegram secrets.

  Prepared and verified locally on 2026-09-10: `.github/workflows/test.yml`
  defines the read-only `Test pipeline logic` job for pushes to `main`, pull
  requests, and manual runs. It uses Python 3.11, pip caching, both requirement
  files, repository-wide Ruff, compilation of all tracked Python directories,
  and pytest, with no secrets or live services. `ruff.toml` establishes a
  reproducible Python 3.11 baseline using core `E4`, `E7`, `E9`, and `F` rules;
  the broader Ruff rules currently expose 157 legacy findings and were not
  silently presented as fixed. The workflow YAML parses successfully, local
  Ruff and compilation pass, and the full suite passes `64 passed`. A real
  GitHub Actions run remains Step 6.

- [ ] **Step 6: Verify locally and in GitHub Actions**

  ```powershell
  python -m pip install -r requirements.txt -r requirements-dev.txt
  python -m ruff check .
  python -m pytest -q
  git diff --check
  ```

  Expected: all commands pass; the GitHub `Test pipeline logic` workflow is green on the branch/PR.

- [ ] **Step 7: Commit**

  ```powershell
  git add requirements-dev.txt .github/workflows/test.yml tests PROGRESS.md
  git commit -m "test: add pipeline regression gate"
  ```

---

### Task 4: Make pipeline run metadata truthful

**Files:**

- Modify: `common/pipeline_runs.py`
- Modify: `pipeline/bronze/loader.py`
- Modify: `pipeline/silver/loader.py`
- Modify: `sql/schema/pipeline_runs.sql`
- Modify: `tests/test_pipeline_runs.py`
- Create: `scripts/close_stale_runs.py`
- Modify: `.github/workflows/pipeline.yml`
- Modify: `docs/operations.md`, `PROGRESS.md`

**Produces:** Accurate per-run counters and deterministic recovery of abandoned run rows.

- [ ] **Step 1: Add an additive counter helper**

  Add `increment_run_counters(run_id: str, **deltas: int) -> None`. Permit only the declared non-negative counter columns, reject negative deltas and unknown names, read current values, and update their sums. Bronze jobs are sequential, so no concurrent increment path is introduced.

- [ ] **Step 2: Record Bronze results after every iteration**

  After driver cleanup, increment `bronze_loaded` by `success_count` and `rejected_count` by `failed_count`. If no pending rows exist, leave counters unchanged and return successfully.

- [ ] **Step 3: Record Silver status counts**

  After successful upload, count transformed records by `normalization_status` and update `silver_success`, `silver_partial`, and `silver_failed`. Until incremental Silver is introduced, these values mean rows processed by the full Silver execution, not newly inserted rows. Do not confuse upload errors with normalization failures.

- [ ] **Step 4: Add unit tests for accumulation**

  Simulate two sequential Bronze iterations and assert that counts accumulate rather than overwrite. Assert that Silver status totals equal the number of transformed records.

- [ ] **Step 5: Define abandoned-run recovery**

  Keep the existing status values. `scripts/close_stale_runs.py` should mark `running` rows older than 12 hours as `failed`, retain their last `current_stage` as `failed_stage`, set `finished_at`, and write a clear cancellation/interruption message. It must never modify a recent running row.

- [ ] **Step 6: Run stale cleanup at the start of acquisition**

  Execute the cleanup immediately before creating the new run record. Because workflow concurrency prevents overlapping pipeline runs and the schedule is daily, the 12-hour threshold does not collide with a normal next run.

- [ ] **Step 7: Verify against a fresh workflow run**

  Confirm a new successful row has non-zero Bronze/Silver counts when records were processed, `gold_refreshed=true`, terminal timestamps, and no `current_stage`. Confirm old abandoned rows are closed without editing historical successful rows manually.

- [ ] **Step 8: Commit counters and cleanup separately**

  ```text
  feat(ops): record bronze and silver run counters
  fix(ops): close abandoned pipeline runs
  ```

---

### Task 5: Add Data Quality v1 before Gold

**Files:**

- Create: `pipeline/quality/__init__.py`
- Create: `pipeline/quality/checks.py`
- Create: `scripts/run_quality.py`
- Create: `tests/test_quality_checks.py`
- Modify: `.github/workflows/pipeline.yml`
- Modify: `docs/operations.md`, `ARCHITECTURE.md`, `PROGRESS.md`

**Consumes:** Silver records and the current run identifier.

**Produces:** A small deterministic quality gate between Silver and Gold.

- [ ] **Step 1: Profile before choosing thresholds**

  Measure row count, normalization-status distribution, duplicate URLs, non-positive prices, impossible floor pairs, missing publication dates, and freshness. Record the observed baseline and do not derive thresholds from one anomalous run.

- [ ] **Step 2: Implement pure check evaluation**

  Each check returns a dictionary with `check_name`, `severity`, `status`, `actual_value`, `expected_value`, and `details`. Keep evaluation pure so tests require no database.

- [ ] **Step 3: Start with conservative classifications**

  Blocking: Silver query/upload failure, zero eligible Silver rows, duplicate URL contract violation, and existing Gold RPC failure. Warning initially: non-positive price, `floor > total_floors`, missing publication date, large missingness changes, and unusual new-link/parser counts. Promote a warning to blocking only after real-data review proves the rule and false-positive risk is low.

- [ ] **Step 4: Insert the quality job between Silver and Gold**

  Change dependencies to `silver -> quality -> gold`. The quality script exits non-zero only for failed blocking checks and prints a concise summary for artifacts and Telegram failure context.

- [ ] **Step 5: Add deterministic tests**

  Cover passing data, every blocking failure, warning-only results, null handling, and boundary thresholds. Expected values must be explicit invariants, not copies of the production calculation.

- [ ] **Step 6: Observe warning behavior before persisting results**

  Run the checks for at least several normal pipeline executions. If results are stable and useful, proceed to Task 6; otherwise adjust or remove noisy checks before adding storage and alerts.

- [ ] **Step 7: Commit**

  ```powershell
  git add pipeline/quality scripts/run_quality.py tests/test_quality_checks.py .github/workflows/pipeline.yml ARCHITECTURE.md docs/operations.md PROGRESS.md
  git commit -m "feat: add pre-gold data quality gate"
  ```

---

### Task 6: Persist useful quality results and warnings

**Entry condition:** Task 5 checks have demonstrated stable, actionable output over multiple runs.

**Files:**

- Create: `sql/schema/data_quality_results.sql`
- Modify: `scripts/run_quality.py`
- Modify: `scripts/send_telegram_alert.py`
- Modify: `.github/workflows/pipeline.yml`
- Modify: `docs/operations.md`, `PROGRESS.md`

- [ ] **Step 1: Create the internal results table**

  Use `run_id`, `check_name`, `layer`, `severity`, `status`, numeric/text actual and expected values, `details jsonb`, and `checked_at timestamptz`. Enable RLS, revoke `anon`/`authenticated`, and grant only required server-side access.

- [ ] **Step 2: Persist one row per evaluated check**

  Link results to `pipeline_runs.run_id`; avoid adding duplicate observability columns to every data row.

- [ ] **Step 3: Add one warning notification**

  Send a concise Telegram warning only when at least one warning check fails. Keep normal success runs silent.

- [ ] **Step 4: Verify security and behavior**

  Verify service-role writes, public denial, RLS/advisors, warning-only green workflow behavior, and blocking red workflow behavior.

- [ ] **Step 5: Commit**

  ```text
  feat(dq): persist quality check results
  feat(alerts): notify on actionable quality warnings
  ```

---

### Task 7: Decide on incremental Silver and dbt from evidence

**This is a decision gate, not an automatic implementation task.**

- [ ] **Step 1: Measure Silver cost**

  Record Bronze row count, rows transformed per run, Silver duration, network volume where available, and total workflow duration for at least five normal runs.

- [ ] **Step 2: Decide whether incremental Silver is justified**

  Implement it only if full reprocessing is a meaningful runtime/cost problem or row-level lineage is required. If implemented, define an idempotent watermark or explicit processed-version contract; do not rely on local timestamps or list offsets.

- [ ] **Step 3: Decide whether dbt owns real transformations**

  Adopt dbt only if the next change moves a real staging/Gold/API SQL model plus tests and documentation into dbt. Reject an empty `dbt_estate` skeleton that leaves all production SQL in ad-hoc functions.

- [ ] **Step 4: Keep the simpler architecture when thresholds are not met**

  If the existing Python plus PostgreSQL functions remain fast, understandable, and tested, record the decision in `PROGRESS.md` and stop. A justified non-adoption is stronger engineering evidence than unused tooling.

---

## Execution Order

Execute strictly in this order:

1. Task 1 — documentation baseline.
2. Task 2 — database/API ownership and reproducibility.
3. Task 3 — automated tests and CI.
4. Task 4 — truthful operational metadata.
5. Task 5 — minimal Data Quality gate.
6. Task 6 — persistence and warning alerts, only after stable observations.
7. Task 7 — evidence-based incremental Silver/dbt decision.

Do not begin a later task while the previous task has unresolved verification failures. After each task, update `Verified Baseline`, `Confirmed open problems`, and the task checkboxes with the exact commands and environment used.
