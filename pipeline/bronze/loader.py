import os
import logging
import uuid
import argparse
from dotenv import load_dotenv

from .parsers import parse_features

from supabase import create_client, Client
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
import time
import random
import shutil

from common.pipeline_runs import finish_run, get_run_id, update_run

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in .env file!\n"
        f"Current values: URL={SUPABASE_URL}, KEY={'[hidden]' if SUPABASE_KEY else None}"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LOG_PATH = os.path.join("logs", "bronze_loader.log")
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)


def save_estate(record: dict) -> bool:
    """
    Save a single estate record into the bronze_estate table.
    Returns True if successful, False otherwise.
    """
    try:
        result = (
            supabase.table("bronze_estate")
            .upsert(
                {
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
                },
                on_conflict="url",
            )
            .execute()
        )

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
        check = (
            supabase.table("raw_links")
            .select("id, url, status, attempts")
            .eq("url", url)
            .execute()
        )
        logging.info(f"   Found in DB: {len(check.data) if check.data else 0} records")

        if not check.data or len(check.data) == 0:
            logging.error(f"❌ URL not found in raw_links: {url}")
            return False

        # Perform update
        result = (
            supabase.table("raw_links")
            .update({"status": status, "attempts": current_attempts + 1})
            .eq("url", url)
            .execute()
        )

        logging.info("   Update executed, checking result...")

        if result.data and len(result.data) > 0:
            logging.info(
                f"✅ Updated {len(result.data)} record(s): {url} → status: {status}, attempts: {current_attempts + 1}"
            )
            return True
        else:
            logging.error(f"❌ Update returned no data for URL: {url}")
            logging.error(f"   Response: {result}")

            verify = (
                supabase.table("raw_links")
                .select("status, attempts, updated_at")
                .eq("url", url)
                .execute()
            )
            logging.error(f"   Current record state: {verify.data}")
            return False

    except Exception as e:
        logging.error(f"❌ Exception while updating link {url}: {e}")
        import traceback

        logging.error(traceback.format_exc())
        return False


def cleanup_driver_cache():
    """Clean up undetected_chromedriver cache"""
    cache_paths = [
        os.path.expanduser("~/.local/share/undetected_chromedriver"),
        "/tmp/undetected_chromedriver",
        "/tmp/.com.google.Chrome.*",
    ]

    for cache_path in cache_paths:
        try:
            if "*" in cache_path:
                # Handle glob patterns
                import glob

                for path in glob.glob(cache_path):
                    if os.path.exists(path):
                        shutil.rmtree(path, ignore_errors=True)
            elif os.path.exists(cache_path):
                shutil.rmtree(cache_path, ignore_errors=True)
        except Exception as e:
            logging.debug(f"   Cache cleanup error for {cache_path}: {e}")


