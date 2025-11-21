import os
import sqlite3
import logging

DB_PATH = os.path.join("storage", "estate.db")
SCHEMA_PATH = os.path.join("schema.sql")

# Настройка логирования
LOG_PATH = os.path.join("logs", "init_db.log")
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

def init_db():
    os.makedirs("storage", exist_ok=True)
    logging.info("Starting database initialization...")

    # Читаем schema.sql
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        logging.info("Loaded schema.sql successfully")
    except Exception as e:
        logging.error(f"Failed to read schema.sql: {e}")
        return

    # Прогоняем SQL в SQLite
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.executescript(schema_sql)
            conn.commit()
        logging.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return

    logging.info("✅ init_db completed successfully")

if __name__ == "__main__":
    init_db()
