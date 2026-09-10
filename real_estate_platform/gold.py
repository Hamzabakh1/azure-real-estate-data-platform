from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .config import PlatformPaths
from .io_utils import read_csv


def _execute_schema(connection: sqlite3.Connection, schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def publish_gold(
    paths: PlatformPaths, silver_paths: dict[str, Path], snapshot_date: str
) -> dict[str, Any]:
    """Load conformed dimensions and facts into the local Azure SQL analogue."""

    paths.gold_dir.mkdir(parents=True, exist_ok=True)
    agencies = read_csv(silver_paths["agencies"])
    listings = read_csv(silver_paths["listings"])
    transactions = read_csv(silver_paths["transactions"])

    with closing(sqlite3.connect(paths.gold_database)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _execute_schema(connection, paths.local_schema)

        connection.executemany(
            """
            INSERT INTO dim_agency (agency_id, agency_name, city, email)
            VALUES (:agency_id, :agency_name, :city, :email)
            ON CONFLICT(agency_id) DO UPDATE SET
              agency_name = excluded.agency_name,
              city = excluded.city,
              email = excluded.email
            """,
            agencies,
        )
        connection.executemany(
            "INSERT OR IGNORE INTO dim_location (city, district) VALUES (:city, :district)", listings
        )
        connection.executemany(
            """
            INSERT INTO dim_property (
              listing_id, property_type, bedrooms, bathrooms, area_sqm,
              latitude, longitude, agency_id, first_listed_at
            ) VALUES (
              :listing_id, :property_type, :bedrooms, :bathrooms, :area_sqm,
              :latitude, :longitude, :agency_id, :listed_at
            )
            ON CONFLICT(listing_id) DO UPDATE SET
              property_type = excluded.property_type,
              bedrooms = excluded.bedrooms,
              bathrooms = excluded.bathrooms,
              area_sqm = excluded.area_sqm,
              latitude = excluded.latitude,
              longitude = excluded.longitude,
              agency_id = excluded.agency_id
            """,
            listings,
        )

        for listing in listings:
            location_key = connection.execute(
                "SELECT location_key FROM dim_location WHERE city = ? AND district = ?",
                (listing["city"], listing["district"]),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO fact_listing_snapshot (
                  listing_id, snapshot_date, location_key, price_mad,
                  price_per_sqm_mad, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(listing_id, snapshot_date) DO UPDATE SET
                  location_key = excluded.location_key,
                  price_mad = excluded.price_mad,
                  price_per_sqm_mad = excluded.price_per_sqm_mad,
                  status = excluded.status
                """,
                (
                    listing["listing_id"],
                    snapshot_date,
                    location_key,
                    float(listing["price_mad"]),
                    float(listing["price_per_sqm_mad"]),
                    listing["status"],
                ),
            )

        connection.executemany(
            """
            INSERT INTO fact_transaction (
              transaction_id, listing_id, transaction_date, sale_price_mad,
              buyer_type, payment_method
            ) VALUES (
              :transaction_id, :listing_id, :transaction_date, :sale_price_mad,
              :buyer_type, :payment_method
            )
            ON CONFLICT(transaction_id) DO UPDATE SET
              sale_price_mad = excluded.sale_price_mad,
              buyer_type = excluded.buyer_type,
              payment_method = excluded.payment_method
            """,
            transactions,
        )
        connection.commit()

        table_counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "dim_agency",
                "dim_location",
                "dim_property",
                "fact_listing_snapshot",
                "fact_transaction",
            )
        }
        mart_rows = connection.execute("SELECT COUNT(*) FROM mart_city_market").fetchone()[0]

    return {
        "database": str(paths.gold_database.relative_to(paths.runtime_root)),
        "table_counts": table_counts,
        "mart_city_market_rows": mart_rows,
    }