def create_driver_with_retry(max_retries=5):
    """
    Create Chrome driver with comprehensive retry logic.
    Handles version mismatches, cache issues, and connection timeouts.
    """

    for attempt in range(max_retries):
        try:
            # Clean cache on retries
            if attempt > 0:
                logging.info(f"🔄 Retry {attempt + 1}/{max_retries}, cleaning cache...")
                cleanup_driver_cache()
                time.sleep(3)

            # CRITICAL: Create NEW options for each attempt
            # Reusing ChromeOptions causes "you cannot reuse the ChromeOptions object" error
            options = uc.ChromeOptions()

            # Essential arguments
            options.add_argument("--headless=new")  # New headless mode (Chrome 109+)
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # Speed optimizations
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")
            options.add_argument("--blink-settings=imagesEnabled=false")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-default-apps")

            # Memory optimization
            options.add_argument("--memory-pressure-off")
            options.add_argument("--disable-background-timer-throttling")

            # CI environment specific
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--remote-debugging-address=0.0.0.0")
            options.add_argument("--disable-setuid-sandbox")

            # Page load strategy - don't wait for all resources
            # options.page_load_strategy = 'eager'

            # User agent to avoid detection
            options.add_argument(
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            logging.info("   Creating driver (attempt {attempt + 1})...")

            from shutil import which
            import subprocess
            chrome_path = which("google-chrome") or "/usr/bin/google-chrome"
            chrome_version = subprocess.check_output([chrome_path, "--version"]).decode().strip()
            major_version = int(chrome_version.split()[2].split(".")[0])
            
            # Create driver with version autodetection
            driver = uc.Chrome(
                options=options,
                version_main=major_version,   # вместо захардкоженных 150
                headless=True,
                use_subprocess=True,
                driver_executable_path=None,
            )

            

            # Configure timeouts - increased for slow connections
            driver.set_page_load_timeout(60)  # Page load timeout
            driver.set_script_timeout(60)  # Script execution timeout
            driver.implicitly_wait(10)  # Element finding timeout

            # Increase connection timeout for DevTools protocol
            # This fixes "HTTPConnectionPool Read timed out" errors
            try:
                if hasattr(driver, "command_executor") and hasattr(
                    driver.command_executor, "_client_config"
                ):
                    driver.command_executor._client_config.timeout = 180
                elif hasattr(driver, "command_executor"):
                    import warnings

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        driver.command_executor.set_timeout(180)
            except (AttributeError, Exception) as e:
                logging.debug(f"   Could not set command_executor timeout: {e}")

            # Test driver is working
            driver.get("about:blank")
            logging.info(f"✅ Driver initialized successfully (attempt {attempt + 1})")

            return driver

        except Exception as e:
            error_msg = str(e)
            logging.error(
                f"❌ Driver init failed (attempt {attempt + 1}/{max_retries}): {error_msg}"
            )

            # Cleanup on error
            cleanup_driver_cache()

            # Exponential backoff
            if attempt < max_retries - 1:
                wait_time = min(5 * (attempt + 1), 30)  # Cap at 30 seconds
                logging.info(f"   ⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logging.error("🚨 All driver initialization retries exhausted")
                raise


def is_driver_alive(driver) -> bool:
    """Check if driver is still responsive"""
    try:
        driver.current_url
        return True
    except Exception:
        return False


def recreate_driver(old_driver):
    """Safely recreate driver after failure"""
    try:
        if old_driver:
            old_driver.quit()
    except Exception:
        pass

    return create_driver_with_retry(max_retries=3)


def main(start: int, end: int):
    """
    Load pending links from raw_links in the given range [start, end],
    parse them, and save into bronze_estate.
    """

    run_id = get_run_id()
    update_run(run_id, current_stage="bronze")

    offset = start - 1 if start > 0 else 0
    limit = end - start + 1

    try:
        logging.info(
            f"📥 Fetching pending links (user range {start}-{end}, API range {offset}-{offset + limit - 1})..."
        )
        resp = (
            supabase.table("raw_links")
            .select("url, attempts")
            .in_("status", ["pending"])
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = resp.data or []

    except Exception as error:
        logging.exception("Failed to fetch pending links")

        finish_run(
            run_id,
            status="failed",
            failed_stage="bronze",
            error_message=str(error),
        )

        raise RuntimeError("Could not fetch pending links from raw_links") from error

    if not rows:
        logging.warning(f"⚠️ No pending links found in range {start}-{end}")
        return

    logging.info(f"✅ Found {len(rows)} pending links in range {start}-{end}")

    # ============================================
    # Initialize Chrome driver
    # ============================================
    logging.info("🚀 Initializing Chrome driver...")

    driver = None
    try:
        driver = create_driver_with_retry(max_retries=5)

    except Exception as error:
        logging.exception("Failed to initialize Chrome driver after all retries")

        finish_run(
            run_id,
            status="failed",
            failed_stage="bronze",
            error_message=str(error),
        )

        raise RuntimeError("Bronze cannot run without a Chrome driver") from error

    success_count = 0
    failed_count = 0
    timeout_count = 0
    webdriver_errors = 0

    try:
        for idx, row in enumerate(rows, 1):
            url = row["url"].strip()
            current_attempts = row.get("attempts", 0) or 0

            logging.info(f"\n{'=' * 60}")
            logging.info(f"🔄 [{idx}/{len(rows)}] Processing: {url}")
            logging.info(f"   Current attempts: {current_attempts}")

            if current_attempts >= 3:
                logging.warning(f"   ⏭️ Skipping URL with {current_attempts} attempts")
                update_link_status(url, "max_attempts_reached", current_attempts)
                continue

            # Check driver health before parsing
            if not is_driver_alive(driver):
                logging.warning("   🔄 Driver not responsive, recreating...")
                driver = recreate_driver(driver)

            # Parse the URL with comprehensive error handling
            try:
                record = parse_features(url, driver=driver)
                logging.info("   ✅ Parsing completed")

            except TimeoutException as e:
                logging.error(f"   ⏱️ Timeout during parsing: {e}")
                record = {"status": "timeout", "url": url}
                timeout_count += 1

                # Recreate driver after timeout
                try:
                    logging.info("   🔄 Recreating driver after timeout...")
                    driver = recreate_driver(driver)
                except Exception as driver_err:
                    logging.error(f"   ❌ Failed to recreate driver: {driver_err}")
                    # Continue with potentially broken driver, will check health next iteration

            except WebDriverException as e:
                logging.error(f"   ❌ WebDriver error: {e}")
                record = {"status": "webdriver_error", "url": url}
                webdriver_errors += 1

                # Try to recreate driver
                try:
                    logging.info("   🔄 Recreating driver after WebDriver error...")
                    driver = recreate_driver(driver)
                except Exception as driver_err:
                    logging.error(f"   ❌ Failed to recreate driver: {driver_err}")
                    # Don't break - try to continue

            except Exception as e:
                logging.error(f"   ❌ Parsing failed: {e}")
                import traceback

                logging.error(traceback.format_exc())
                record = {"status": "failed", "url": url}

            parse_status = record.get("status", "failed")
            logging.info(f"   Parse status: {parse_status}")

            if parse_status == "success":
                logging.info("   💾 Attempting to save to bronze_estate...")
                saved = save_estate(record)
                logging.info(
                    f"   Save result: {'✅ Success' if saved else '❌ Failed'}"
                )

                if saved:
                    logging.info("   🔄 Updating link status to 'processed'...")
                    updated = update_link_status(url, "processed", current_attempts)
                    if updated:
                        success_count += 1
                        logging.info("   ✅ Link status updated successfully")
                    else:
                        logging.error("   ❌ Failed to update link status")
                        failed_count += 1
                else:
                    logging.info(
                        "   ⚠️ Parsing OK but saving failed, marking as 'save_failed'"
                    )
                    update_link_status(url, "save_failed", current_attempts)
                    failed_count += 1
            else:
                status_map = {
                    "timeout": "parse_timeout",
                    "webdriver_error": "parse_error",
                    "failed": "parse_failed",
                }
                final_status = status_map.get(parse_status, "parse_failed")

                logging.info(f"   ⚠️ Parsing failed, marking as '{final_status}'")
                update_link_status(url, final_status, current_attempts)
                failed_count += 1

            logging.info(f"{'=' * 60}\n")

            # Progress indicator every 10 records
            if idx % 10 == 0:
                logging.info(
                    f"📊 Progress: {idx}/{len(rows)} | ✅ {success_count} | ❌ {failed_count} | ⏱️ {timeout_count} | 🔧 {webdriver_errors}"
                )

            # Rate limiting - random delay between requests
            delay = random.uniform(1, 2)  # 1-2 seconds
            logging.info(f"   ⏳ Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

    finally:
        # ============================================
        # Cleanup
        # ============================================
        if driver:
            logging.info("🔚 Closing Chrome driver...")
            try:
                driver.quit()
                logging.info("✅ Driver closed successfully")
            except Exception as e:
                logging.error(f"⚠️ Error closing driver: {e}")

        # Final cache cleanup
        cleanup_driver_cache()

    logging.info("🎉 Processing complete!")
    logging.info(
        f"📊 Summary: ✅ {success_count} successful | ❌ {failed_count} failed | ⏱️ {timeout_count} timeouts | 🔧 {webdriver_errors} webdriver errors | Total: {len(rows)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start", type=int, required=True, help="Start index in raw_links"
    )
    parser.add_argument("--end", type=int, required=True, help="End index in raw_links")
    args = parser.parse_args()

    main(args.start, args.end)
