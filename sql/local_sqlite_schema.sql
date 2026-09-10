CREATE TABLE IF NOT EXISTS dim_agency (
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT
);

CREATE TABLE IF NOT EXISTS dim_location (
    location_key INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    district TEXT NOT NULL,
    UNIQUE (city, district)
);

CREATE TABLE IF NOT EXISTS dim_property (
    listing_id TEXT PRIMARY KEY,
    property_type TEXT NOT NULL,
    bedrooms INTEGER NOT NULL,
    bathrooms INTEGER NOT NULL,
    area_sqm REAL NOT NULL,
    latitude REAL,
    longitude REAL,
    agency_id TEXT NOT NULL,
    first_listed_at TEXT NOT NULL,
    FOREIGN KEY (agency_id) REFERENCES dim_agency (agency_id)
);

CREATE TABLE IF NOT EXISTS fact_listing_snapshot (
    listing_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    location_key INTEGER NOT NULL,
    price_mad REAL NOT NULL,
    price_per_sqm_mad REAL NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (listing_id, snapshot_date),
    FOREIGN KEY (listing_id) REFERENCES dim_property (listing_id),
    FOREIGN KEY (location_key) REFERENCES dim_location (location_key)
);

CREATE TABLE IF NOT EXISTS fact_transaction (
    transaction_id TEXT PRIMARY KEY,
    listing_id TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    sale_price_mad REAL NOT NULL,
    buyer_type TEXT,
    payment_method TEXT,
    FOREIGN KEY (listing_id) REFERENCES dim_property (listing_id)
);

CREATE INDEX IF NOT EXISTS ix_snapshot_location_date
    ON fact_listing_snapshot (location_key, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_transaction_listing_date
    ON fact_transaction (listing_id, transaction_date);

CREATE VIEW IF NOT EXISTS mart_city_market AS
SELECT
    s.snapshot_date,
    l.city,
    COUNT(DISTINCT s.listing_id) AS listing_count,
    ROUND(AVG(s.price_mad), 2) AS average_listing_price_mad,
    ROUND(AVG(s.price_per_sqm_mad), 2) AS average_price_per_sqm_mad,
    SUM(CASE WHEN s.status = 'active' THEN 1 ELSE 0 END) AS active_listing_count,
    COUNT(DISTINCT t.transaction_id) AS transaction_count,
    ROUND(AVG(t.sale_price_mad), 2) AS average_sale_price_mad
FROM fact_listing_snapshot AS s
JOIN dim_location AS l ON l.location_key = s.location_key
LEFT JOIN fact_transaction AS t ON t.listing_id = s.listing_id
GROUP BY s.snapshot_date, l.city;

CREATE VIEW IF NOT EXISTS mart_property_type AS
SELECT
    s.snapshot_date,
    p.property_type,
    COUNT(*) AS listing_count,
    ROUND(AVG(p.area_sqm), 2) AS average_area_sqm,
    ROUND(AVG(s.price_mad), 2) AS average_listing_price_mad,
    ROUND(AVG(s.price_per_sqm_mad), 2) AS average_price_per_sqm_mad
FROM fact_listing_snapshot AS s
JOIN dim_property AS p ON p.listing_id = s.listing_id
GROUP BY s.snapshot_date, p.property_type;
