CREATE SCHEMA core;
GO
CREATE SCHEMA mart;
GO

CREATE TABLE core.dim_agency (
    agency_id varchar(20) NOT NULL PRIMARY KEY,
    agency_name nvarchar(200) NOT NULL,
    city nvarchar(100) NOT NULL,
    email nvarchar(254) NULL,
    updated_at datetime2 NOT NULL DEFAULT sysutcdatetime()
);
GO

CREATE TABLE core.dim_location (
    location_key int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    city nvarchar(100) NOT NULL,
    district nvarchar(150) NOT NULL,
    CONSTRAINT uq_location UNIQUE (city, district)
);
GO

CREATE TABLE core.dim_property (
    listing_id varchar(40) NOT NULL PRIMARY KEY,
    property_type varchar(30) NOT NULL,
    bedrooms smallint NOT NULL,
    bathrooms smallint NOT NULL,
    area_sqm decimal(12,2) NOT NULL,
    latitude decimal(9,6) NULL,
    longitude decimal(9,6) NULL,
    agency_id varchar(20) NOT NULL,
    first_listed_at date NOT NULL,
    updated_at datetime2 NOT NULL DEFAULT sysutcdatetime(),
    CONSTRAINT fk_property_agency FOREIGN KEY (agency_id) REFERENCES core.dim_agency (agency_id),
    CONSTRAINT ck_property_area CHECK (area_sqm >= 10)
);
GO

CREATE TABLE core.fact_listing_snapshot (
    listing_id varchar(40) NOT NULL,
    snapshot_date date NOT NULL,
    location_key int NOT NULL,
    price_mad decimal(18,2) NOT NULL,
    price_per_sqm_mad decimal(18,2) NOT NULL,
    status varchar(20) NOT NULL,
    loaded_at datetime2 NOT NULL DEFAULT sysutcdatetime(),
    CONSTRAINT pk_listing_snapshot PRIMARY KEY (listing_id, snapshot_date),
    CONSTRAINT fk_snapshot_property FOREIGN KEY (listing_id) REFERENCES core.dim_property (listing_id),
    CONSTRAINT fk_snapshot_location FOREIGN KEY (location_key) REFERENCES core.dim_location (location_key),
    CONSTRAINT ck_snapshot_price CHECK (price_mad > 0)
);
GO

CREATE TABLE core.fact_transaction (
    transaction_id varchar(40) NOT NULL PRIMARY KEY,
    listing_id varchar(40) NOT NULL,
    transaction_date date NOT NULL,
    sale_price_mad decimal(18,2) NOT NULL,
    buyer_type varchar(30) NULL,
    payment_method varchar(30) NULL,
    loaded_at datetime2 NOT NULL DEFAULT sysutcdatetime(),
    CONSTRAINT fk_transaction_property FOREIGN KEY (listing_id) REFERENCES core.dim_property (listing_id),
    CONSTRAINT ck_transaction_price CHECK (sale_price_mad > 0)
);
GO

CREATE INDEX ix_snapshot_location_date
ON core.fact_listing_snapshot (location_key, snapshot_date)
INCLUDE (price_mad, price_per_sqm_mad, status);
GO

CREATE INDEX ix_transaction_listing_date
ON core.fact_transaction (listing_id, transaction_date)
INCLUDE (sale_price_mad);
GO
