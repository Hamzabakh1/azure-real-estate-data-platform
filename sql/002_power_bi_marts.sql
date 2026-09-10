CREATE OR ALTER VIEW mart.vw_city_market AS
SELECT
    s.snapshot_date,
    l.city,
    COUNT_BIG(*) AS listing_count,
    CAST(AVG(s.price_mad) AS decimal(18,2)) AS average_listing_price_mad,
    CAST(AVG(s.price_per_sqm_mad) AS decimal(18,2)) AS average_price_per_sqm_mad,
    SUM(CASE WHEN s.status = 'active' THEN 1 ELSE 0 END) AS active_listing_count,
    COUNT(DISTINCT t.transaction_id) AS transaction_count,
    CAST(AVG(t.sale_price_mad) AS decimal(18,2)) AS average_sale_price_mad
FROM core.fact_listing_snapshot AS s
JOIN core.dim_location AS l ON l.location_key = s.location_key
LEFT JOIN core.fact_transaction AS t ON t.listing_id = s.listing_id
GROUP BY s.snapshot_date, l.city;
GO

CREATE OR ALTER VIEW mart.vw_property_type AS
SELECT
    s.snapshot_date,
    p.property_type,
    COUNT_BIG(*) AS listing_count,
    CAST(AVG(p.area_sqm) AS decimal(18,2)) AS average_area_sqm,
    CAST(AVG(s.price_mad) AS decimal(18,2)) AS average_listing_price_mad,
    CAST(AVG(s.price_per_sqm_mad) AS decimal(18,2)) AS average_price_per_sqm_mad
FROM core.fact_listing_snapshot AS s
JOIN core.dim_property AS p ON p.listing_id = s.listing_id
GROUP BY s.snapshot_date, p.property_type;
GO
