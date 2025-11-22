-- Очередь ссылок на объявления
CREATE TABLE IF NOT EXISTS raw_links (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',   -- pending / parsed / failed
    attempts INTEGER DEFAULT 0,      -- количество попыток обработки
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Бронзовый слой: извлечённые данные по объявлениям
CREATE TABLE IF NOT EXISTS raw_estate (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    ad_id TEXT,
    status TEXT,                     -- success / error
    publication_date TEXT,
    user_login TEXT,
    deal_type TEXT,
    region TEXT,
    description TEXT,
    price_json TEXT,                 -- {"mdl": ..., "eur": ..., "usd": ...}
    main_features_json TEXT,         -- JSON с основными характеристиками
    additional_features_json TEXT,   -- JSON с дополнительными характеристиками
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
