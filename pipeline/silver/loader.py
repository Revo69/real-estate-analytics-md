import os
import logging
import sqlite3
import json
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from config import DB_PATH

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def transform_record(row):
    """Transform raw_estate row into silver_estate payload for Supabase."""
    (
        id, url, ad_id, status, publication_date, user_login, deal_type,
        region, description, price_json, main_features_json, additional_features_json
    ) = row

    price = json.loads(price_json) if price_json else {}
    main = json.loads(main_features_json) if main_features_json else {}
    add = json.loads(additional_features_json) if additional_features_json else {}

    return {
        "id": id,
        "url": url,
        "ad_id": ad_id,
        "status": status,
        "publication_date": publication_date,
        "user_login": user_login,
        "deal_type": deal_type,
        "region": region,
        "description": description,

        # Prices
        "price_mdl": price.get("mdl"),
        "price_eur": price.get("eur"),
        "price_usd": price.get("usd"),

        # Main features
        "listing_author": main.get("listing_author"),
        "number_of_rooms": main.get("number_of_rooms"),
        "living_room": main.get("living_room"),
        "total_area_m2": main.get("total_area_m2"),
        "housing_type": main.get("housing_type"),
        "floor": main.get("floor"),
        "total_floors": main.get("total_floors"),
        "developer": main.get("developer"),
        "building_type": main.get("building_type"),
        "apartment_condition": main.get("apartment_condition"),
        "layout": main.get("layout"),
        "living_area_m2": main.get("living_area_m2"),
        "kitchen_area_m2": main.get("kitchen_area_m2"),
        "bathroom_count": main.get("bathroom_count"),
        "balcony_loggia": main.get("balcony_loggia"),
        "ceiling_height_cm": main.get("ceiling_height_cm"),
        "parking_space": main.get("parking_space"),

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

def upload_estate(record: dict):
    """Upload one estate record to Supabase silver_estate table."""
    try:
        supabase.table("silver_estate").upsert(record, on_conflict=["id"]).execute()
        logging.info(f"✅ Uploaded estate {record['url']}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to upload estate {record['url']}: {e}")
        return False

def main():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, url, ad_id, status, publication_date, user_login, deal_type, region, description,
                   price_json, main_features_json, additional_features_json
            FROM raw_estate
        """)
        rows = cur.fetchall()

    logging.info(f"Found {len(rows)} estates to upload")

    for row in rows:
        record = transform_record(row)
        success = upload_estate(record)
        if success:
            logging.info(f"✅ Estate {record['url']} uploaded to Supabase")
        else:
            logging.warning(f"⚠️ Estate {record['url']} skipped due to error")
        time.sleep(0.2)  # small delay to avoid hitting rate limits

    logging.info("🎉 Silver layer sync completed")

if __name__ == "__main__":
    main()
