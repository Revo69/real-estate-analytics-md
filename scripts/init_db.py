import os
import sqlite3

DB_PATH = os.path.join("storage", "estate.db")
SCHEMA_PATH = os.path.join("schema.sql")

def init_db():
    # Создаём папку storage, если её нет
    os.makedirs("storage", exist_ok=True)

    # Читаем schema.sql
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Прогоняем SQL в SQLite
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.executescript(schema_sql)
        conn.commit()

    print(f"✅ Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
