# 🏡 Real Estate Analytics MD

A modular data pipeline for collecting, transforming, and analyzing real estate listings in Moldova.

---

## Architecture Overview

```mermaid
%% Real Estate Analytics — Architecture Overview
graph TD
    subgraph "Acquisition"
        A[Links Collector<br/>Scraper] --> B[Raw Links Queue]
    end

    subgraph "Bronze Layer"
        B --> C[Bronze Loader]
        C --> D[bronze_estate<br/>Raw structured data<br/>SQLite estate.db]
    end

    subgraph "Silver Layer"
        D --> E[Silver Transformer + Loader<br/>silver/transformers.py<br/>silver/loader.py]
        E --> F[silver_estate<br/>Clean & normalized data<br/>Supabase PostgreSQL]
    end

    subgraph "Gold Layer — Planned"
        F --> G[Aggregations & Business Metrics<br/>Price trends<br/>Stats by region<br/>Anomaly detection]
    end

    subgraph "Analytics & Consumption"
        F --> H[Dashboards<br/>Metabase • Streamlit • Looker Studio]
        G --> H
        F --> I[Ad-hoc Analysis<br/>Jupyter • Pandas • SQL clients]
        G --> I
    end

    %% Styles
    classDef bronze    fill:#8B4513, color:#fff, stroke:#333
    classDef silver    fill:#C0C0C0, color:#000, stroke:#333
    classDef gold      fill:#FFD700, color:#000, stroke:#333
    classDef analytics fill:#E3F2FD, color:#1976D2, stroke:#1976D2

    class D bronze
    class F silver
    class G gold
    class H,I analytics
```

---

## 🟤 Bronze Layer: Parsed Listings Table

Instead of storing raw HTML pages, the Bronze layer in this project captures **already parsed listings** in the relational table `bronze_estate`. Each record includes:

- 🔑 **id** — unique UUID  
- 🌐 **url** — link to the original listing  
- 🆔 **ad_id** — listing identifier on the platform  
- 📊 **status** — processing result (`success` / `error`)  
- 📅 **publication_date** — publication or update date  
- 👤 **user_login** — listing author  
- 📑 **deal_type** — type of deal (sale, rent, etc.)  
- 🗺️ **region** — region/address  
- 📝 **description** — textual description  
- 💰 **price_json** — JSON with prices in multiple currencies (`mdl`, `eur`, `usd`)  
- 🏠 **main_features_json** — JSON with main property features (rooms, floor, condition, etc.)  
- ➕ **additional_features_json** — JSON with extra options (heating, elevator, security, etc.)  
- ⏱️ **created_at** — timestamp when the record was inserted  

This design ensures:

- ✅ Semantic information is preserved without loss  
- ✅ Flexible downstream normalization and analytics  
- ✅ Easy debugging and reproducibility  

### Example record in `bronze_estate`

```json
{
  "id": "ad5898ad-38ac-4fec-964a-a4e59c717fd5",
  "url": "https://999.md/ru/100040456",
  "ad_id": "100040456",
  "status": "success",
  "publication_date": "Updated: Nov 24, 2025, 14:40",
  "user_login": "Mirax",
  "deal_type": "Sale",
  "region": "Chișinău mun., Durlești, Center, str. Alexandr Orlov",
  "description": "One-bedroom apartment with living room in Colina Verde Residence, Durlești...",
  "price_json": {"mdl": null, "eur": 77000, "usd": null},
  "main_features_json": {
    "listing_author": "Agency",
    "number_of_rooms": "1-room apartment",
    "housing_type": "New building",
    "floor": "3",
    "total_floors": "8",
    "apartment_condition": "Shell condition"
  },
  "additional_features_json": {
    "autonomous_heating": true,
    "double_glazing": true,
    "security_door": true,
    "intercom": true,
    "video_surveillance": true,
    "elevator": true,
    "playground": true
  },
  "created_at": "2025-11-24 12:54:41"
}
```

---

## ⚙️ Technologies

- **Python 3.11** — core language for ETL scripts and orchestration  
- **SQLite** — lightweight local database for Bronze layer storage  
- **Supabase** — managed Postgres backend for Silver layer persistence and analytics  
- **GitHub Actions** — CI/CD automation for scheduled and reproducible pipeline runs  
- **Modular ETL architecture** — clear separation of Bronze (parsed listings), Silver (normalized data), and Gold (analytics-ready datasets)  
- **Undetected‑chromedriver + Selenium** — resilient acquisition layer for scraping dynamic content  
- **Mermaid diagrams & structured documentation** — visualizing pipeline architecture and onboarding collaborators  
- **Jupyter Notebooks** — exploratory analysis, validation of A/B tests, and prototyping downstream models  

---

## 🚀 Usage

```bash
# Run full pipeline locally from project root
python -m scripts.run_links_loader --start 1 --end 100
python -m scripts.run_bronze
python -m scripts.run_silver
# Gold layer (analytics-ready datasets) is planned but not yet implemented
```

Or let **GitHub Actions** orchestrate it automatically via  
`.github/workflows/pipeline.yml` — scheduled daily at 02:00 UTC.

---

## 📊 Notebooks

- `price_analysis.ipynb` — explore price trends by region and currency  
- `region_distribution.ipynb` — visualize listing density across districts  
- `feature_quality_check.ipynb` — validate completeness and consistency of parsed features  
- `ab_test_validation.ipynb` — statistical validation of experimental changes (e.g. publisher module A/B tests)  

---

## 📁 Data Storage

- `storage/estate.db` — local **SQLite** database containing Bronze and Silver layers  
- `raw_links` — deduplicated queue of listing URLs for acquisition  
- `bronze_estate` — parsed listings table with structured fields and embedded JSON (prices, features)  
- `silver_estate` — normalized records stored in **Supabase/Postgres** for downstream analytics  
- `logs/` — pipeline execution logs, uploaded as artifacts in CI/CD  

---

✅ This version makes it clear that the Gold layer is **planned but not implemented yet**, while keeping the architecture and usage instructions consistent with your current pipeline.

