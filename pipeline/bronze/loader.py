import os
import logging
import sqlite3
import uuid
import json
from .parsers import parse_features

# Logging setup
LOG_PATH = os.path.join("logs", "bronze_loader.log")
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

DB_PATH = os.path.join("storage", "estate.db")


def save_estate(record: dict):
    """Save a single estate record into the bronze_estate table."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bronze_estate (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                ad_id TEXT,
                status TEXT,
                publication_date TEXT,
                user_login TEXT,
                deal_type TEXT,
                region TEXT,
                description TEXT,
                price_json TEXT,
                main_features_json TEXT,
                additional_features_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            cur.execute("""
                INSERT OR REPLACE INTO bronze_estate 
                (id, url, ad_id, status, publication_date, user_login, deal_type, region, description,
                 price_json, main_features_json, additional_features_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                record.get("url"),
                record.get("ad_id"),
                record.get("status"),
                record.get("publication_date"),
                record.get("user_login"),
                record.get("deal_type"),
                record.get("region"),
                record.get("description"),
                json.dumps(record.get("price_json"), ensure_ascii=False),
                json.dumps(record.get("main_features"), ensure_ascii=False),
                json.dumps(record.get("additional_features"), ensure_ascii=False)
            ))
            conn.commit()
            logging.info(f"Saved estate record: {record.get('url')}")
        except Exception as e:
            logging.error(f"Failed to save estate record {record.get('url')}: {e}")


def main():
    """Load pending links from raw_links, parse them, and save into bronze_estate."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT url FROM raw_links WHERE status='pending'")
        urls = [row[0] for row in cur.fetchall()]

    logging.info(f"Found {len(urls)} pending links")

    for url in urls:
        record = parse_features(url)
        save_estate(record)

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE raw_links 
                SET status=?, attempts=attempts+1, updated_at=CURRENT_TIMESTAMP
                WHERE url=?
            """, (record.get("status"), url))
            conn.commit()
        logging.info(f"Marked link {url} as {record.get('status')}")


if __name__ == "__main__":
    main()
