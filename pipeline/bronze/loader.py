from datetime import datetime, timezone
import os
import logging
import uuid
import argparse
from dotenv import load_dotenv
from .parsers import parse_features
from supabase import create_client, Client
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
import time
import random

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in .env file!\n"
        f"Current values: URL={SUPABASE_URL}, KEY={'[hidden]' if SUPABASE_KEY else None}"
    )

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

def save_estate(record: dict) -> bool:
    """
    Save a single estate record into the bronze_estate table.
    Returns True if successful, False otherwise.
    """
    try:
        result = supabase.table("bronze_estate").upsert({
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
        }, on_conflict="url").execute()
        
        if result.data:
            logging.info(f"✅ Saved estate record: {record.get('url')}")
            return True
        else:
            logging.warning(f"⚠️ No data returned when saving: {record.get('url')}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Failed to save estate record {record.get('url')}: {e}")
        return False

def update_link_status(url: str, status: str, current_attempts: int) -> bool:
    """
    Update the status and attempts count for a link in raw_links.
    Returns True if successful, False otherwise.
    """
    try:
        logging.info(f"🔄 Attempting to update: {url}")
        
        # First, check that the record exists
        check = supabase.table("raw_links").select("id, url, status, attempts").eq("url", url).execute()
        logging.info(f"   Found in DB: {len(check.data) if check.data else 0} records")
        
        if not check.data or len(check.data) == 0:
            logging.error(f"❌ URL not found in raw_links: {url}")
            return False
        
        # Perform update
        result = supabase.table("raw_links").update({
            "status": status,
            "attempts": current_attempts + 1
        }).eq("url", url).execute()
        
        logging.info(f"   Update executed, checking result...")
        
        # Check result
        if result.data and len(result.data) > 0:
            logging.info(f"✅ Updated {len(result.data)} record(s): {url} → status: {status}, attempts: {current_attempts + 1}")
            return True
        else:
            logging.error(f"❌ Update returned no data for URL: {url}")
            logging.error(f"   Response: {result}")
            
            # Verify again after update
            verify = supabase.table("raw_links").select("status, attempts, updated_at").eq("url", url).execute()
            logging.error(f"   Current record state: {verify.data}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Exception while updating link {url}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

def create_driver_with_retry(max_retries=3):
    """Create Chrome driver with retry logic"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')

    # Disable images for faster loading
    options.add_argument('--disable-images')
    options.add_argument('--blink-settings=imagesEnabled=false')    
    
    # Add timeouts
    options.page_load_strategy = 'eager'  # Don't wait for all resources
    
    for attempt in range(max_retries):
        try:
            driver = uc.Chrome(options=options)
            
            # Set timeouts for Selenium
            driver.set_page_load_timeout(60)  # 60 seconds max for page load
            driver.implicitly_wait(10)  # 10 seconds for element finding
            
            logging.info(f"✅ Driver initialized successfully (attempt {attempt + 1})")
            return driver
        except Exception as e:
            logging.error(f"❌ Driver initialization failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise

def main(start: int, end: int):
    """Load pending links from raw_links in the given range [start, end], parse them, and save into bronze_estate."""
    offset = start - 1 if start > 0 else 0
    limit = end - start + 1
    
    try:
        logging.info(f"📥 Fetching pending links (user range {start}-{end}, API range {offset}-{offset + limit - 1})...")
        resp = supabase.table("raw_links") \
            .select("url, attempts") \
            .eq("status", ["pending", "parsed_failed"]) \
            .range(offset, offset + limit - 1) \
            .execute()
        rows = resp.data or []
    except Exception as e:
        logging.error(f"❌ Failed to fetch pending links: {e}")
        rows = []
    
    if not rows:
        logging.warning(f"⚠️ No pending links found in range {start}-{end}")
        return
    
    logging.info(f"✅ Found {len(rows)} pending links in range {start}-{end}")
    
    # ============================================
    # 🚀 Create driver with retry logic
    # ============================================
    logging.info("🚀 Initializing Chrome driver...")
    
    driver = None
    try:
        driver = create_driver_with_retry()
    except Exception as e:
        logging.error(f"❌ Failed to initialize driver after all retries: {e}")
        logging.error("Cannot proceed without driver. Exiting.")
        return
    
    success_count = 0
    failed_count = 0
    timeout_count = 0
    
    try:
        for idx, row in enumerate(rows, 1):
            url = row["url"].strip()
            current_attempts = row.get("attempts", 0) or 0
            
            logging.info(f"\n{'='*60}")
            logging.info(f"🔄 [{idx}/{len(rows)}] Processing: {url}")
            logging.info(f"   Current attempts: {current_attempts}")
            
            # Skip URLs that have failed too many times
            if current_attempts >= 3:
                logging.warning(f"   ⏭️ Skipping URL with {current_attempts} attempts")
                continue
            
            # Parse the URL with timeout handling
            try:
                record = parse_features(url, driver=driver)
                logging.info(f"   ✅ Parsing completed")
                
            except TimeoutException as e:
                logging.error(f"   ⏱️ Timeout during parsing: {e}")
                record = {"status": "timeout", "url": url}
                timeout_count += 1
                
                # Recreate driver after timeout
                try:
                    logging.info("   🔄 Recreating driver after timeout...")
                    driver.quit()
                    driver = create_driver_with_retry()
                except Exception as driver_err:
                    logging.error(f"   ❌ Failed to recreate driver: {driver_err}")
                    break
                    
            except WebDriverException as e:
                logging.error(f"   ❌ WebDriver error: {e}")
                record = {"status": "webdriver_error", "url": url}
                
            except Exception as e:
                logging.error(f"   ❌ Parsing failed: {e}")
                import traceback
                logging.error(traceback.format_exc())
                record = {"status": "failed", "url": url}
            
            # Determine the actual status based on parsing result
            parse_status = record.get("status", "failed")
            logging.info(f"   Parse status: {parse_status}")
            
            # Only save if parsing was successful
            if parse_status == "success":
                logging.info(f"   💾 Attempting to save to bronze_estate...")
                saved = save_estate(record)
                logging.info(f"   Save result: {'✅ Success' if saved else '❌ Failed'}")
                
                if saved:
                    logging.info(f"   🔄 Updating link status to 'processed'...")
                    updated = update_link_status(url, "processed", current_attempts)
                    if updated:
                        success_count += 1
                        logging.info(f"   ✅ Link status updated successfully")
                    else:
                        logging.error(f"   ❌ Failed to update link status")
                        failed_count += 1
                else:
                    logging.info(f"   ⚠️ Parsing OK but saving failed, marking as 'save_failed'")
                    update_link_status(url, "save_failed", current_attempts)
                    failed_count += 1
            else:
                # Parsing failed
                status_map = {
                    "timeout": "parse_timeout",
                    "webdriver_error": "parse_error",
                    "failed": "parse_failed"
                }
                final_status = status_map.get(parse_status, "parse_failed")
                
                logging.info(f"   ⚠️ Parsing failed, marking as '{final_status}'")
                update_link_status(url, final_status, current_attempts)
                failed_count += 1
            
            logging.info(f"{'='*60}\n")
            
            # Progress indicator every 10 records
            if idx % 10 == 0:
                logging.info(f"📊 Progress: {idx}/{len(rows)} | ✅ {success_count} | ❌ {failed_count} | ⏱️ {timeout_count}")
            
            # CRITICAL: Add delay between requests to avoid rate limiting
            delay = random.uniform(2, 5)  # 2-5 seconds
            logging.info(f"   ⏳ Waiting {delay:.1f}s before next request...")
            time.sleep(delay)
            
    finally:
        # ============================================
        # 🔚 Close driver at the end
        # ============================================
        if driver:
            logging.info("🔚 Closing Chrome driver...")
            try:
                driver.quit()
                logging.info("✅ Driver closed successfully")
            except Exception as e:
                logging.error(f"⚠️ Error closing driver: {e}")
    
    logging.info(f"🎉 Processing complete!")
    logging.info(f"📊 Summary: ✅ {success_count} successful | ❌ {failed_count} failed | ⏱️ {timeout_count} timeouts | Total: {len(rows)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="Start index in raw_links")
    parser.add_argument("--end", type=int, required=True, help="End index in raw_links")
    args = parser.parse_args()
    
    main(args.start, args.end)
