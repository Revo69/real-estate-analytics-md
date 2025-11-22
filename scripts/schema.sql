-- Queue of advertisement links
CREATE TABLE IF NOT EXISTS raw_links (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',   -- pending / parsed / failed
    attempts INTEGER DEFAULT 0,      -- number of processing attempts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Bronze layer: extracted advertisement data
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
    main_features_json TEXT,         -- JSON with main features
    additional_features_json TEXT,   -- JSON with additional features
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
