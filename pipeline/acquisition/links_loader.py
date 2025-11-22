import os
import time
import logging
import sqlite3
import uuid
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Настройка логирования
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

BASE_URL = "https://999.md/ru/list/real-estate/apartments-and-rooms?view_type=short&page={}&appl=1&ef=16,9441,32,30,2307&eo=13859,12885,12900,12912&o_16_1=778,776,777,903,912,922"
MAX_PAGES = 200
MAX_WORKERS = 5
MAX_RETRIES = 3
DB_PATH = os.path.join("storage", "estate.db")


def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def fetch_links_from_page(page: int) -> list[str]:
    driver = init_driver()
    try:
        parsed = urlparse(BASE_URL.format(page))
        url = urlunparse(parsed)

        for attempt in range(1, MAX_RETRIES + 1):
            logging.info(f"Page {page}, attempt {attempt}: {url}")
            driver.get(url)
            time.sleep(1.0)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "AdShort_title__link__EnVP9"))
                )
            except Exception:
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
    all_links = set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_links_from_page, page): page for page in range(1, MAX_PAGES + 1)}
        for future in as_completed(futures):
            page = futures[future]
            links = future.result()
            if links:
                all_links.update(links)
            else:
                logging.error(f"Page {page} completely failed after {MAX_RETRIES} retries")

    logging.info(f"Collected {len(all_links)} unique links")
    save_links_to_db(sorted(all_links))


if __name__ == "__main__":
    main()
