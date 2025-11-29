import os
import logging
import sqlite3
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from .mappings import MONTHS_MAP
from pipeline.silver.normalizers import (
    normalize_number_of_rooms,
    normalize_living_room,
    normalize_area,
    normalize_ceiling_height,
    normalize_int,
    normalize_balcony,
    normalize_date,
    normalize_price,
    normalize_text,
    normalize_region
)

from pipeline.silver.quality import (
    calculate_quality_score,
    assign_status
)

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DB_PATH = os.path.join("storage", "estate.db")

# Logging setup
LOG_PATH = os.path.join("logs", "silver_loader_supabase.log")
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

def parse_publication_date(raw_date: str):
    """Convert 'Дата обновления:22 ноя. 2025, 01:10' → datetime.date(2025, 11, 22)"""
    if not raw_date:
        return None
    try:
        #raw_date = raw_date.replace("Дата обновления:", "").strip()

        for prefix in ("Дата обновления:", "Дата публикации:"):
            if raw_date.startswith(prefix):
                raw_date = raw_date.replace(prefix, "").strip()
                break

        date_part, time_part = raw_date.split(",")
        day, month_str, year = date_part.strip().split(" ")
        month = MONTHS_MAP.get(month_str.lower())
        if not month:
            raise ValueError(f"Unknown month: {month_str}")
        dt = datetime.strptime(f"{day}.{month}.{year} {time_part.strip()}", "%d.%m.%Y %H:%M")
        return dt.date()
    except Exception as e:
        logging.error(f"Failed to parse publication_date '{raw_date}': {e}")
        return None

def safe_json_loads(raw: str) -> dict:
    """Safely parse JSON string, return {} if invalid."""
    if raw is None or str(raw).strip() == "":
        return {}
    try:
        return json.loads(raw)
    except Exception as e:  
        logging.warning(f"Invalid JSON skipped: {raw!r} | {e}")
        return {}

def transform_record(row):
    """Transform bronze_estate row into silver_estate payload for Supabase."""
    (
        id, url, ad_id, status, publication_date, user_login, deal_type,
        region_raw, description, price_json, main_features_json, additional_features_json
    ) = row

    price = safe_json_loads(price_json)
    main = safe_json_loads(main_features_json)
    add = safe_json_loads(additional_features_json)

    pub_date = parse_publication_date(publication_date)

    # address
    region_data = normalize_region(region_raw)
    
    record = {
        "id": id,
        "url": url,
        "ad_id": ad_id,
        "status": status,
        "publication_date": normalize_date(pub_date),
        "user_login": user_login,
        "deal_type": deal_type,
        "region_raw": region_raw,
        "description": description,

        # geo
        "municipality": region_data["municipality"],
        "city":         region_data["city"],
        "sector":       region_data["sector"],
        "street_raw":   region_data["street_raw"],
        "house":        region_data["house"],
        "region_raw":   region_data["region_raw"],
        
        # Prices
        "price_mdl": normalize_price(price.get("mdl")),
        "price_eur": normalize_price(price.get("eur")),
        "price_usd": normalize_price(price.get("usd")),

        # Main features
        "listing_author": normalize_text(main.get("listing_author")),
        "number_of_rooms": normalize_number_of_rooms(main.get("number_of_rooms")),
        "living_room": normalize_living_room(main.get("living_room")),
        "total_area_m2": normalize_area(main.get("total_area_m2")),
        "housing_type": normalize_text(main.get("housing_type")),
        "floor": normalize_int(main.get("floor")),
        "total_floors": normalize_int(main.get("total_floors")),
        "developer": normalize_text(main.get("developer")),
        "building_type": normalize_text(main.get("building_type")),
        "apartment_condition": normalize_text(main.get("apartment_condition")),
        "layout": normalize_text(main.get("layout")),
        "living_area_m2": normalize_area(main.get("living_area_m2")),
        "kitchen_area_m2": normalize_area(main.get("kitchen_area_m2")),
        "bathroom_count": normalize_int(main.get("bathroom_count")),
        "balcony_loggia": normalize_balcony(main.get("balcony_loggia")),
        "ceiling_height_cm": normalize_ceiling_height(main.get("ceiling_height_cm")),
        "parking_space": normalize_text(main.get("parking_space")),

        # Additional features
        "ready_to_move_in": add.get("ready_to_move_in"),
        "extension": add.get("extension"),
        "terrace": add.get("terrace"),
        "separate_entrance": add.get("separate_entrance"),
        "park_area": add.get("park_area"),
        "furnished": add.get("furnished"),
        "with_appliances": add.get("with_appliances"),
        "autonomous_heating": add.get("autonomous_heating"),
        "air_conditioning": add.get("air_conditioning"),
        "underfloor_heating": add.get("underfloor_heating"),
        "double_glazing": add.get("double_glazing"),
        "panoramic_windows": add.get("panoramic_windows"),
        "parquet_floor": add.get("parquet_floor"),
        "laminate_floor": add.get("laminate_floor"),
        "security_door": add.get("security_door"),
        "telephone_line": add.get("telephone_line"),
        "smart_home": add.get("smart_home"),
        "intercom": add.get("intercom"),
        "internet": add.get("internet"),
        "cable_tv": add.get("cable_tv"),
        "alarm_system": add.get("alarm_system"),
        "video_surveillance": add.get("video_surveillance"),
        "elevator": add.get("elevator"),
        "playground": add.get("playground"),
    }

    # 🔑 Quality score
    score = calculate_quality_score(record)
    record["quality_score"] = score
    record["normalization_status"] = assign_status(score)

    return record



def batch_upload(records, batch_size=100):
    """Upload records to Supabase in batches with logging statistics."""
    success_count = 0
    error_count = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            supabase.table("silver_estate").upsert(batch, on_conflict=["id"]).execute()
            success_count += len(batch)
            logging.info(f"✅ Uploaded batch {i//batch_size+1} ({len(batch)} records)")
        except Exception as e:
            error_count += len(batch)
            logging.error(f"❌ Failed to upload batch {i//batch_size+1}: {e}")
        time.sleep(0.5)  # small delay between batches

    logging.info(f"📊 Upload summary: {success_count} successful, {error_count} failed")

def main():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, url, ad_id, status, publication_date, user_login, deal_type, region, description,
                   price_json, main_features_json, additional_features_json
            FROM bronze_estate
        """)
        rows = cur.fetchall()

    logging.info(f"Found {len(rows)} estates to upload")

    records = [transform_record(row) for row in rows]
    batch_upload(records, batch_size=100)

    logging.info("🎉 Silver layer sync completed")

if __name__ == "__main__":
    main()
