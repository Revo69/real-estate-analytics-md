import os
import time
import logging
import sqlite3
import uuid
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from bs4 import BeautifulSoup
import argparse

# Logging setup
LOG_PATH = os.path.join("logs", "links_loader.log")
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

BASE_URL = (
    "https://999.md/ru/list/real-estate/apartments-and-rooms"
    "?view_type=short&page={}&appl=1&ef=16,9441,32,30,2307"
    "&eo=13859,12885,12900,12912&o_16_1=778,776,777,903,912,922"
)
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 3))  # fewer threads for CI stability
MAX_RETRIES = 3
DB_PATH = os.path.join("storage", "estate.db")


def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    #options.add_argument("--no-sandbox")
    #options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def get_max_pages() -> int:
    """Determine the actual number of pages by clicking the 'last page' button."""
    driver = init_driver()
    try:
        driver.get(BASE_URL.format(1))

        # Wait for the "last page" button and click it
        last_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME,
                "Pagination_pagination__container__buttons__wrapper__icon__last__page__84ROu"))
        )
        last_button.click()

        # Wait for pagination buttons to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[data-testid='pagination-page']"))
        )

        # Parse DOM and get the maximum page number
        soup = BeautifulSoup(driver.page_source, "html.parser")
        buttons = soup.find_all("button", {"data-testid": "pagination-page"})
        if not buttons:
            logging.warning("Pagination buttons not found, fallback = 200")
            return 200

        max_page = max(int(btn.get("data-test-page-value", 1)) for btn in buttons)
        logging.info(f"Detected maximum number of pages: {max_page}")
        return max_page
    finally:
        driver.quit()


def fetch_links_from_page(page: int) -> list[str]:
    driver = init_driver()
    try:
        url = urlunparse(urlparse(BASE_URL.format(page)))

        for attempt in range(1, MAX_RETRIES + 1):
            logging.info(f"Page {page}, attempt {attempt}: {url}")
            try:
                driver.set_page_load_timeout(60)
                driver.get(url)
            except (TimeoutException, WebDriverException) as e:
                logging.warning(f"Page {page} failed to load (attempt {attempt}): {e}")
                time.sleep(5)
                continue

            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "AdShort_title__link__EnVP9"))
                )
            except TimeoutException:
                logging.warning(f"Timeout waiting for links on page {page}")
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            link_elements = soup.find_all("a", class_="AdShort_title__link__EnVP9")

            if link_elements:
                links = []
                for link in link_elements:
                    href = link.get("href")
                    if href:
                        href = href.split("?")[0]
                        if href.startswith("/"):
                            full_link = "https://999.md" + href
                        elif href.startswith("http"):
                            full_link = href
                        else:
                            full_link = "https://999.md/" + href
                        links.append(full_link)
                logging.info(f"Found {len(links)} links on page {page}")
                return links

        logging.error(f"Failed to get links from page {page} after {MAX_RETRIES} attempts")
        return []
    finally:
        driver.quit()


def save_links_to_db(links: list[str]):
    os.makedirs("storage", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_links (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        before = cur.execute("SELECT COUNT(*) FROM raw_links").fetchone()[0]
        cur.executemany(
            "INSERT OR IGNORE INTO raw_links (id, url) VALUES (?, ?)",
            [(str(uuid.uuid4()), u) for u in links]
        )
        conn.commit()
        after = cur.execute("SELECT COUNT(*) FROM raw_links").fetchone()[0]
        logging.info(f"Saved {after - before} new links (total {after})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")
    args = parser.parse_args()

    all_links = set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_links_from_page, page): page for page in range(args.start, args.end + 1)}
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

    logging.info(f"Collected {len(all_links)} unique links in batch {args.start}-{args.end}")
    if all_links:
        save_links_to_db(sorted(all_links))


if __name__ == "__main__":
    main()
