-- Bronze layer: extracted advertisement data
CREATE TABLE IF NOT EXISTS bronze_estate (
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
    main_features_json TEXT,         -- JSON with main features
    additional_features_json TEXT,   -- JSON with additional features
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
