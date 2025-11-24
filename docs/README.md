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

## 🟤 Bronze Layer: Structured JSON

Unlike traditional bronze layers that store raw HTML or unprocessed data, this project stores **pre-parsed structured JSON** extracted from HTML listings. This ensures:

- ✅ No loss of semantic information  
- ✅ Easier debugging and reproducibility  
- ✅ Ready for downstream normalization  

Example record in `raw_estate`:

```json
{
  "price": "89 000 €",
  "location": "Chișinău, Botanica",
  "rooms": "2",
  "area": "54 m²",
  "floor": "3/5",
  "features": ["balcony", "elevator"]
}
```

---

## ⚙️ Technologies

- Python 3.11  
- SQLite  
- Supabase (Silver layer storage)  
- GitHub Actions (CI/CD orchestration)  
- Modular ETL structure (Bronze/Silver/Gold)  
- Jupyter notebooks for analysis  

---

## 🚀 Usage

```bash
# Run full pipeline locally
python scripts/run_links_loader.py
python scripts/run_bronze.py
python scripts/run_silver.py
# Gold layer is not yet implemented
```

Or let GitHub Actions run it daily via `.github/workflows/pipeline.yml`.

---

## 📊 Notebooks

- `price_analysis.ipynb`: price trends by region  
- `region_distribution.ipynb`: listing density  
- `feature_quality_check.ipynb`: data completeness  

---

## 📁 Data Storage

- `storage/estate.db`: SQLite database containing Bronze and Silver layers  
- `raw_links`: deduplicated queue of listing URLs  
- `bronze_estate`: structured JSON records  

---

✅ This version makes it clear that the Gold layer is **planned but not implemented yet**, while keeping the architecture and usage instructions consistent with your current pipeline.













# 🏡 Real Estate Analytics MD
