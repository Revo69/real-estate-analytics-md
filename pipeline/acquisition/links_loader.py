import re
import os
import logging
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from bs4 import BeautifulSoup
import argparse

from dotenv import load_dotenv
from supabase import create_client, Client

import time
import random

from common.pipeline_runs import finish_run, get_run_id, start_run, update_run

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Logging setup
LOG_PATH = os.path.join("logs", "links_loader.log")
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)

# ──────────────────────────────────────────────
# New design — no designVersion cookie needed
# URL filter: keep only real estate listings (/ru/<digits>)
# ──────────────────────────────────────────────
AD_HREF_RE = re.compile(r"^/ru/\d+")

BASE_URL = (
    "https://999.md/ru/list/real-estate/apartments-and-rooms?page={}&o_16_1=776,903,912"
)

MAX_WORKERS = int(os.getenv("MAX_WORKERS", 1))
MAX_RETRIES = 3
MAX_CONSECUTIVE_FAILED_PAGES = int(os.getenv("MAX_CONSECUTIVE_FAILED_PAGES", 3))
MAX_FAILED_PAGES_RATIO = float(os.getenv("MAX_FAILED_PAGES_RATIO", 0.2))


def init_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ru-RU")

    from shutil import which
    import subprocess

    chrome_path = which("google-chrome") or "/usr/bin/google-chrome"
    chrome_version = (
        subprocess.check_output([chrome_path, "--version"]).decode().strip()
    )
    major_version = int(chrome_version.split()[2].split(".")[0])
    options.add_argument(
        f"user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{major_version}.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(
        options=options,
        version_main=major_version,
        browser_executable_path=chrome_path,
        use_subprocess=True,
    )
    return driver


def fetch_links_from_page(page: int) -> list[str]:
    """
    Fetch listing URLs from one search-results page.

    New design: each card is an <a href="/ru/<id>?clickToken=..."> wrapping
    the card div. We collect all such hrefs, strip query params, and deduplicate.
    """
    driver = init_driver()
    try:
        url = BASE_URL.format(page)

        for attempt in range(1, MAX_RETRIES + 1):
            logging.info(f"Page {page}, attempt {attempt}: {url}")
            try:
                driver.set_page_load_timeout(20)
                driver.get(url)

            except TimeoutException:
                logging.warning(
                    f"Page {page} did not finish loading; checking the partial DOM"
                )
                try:
                    driver.execute_script("window.stop();")
                except WebDriverException:
                    pass

            except WebDriverException as error:
                logging.warning(
                    f"Page {page} failed to load (attempt {attempt}): {error}"
                )
                continue

            time.sleep(random.uniform(2.0, 3.0))

            # Wait for at least one card link to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/ru/']"))
                )
            except TimeoutException:
                logging.warning(
                    f"Timeout waiting for links on page {page}; "
                    f"title={driver.title!r}; current_url={driver.current_url}"
                )
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")

            links = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Keep only /ru/<numeric-id> paths, drop everything else
                # (navigation links, profile links, etc.)
                clean = href.split("?")[0]
                if AD_HREF_RE.match(clean) and clean not in seen:
                    seen.add(clean)
                    links.append("https://999.md" + clean)

            if links:
                logging.info(f"Found {len(links)} links on page {page}")
                return links

        logging.error(
            f"Failed to get links from page {page} after {MAX_RETRIES} attempts"
        )
        return []
    finally:
        driver.quit()


def save_links_to_db(links: list[str]) -> int:
    if not links:
        logging.info("No links to save")
        return 0

    before_resp = (
        supabase.table("raw_links").select("*", count="exact").limit(1).execute()
    )
    before = before_resp.count or 0

    existing_urls = set()
    CHECK_BATCH_SIZE = 500

    for i in range(0, len(links), CHECK_BATCH_SIZE):
        batch = links[i : i + CHECK_BATCH_SIZE]
        try:
            existing_check = (
                supabase.table("raw_links").select("url").in_("url", batch).execute()
            )
            existing_urls.update(row["url"] for row in existing_check.data)
        except Exception as e:
            logging.error(
                f"Error checking existing URLs (batch {i}-{i + len(batch)}): {e}"
            )
            raise

    new_links = [u for u in links if u not in existing_urls]

    if not new_links:
        logging.info(
            f"No new links to save (all {len(links)} are duplicates, total {before})"
        )
        return 0

    INSERT_BATCH_SIZE = 1000
    inserted_count = 0

    for i in range(0, len(new_links), INSERT_BATCH_SIZE):
        batch = new_links[i : i + INSERT_BATCH_SIZE]
        rows = [
            {"id": str(uuid.uuid4()), "url": u, "status": "pending", "attempts": 0}
            for u in batch
        ]
        try:
            supabase.table("raw_links").insert(rows).execute()
            inserted_count += len(batch)
            logging.info(
                f"Inserted batch {i // INSERT_BATCH_SIZE + 1}: {len(batch)} links"
            )
        except Exception as e:
            logging.error(f"Error inserting batch {i}-{i + len(batch)}: {e}")
            raise

    after = before + inserted_count
    logging.info(
        f"Saved {inserted_count} new links "
        f"(skipped {len(links) - inserted_count} duplicates, total {after})"
    )

    return inserted_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")
    args = parser.parse_args()

    run_id = get_run_id()
    start_run(run_id)

    try:
        all_links = set()
        failed_pages = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(fetch_links_from_page, page): page
                for page in range(args.start, args.end + 1)
            }

            for future in as_completed(futures):
                page = futures[future]

                page_failed = False

                try:
                    links = future.result()

                    if links:
                        all_links.update(links)
                    else:
                        page_failed = True
                        failed_pages.append(page)
                        logging.error(f"Page {page} completely failed")

                except Exception as error:
                    page_failed = True
                    failed_pages.append(page)
                    logging.exception(f"Unexpected error on page {page}: {error}")

                if page_failed:
                    recent_pages = list(
                        range(
                            page - MAX_CONSECUTIVE_FAILED_PAGES + 1,
                            page + 1,
                        )
                    )

                    if all(p in failed_pages for p in recent_pages):
                        failed_pages_text = ", ".join(
                            str(p) for p in sorted(failed_pages)
                        )
                        raise RuntimeError(
                            "Too many consecutive listing pages failed during links collection: "
                            f"{failed_pages_text}"
                        )

        logging.info(
            f"Collected {len(all_links)} unique links in batch {args.start}-{args.end}"
        )

        total_pages = args.end - args.start + 1
        max_failed_pages = int(total_pages * MAX_FAILED_PAGES_RATIO)

        if failed_pages:
            failed_pages_text = ", ".join(str(p) for p in sorted(failed_pages))
            logging.warning(
                f"Failed to collect links from {len(failed_pages)} page(s): "
                f"{failed_pages_text}"
            )

        if len(failed_pages) > max_failed_pages:
            raise RuntimeError(
                f"Too many listing pages failed: {len(failed_pages)} of {total_pages}"
            )

        new_links = save_links_to_db(sorted(all_links)) if all_links else 0

        update_run(
            run_id,
            links_discovered=len(all_links),
            new_links=new_links,
            current_stage="bronze",
        )

    except Exception as error:
        logging.exception("Links collection failed")

        finish_run(
            run_id,
            status="failed",
            failed_stage="collect_links",
            error_message=str(error),
        )

        raise


if __name__ == "__main__":
    main()
