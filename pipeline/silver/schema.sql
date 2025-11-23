CREATE TABLE IF NOT EXISTS silver_estate (
    id UUID PRIMARY KEY,                  -- UUID из Bronze
    url TEXT NOT NULL UNIQUE,
    ad_id TEXT,
    status TEXT,                          -- success / error
    publication_date DATE,
    user_login TEXT,
    deal_type TEXT,
    region TEXT,
    description TEXT,

    -- Prices
    price_mdl NUMERIC,
    price_eur NUMERIC,
    price_usd NUMERIC,

    -- Main features
    listing_author TEXT,
    number_of_rooms INTEGER,
    living_room BOOLEAN,
    total_area_m2 NUMERIC,
    housing_type TEXT,
    floor INTEGER,
    total_floors INTEGER,
    developer TEXT,
    building_type TEXT,
    apartment_condition TEXT,
    layout TEXT,
    living_area_m2 NUMERIC,
    kitchen_area_m2 NUMERIC,
    bathroom_count INTEGER,
    balcony_loggia TEXT,
    ceiling_height_cm NUMERIC,
    parking_space BOOLEAN,

    -- Additional features
    ready_to_move_in BOOLEAN,
    extension BOOLEAN,
    terrace BOOLEAN,
    separate_entrance BOOLEAN,
    park_area BOOLEAN,
    furnished BOOLEAN,
    with_appliances BOOLEAN,
    autonomous_heating BOOLEAN,
    air_conditioning BOOLEAN,
    underfloor_heating BOOLEAN,
    double_glazing BOOLEAN,
    panoramic_windows BOOLEAN,
    parquet_floor BOOLEAN,
    laminate_floor BOOLEAN,
    security_door BOOLEAN,
    telephone_line BOOLEAN,
    smart_home BOOLEAN,
    intercom BOOLEAN,
    internet BOOLEAN,
    cable_tv BOOLEAN,
    alarm_system BOOLEAN,
    video_surveillance BOOLEAN,
    elevator BOOLEAN,
    playground BOOLEAN,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
