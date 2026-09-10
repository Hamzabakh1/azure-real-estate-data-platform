CREATE SCHEMA stg;
GO
CREATE SCHEMA etl;
GO

CREATE TABLE stg.agency (
    pipeline_run_id varchar(80) NOT NULL,
    agency_id varchar(20) NOT NULL,
    agency_name nvarchar(200) NOT NULL,
    city nvarchar(100) NOT NULL,
    email nvarchar(254) NULL
);
GO
CREATE TABLE stg.listing (
    pipeline_run_id varchar(80) NOT NULL,
    listing_id varchar(40) NOT NULL,
    property_type varchar(30) NOT NULL,
    city nvarchar(100) NOT NULL,
    district nvarchar(150) NOT NULL,
    latitude decimal(9,6) NULL,
    longitude decimal(9,6) NULL,
    bedrooms smallint NOT NULL,
    bathrooms smallint NOT NULL,
    area_sqm decimal(12,2) NOT NULL,
    price_mad decimal(18,2) NOT NULL,
    price_per_sqm_mad decimal(18,2) NOT NULL,
    status varchar(20) NOT NULL,
    listed_at date NOT NULL,
    agency_id varchar(20) NOT NULL
);
GO
CREATE TABLE stg.[transaction] (
    pipeline_run_id varchar(80) NOT NULL,
    transaction_id varchar(40) NOT NULL,
    listing_id varchar(40) NOT NULL,
    transaction_date date NOT NULL,
    sale_price_mad decimal(18,2) NOT NULL,
    buyer_type varchar(30) NULL,
    payment_method varchar(30) NULL
);
GO

CREATE OR ALTER PROCEDURE etl.usp_publish_real_estate_marts
    @pipeline_run_id varchar(80),
    @snapshot_date date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;

    MERGE core.dim_agency AS target
    USING (SELECT agency_id, agency_name, city, email FROM stg.agency WHERE pipeline_run_id = @pipeline_run_id) AS source
      ON target.agency_id = source.agency_id
    WHEN MATCHED THEN UPDATE SET agency_name = source.agency_name, city = source.city, email = source.email, updated_at = sysutcdatetime()
    WHEN NOT MATCHED THEN INSERT (agency_id, agency_name, city, email) VALUES (source.agency_id, source.agency_name, source.city, source.email);

    MERGE core.dim_location AS target
    USING (SELECT DISTINCT city, district FROM stg.listing WHERE pipeline_run_id = @pipeline_run_id) AS source
      ON target.city = source.city AND target.district = source.district
    WHEN NOT MATCHED THEN INSERT (city, district) VALUES (source.city, source.district);

    MERGE core.dim_property AS target
    USING (SELECT * FROM stg.listing WHERE pipeline_run_id = @pipeline_run_id) AS source
      ON target.listing_id = source.listing_id
    WHEN MATCHED THEN UPDATE SET
      property_type = source.property_type, bedrooms = source.bedrooms, bathrooms = source.bathrooms,
      area_sqm = source.area_sqm, latitude = source.latitude, longitude = source.longitude,
      agency_id = source.agency_id, updated_at = sysutcdatetime()
    WHEN NOT MATCHED THEN INSERT (listing_id, property_type, bedrooms, bathrooms, area_sqm, latitude, longitude, agency_id, first_listed_at)
      VALUES (source.listing_id, source.property_type, source.bedrooms, source.bathrooms, source.area_sqm, source.latitude, source.longitude, source.agency_id, source.listed_at);

    MERGE core.fact_listing_snapshot AS target
    USING (
      SELECT s.listing_id, @snapshot_date AS snapshot_date, l.location_key, s.price_mad, s.price_per_sqm_mad, s.status
      FROM stg.listing AS s
      JOIN core.dim_location AS l ON l.city = s.city AND l.district = s.district
      WHERE s.pipeline_run_id = @pipeline_run_id
    ) AS source
      ON target.listing_id = source.listing_id AND target.snapshot_date = source.snapshot_date
    WHEN MATCHED THEN UPDATE SET location_key = source.location_key, price_mad = source.price_mad, price_per_sqm_mad = source.price_per_sqm_mad, status = source.status, loaded_at = sysutcdatetime()
    WHEN NOT MATCHED THEN INSERT (listing_id, snapshot_date, location_key, price_mad, price_per_sqm_mad, status)
      VALUES (source.listing_id, source.snapshot_date, source.location_key, source.price_mad, source.price_per_sqm_mad, source.status);

    MERGE core.fact_transaction AS target
    USING (SELECT * FROM stg.[transaction] WHERE pipeline_run_id = @pipeline_run_id) AS source
      ON target.transaction_id = source.transaction_id
    WHEN MATCHED THEN UPDATE SET sale_price_mad = source.sale_price_mad, buyer_type = source.buyer_type, payment_method = source.payment_method, loaded_at = sysutcdatetime()
    WHEN NOT MATCHED THEN INSERT (transaction_id, listing_id, transaction_date, sale_price_mad, buyer_type, payment_method)
      VALUES (source.transaction_id, source.listing_id, source.transaction_date, source.sale_price_mad, source.buyer_type, source.payment_method);

    COMMIT TRANSACTION;
END;
GO
