import os
import logging
import uuid
from urllib.parse import urlparse, urlunparse
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

    # динамический user-agent
    from shutil import which
    import subprocess
    chrome_path = which("google-chrome") or "/usr/bin/google-chrome"
    chrome_version = subprocess.check_output([chrome_path, "--version"]).decode().strip()
    major_version = int(chrome_version.split()[2].split(".")[0])
    options.add_argument(f"user-agent=Mozilla/5.0 (X11; Linux x86_64) "
                         f"AppleWebKit/537.36 (KHTML, like Gecko) "
                         f"Chrome/{major_version}.0.0.0 Safari/537.36")

    driver = uc.Chrome(options=options,
                       version_main=major_version,
                       browser_executable_path=chrome_path,
                       use_subprocess=True)
    return driver



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
                continue

            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.AdShort_title__link__EnVP9"))
                )
            except TimeoutException:
                logging.warning(f"Timeout waiting for links on page {page}")
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            link_elements = soup.select("a.AdShort_title__link__EnVP9")

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
    if not links:
        logging.info("No links to save")
        return

    # считаем количество строк до вставки
    before_resp = supabase.table("raw_links").select("*", count="exact").limit(1).execute()
    before = before_resp.count or 0

    # готовим данные
    rows = [{"id": str(uuid.uuid4()), "url": u, "status": "pending", "attempts": 0} for u in links]

    # вставка с игнорированием дубликатов по url
    supabase.table("raw_links").upsert(rows, on_conflict=["url"]).execute()

    # считаем количество строк после вставки
    after_resp = supabase.table("raw_links").select("*", count="exact").limit(1).execute()
    after = after_resp.count or 0

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
