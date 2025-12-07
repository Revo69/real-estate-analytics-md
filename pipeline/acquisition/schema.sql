-- Queue of advertisement links (Acquisition layer)
CREATE TABLE IF NOT EXISTS raw_links (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',   -- pending / parsed / failed
    attempts INTEGER DEFAULT 0,      -- number of processing attempts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
