import os
import sqlite3
import logging

BASE_DIR = os.path.dirname(__file__)  # path to scripts/
DB_PATH = os.path.join("storage", "estate.db")

SCHEMA_PATHS = [
    os.path.abspath(os.path.join(BASE_DIR, "..", "pipeline", "acquisition", "schema.sql")),
    os.path.abspath(os.path.join(BASE_DIR, "..", "pipeline", "bronze", "schema.sql")),
]

# Configure logging
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

def init_db() -> bool:
    os.makedirs("storage", exist_ok=True)
    logging.info("Starting database initialization...")

    schema_sql = ""
    for path in SCHEMA_PATHS:
        if not os.path.exists(path):
            logging.error(f"Schema file not found: {path}")
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                schema_sql += f.read() + "\n"
            logging.info(f"Loaded {path} successfully")
        except Exception as e:
            logging.error(f"Failed to read {path}: {e}")
            return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript(schema_sql)
        logging.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return False

    logging.info("✅ init_db completed successfully")
    return True


if __name__ == "__main__":
    success = init_db()
    if not success:
        exit(1)
