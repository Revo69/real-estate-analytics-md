# 🏗️ Real Estate Analytics MD

**Daily data pipeline for Moldova's residential real-estate market** — from
listing discovery on 999.md to normalized data, private market aggregates, and
the public API behind Imobil.Index.

[![Pipeline](https://github.com/Revo69/real-estate-analytics-md/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Revo69/real-estate-analytics-md/actions/workflows/pipeline.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com/)
[![Automated](https://img.shields.io/badge/schedule-daily-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)

**[→ Open the live Imobil.Index dashboard](https://imobil-index.streamlit.app)**

---

## What it does

The pipeline turns source listings into reproducible, aggregated market data.
Each layer has one clear responsibility:

| Stage | Main object | Responsibility |
|---|---|---|
| 🔎 **Acquisition** | `raw_links` | Discover numeric listing URLs and track their processing status. |
| 🟤 **Bronze** | `bronze_estate` | Parse new listing pages while preserving source-shaped text and JSON. |
| ⚪ **Silver** | `silver_estate` | Normalize dates, prices, locations, dimensions, and property attributes. |
| 🟡 **Gold** | `gold_*` | Build private current aggregates and daily market snapshots. |
| 🔒 **Public API** | `api_*` | Publish aggregated-only, read-only datasets for the dashboard and REST consumers. |

The separate
[Imobil.Index](https://github.com/Revo69/Imobil-Index) Streamlit application
reads only the safe `api_*` layer. Internal listing-level and operational data
remain private.

---

## Highlights

- **Automated daily pipeline** — GitHub Actions runs the full dependency chain
  at `01:00 UTC` and also supports manual execution.
- **Resilient listing discovery** — waits for numeric 999.md listing URLs,
  retries bounded failures, and preserves page diagnostics and screenshots.
- **Source evidence in Bronze** — keeps original text and structured JSON where
  premature normalization would lose useful information.
- **Typed Silver layer** — produces analysis-ready prices, dates, locations,
  dimensions, amenities, `quality_score`, and `normalization_status`.
- **Private Gold, public aggregates** — dashboard users receive market metrics
  without access to listing-level tables or pipeline operations.
- **Truthful failure handling** — critical stage errors remain non-zero after
  diagnostic artifacts are uploaded.
- **Operational run ledger** — `pipeline_runs` records workflow identity,
  timestamps, stage state, link counts, errors, and Gold refresh status.
- **Reproducible dependencies** — direct runtime libraries are pinned; the
  legacy, unused `webdriver-manager` dependency has been removed.

---

## Tech stack

| Area | Tools |
|---|---|
| Acquisition | Selenium, undetected-chromedriver, Beautiful Soup |
| Transformations | Python modules for Bronze, Silver, and Gold |
| Storage and API | Supabase, PostgreSQL, PostgREST |
| Orchestration | GitHub Actions |
| Runtime | Python 3.11 |
| Tests | pytest parser regression suite |
| Consumer | Imobil.Index with Streamlit and Plotly |

Python 3.11 remains the production runtime because
`undetected-chromedriver 3.5.5` still imports the removed standard-library
`distutils` module and does not run in a clean Python 3.12+ environment. The
upgrade to Python 3.14 will follow only after the browser layer has a tested
compatibility path.

---

## Data flow

```text
999.md listing pages
        |
        v
raw_links              one row per discovered URL
        |
        v
bronze_estate          parsed source-shaped fields and JSON
        |
        v
silver_estate          typed and normalized listing fields
        |
        v
Gold datasets          private aggregates and daily snapshots
        |
        v
api_* tables           public read-only aggregated contract
        |
        v
Imobil.Index           Streamlit dashboard
```

The pipeline is intentionally append-only at acquisition time: it processes
new listing URLs but does not revisit every known listing to track later price
changes or removals. It therefore does not claim listing-level price cuts,
time-on-market, delistings, or exact current inventory.

See [ARCHITECTURE.md](ARCHITECTURE.md) for layer grains, system boundaries, and
failure behavior.

---

## Getting started

Clone the repository and create a Python 3.11 environment:

```powershell
git clone https://github.com/Revo69/real-estate-analytics-md.git
cd real-estate-analytics-md
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On systems without the Windows Python launcher, replace `py -3.11` with the
path to a Python 3.11 executable.

Create a local `.env` file containing server-side credentials:

```dotenv
SUPABASE_URL=your-project-url
SUPABASE_KEY=your-server-side-key
```

`SUPABASE_KEY` must be a server-side key capable of writing internal pipeline
tables. Never commit it, print it, or reuse it in the public Streamlit app.

---

## Running the pipeline

Run the same entry points used by GitHub Actions from the repository root:

```powershell
# Discover listing URLs from pages 1 through 30.
python -m pipeline.acquisition.links_loader --start 1 --end 30

# Process the next 500 pending URLs into Bronze.
python -m pipeline.bronze.loader --start 0 --end 500

# Rebuild/upsert the normalized Silver dataset.
python -m scripts.run_silver

# Refresh sales and rent Gold/API datasets through Supabase RPC functions.
python -m scripts.run_gold
```

The scheduled workflow repeats the 500-row Bronze command six times. Silver
currently reads all Bronze rows and upserts the full normalized dataset; an
incremental implementation is deferred until runtime or row-count evidence
justifies the added complexity.

---

## Automation and operations

The main workflow is
[`pipeline.yml`](.github/workflows/pipeline.yml):

```text
collect-links -> parse-bronze -> silver -> gold
```

It runs daily at `01:00 UTC` on Python 3.11. Concurrent scheduled executions
wait instead of cancelling an active scraper. Link, Bronze, and Gold logs are
uploaded for seven days, and a final job sends a Telegram alert when a required
stage fails.

Operational checks, artifact names, run-state interpretation, and recovery
boundaries are documented in the
[operations runbook](docs/operations.md).

---

## Checks

Run the existing deterministic parser tests:

```powershell
python -m pytest -q
```

The repository does not yet declare pytest as a development dependency or run
the suite in a pull-request workflow. Until that planned task is completed, do
not report a clean checkout as tested unless the required test tooling was
installed and the command above completed successfully.

---

## Current limitations

- Acquisition does not track listing history, removals, or price changes.
- Silver currently reprocesses the complete Bronze dataset.
- Bronze and Silver counters in `pipeline_runs` are not populated yet.
- Interrupted historical workflows can leave stale `running` records.
- The complete deployed Gold/API SQL contract still needs to move from the
  dashboard repository into this producer repository.
- Python 3.12+ is blocked by the current browser dependency until a tested
  compatibility strategy replaces the `distutils` import.

The prioritized implementation sequence and verification evidence live in
[PROGRESS.md](PROGRESS.md).

---

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Progress and implementation plan](PROGRESS.md)
- [Operations runbook](docs/operations.md)
- [Documentation index](docs/README.md)

The detailed `api_*` contract will become `docs/public_api_v1.md` when
producer-side SQL ownership is reconciled and moved from `Imobil-Index`.

---

## Contact

**Serghei Matenco**

📧 [sergey.revo@outlook.com](mailto:sergey.revo@outlook.com)

© 2026 Real Estate Analytics MD
