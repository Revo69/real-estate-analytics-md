import os
import time
import logging
import sqlite3
import uuid
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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

# Настройки
BASE_URL = "https://999.md/ru/list/real-estate/apartments-and-rooms?view_type=short&page={}&appl=1&ef=16,9441,32,30,2307&eo=13859,12885,12900,12912&o_16_1=778,776,777,903,912,922"
MAX_PAGES = 1
DB_PATH = os.path.join("storage", "estate.db")


def collect_links(max_pages: int = MAX_PAGES) -> set[str]:
    """Собирает ссылки на объявления со страниц."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)

    links = set()
    try:
        for page in range(1, max_pages + 1):
            parsed = urlparse(BASE_URL)
            q = dict(parse_qsl(parsed.query))
            if page == 1:
                q.pop("page", None)
            else:
                q["page"] = str(page)
            url = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))

            logging.info("Parsing page %d: %s", page, url)
            driver.get(url)
            time.sleep(1.0)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            link_elements = soup.find_all("a", class_="AdShort_title__link__EnVP9")

            if not link_elements:
                logging.warning("No links found on page %d", page)
                break

            for link in link_elements:
                href = link.get("href")
                if not href:
                    continue
                href = href.split("?")[0]
                if href.startswith("/"):
                    full_link = "https://999.md" + href
                elif href.startswith("http"):
                    full_link = href
                else:
                    full_link = "https://999.md/" + href
                links.add(full_link)

            logging.info("Found %d links on page %d", len(link_elements), page)
            time.sleep(2.0)
    finally:
        driver.quit()

    return links


def save_links_to_db(links: set[str], db_path: str = DB_PATH) -> None:
    """Сохраняет ссылки в SQLite, проверяя дубликаты."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_links (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        before = cur.execute("SELECT COUNT(*) FROM raw_links").fetchone()[0]

        cur.executemany(
            "INSERT OR IGNORE INTO raw_links (id, url) VALUES (?, ?)",
            ((str(uuid.uuid4()), u) for u in links)
        )
        conn.commit()

        after = cur.execute("SELECT COUNT(*) FROM raw_links").fetchone()[0]
        logging.info("Saved %d new links (total %d)", after - before, after)


def main():
    links = collect_links(MAX_PAGES)
    logging.info("Collected %d unique links", len(links))
    save_links_to_db(links)


if __name__ == "__main__":
    main()
