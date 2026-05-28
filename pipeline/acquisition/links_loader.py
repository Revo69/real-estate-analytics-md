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
                driver.set_page_load_timeout(60)
                driver.get(url)
                time.sleep(random.uniform(2.0, 3.0))
            except (TimeoutException, WebDriverException) as e:
                logging.warning(f"Page {page} failed to load (attempt {attempt}): {e}")
                continue

            # Wait for at least one card link to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/ru/']"))
                )
            except TimeoutException:
                logging.warning(f"Timeout waiting for links on page {page}")
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


def save_links_to_db(links: list[str]):
    if not links:
        logging.info("No links to save")
        return

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
        return

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")
    args = parser.parse_args()

    all_links = set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_links_from_page, page): page
            for page in range(args.start, args.end + 1)
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                links = future.result()
                if links:
                    all_links.update(links)
                else:
                    logging.error(f"Page {page} completely failed")
            except Exception as e:
                logging.exception(f"Unexpected error on page {page}: {e}")

    logging.info(
        f"Collected {len(all_links)} unique links in batch {args.start}-{args.end}"
    )
    if all_links:
        save_links_to_db(sorted(all_links))


if __name__ == "__main__":
    main()
