from datetime import datetime, timezone
import os
import logging
import uuid
import json
import argparse
from .parsers import parse_features
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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

def save_estate(record: dict):
    """Save a single estate record into the bronze_estate table."""
    try:
        supabase.table("bronze_estate").upsert({
            "id": str(uuid.uuid4()),
            "url": record.get("url"),
            "ad_id": record.get("ad_id"),
            "status": record.get("status"),
            "publication_date": record.get("publication_date"),
            "user_login": record.get("user_login"),
            "deal_type": record.get("deal_type"),
            "region": record.get("region"),
            "description": record.get("description"),
            "price_json": record.get("price_json"),
            "main_features_json": record.get("main_features"),
            "additional_features_json": record.get("additional_features"),
        }, on_conflict=["url"]).execute()
        logging.info(f"Saved estate record: {record.get('url')}")
    except Exception as e:
        logging.error(f"Failed to save estate record: {e}")


def main(start: int, end: int):
    """Load pending links from raw_links in the given range [start, end], parse them, and save into bronze_estate."""
    limit = end - start + 1
    offset = start - 1

    try:
        resp = supabase.table("raw_links") \
            .select("url, attempts") \
            .eq("status", "pending") \
            .range(offset, offset + limit - 1) \
            .execute()
        rows = resp.data or []
    except Exception as e:
        logging.error(f"Failed to fetch pending links: {e}")
        rows = []

    logging.info(f"Found {len(rows)} pending links in range {start}-{end}")

    for row in rows:
        url = row["url"]
        current_attempts = row.get("attempts", 0) or 0
        
        record = parse_features(url)
        save_estate(record)

        try:
            supabase.table("raw_links") \
                .update({
                    "status": record.get("status"),
                    "attempts": current_attempts + 1,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }) \
                .eq("url", url) \
                .execute()

            logging.info(f"Marked link {url} as {record.get('status')}")
        except Exception as e:
            logging.error(f"Failed to update link {url}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="Start index in raw_links")
    parser.add_argument("--end", type=int, required=True, help="End index in raw_links")
    args = parser.parse_args()
    main(args.start, args.end)
