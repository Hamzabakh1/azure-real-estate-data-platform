from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PlatformPaths
from .io_utils import read_csv, read_json, write_csv
from .quality import QualityIssue, normalize_agency, normalize_listing, normalize_transaction

AGENCY_FIELDS = ["agency_id", "agency_name", "city", "email"]
LISTING_FIELDS = [
    "listing_id",
    "property_type",
    "city",
    "district",
    "latitude",
    "longitude",
    "bedrooms",
    "bathrooms",
    "area_sqm",
    "price_mad",
    "price_per_sqm_mad",
    "status",
    "listed_at",
    "agency_id",
    "quality_checked_at",
]
TRANSACTION_FIELDS = [
    "transaction_id",
    "listing_id",
    "transaction_date",
    "sale_price_mad",
    "buyer_type",
    "payment_method",
]
QUARANTINE_FIELDS = ["entity", "source_row", "record_key", "rule", "message", "payload_json"]


def _deduplicate(
    entity: str,
    rows: list[dict[str, Any]],
    key_field: str,
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        key = str(row.get(key_field, ""))
        if key in seen:
            issues.append(
                {
                    **QualityIssue(entity, index, key, "unique_key", f"duplicate {key_field}").to_dict(),
                    "payload_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
                }
            )
        else:
            seen.add(key)
            result.append(row)
    return result


def transform_to_silver(
    paths: PlatformPaths, bronze_paths: dict[str, Path], run_id: str, as_of: str
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Normalize, validate, deduplicate, and quarantine source records."""

    quarantine: list[dict[str, Any]] = []

    raw_agencies = read_json(bronze_paths["agencies"])
    agencies: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_agencies, start=1):
        clean, issues = normalize_agency(raw, index)
        if issues:
            quarantine.extend(
                {**issue.to_dict(), "payload_json": json.dumps(raw, ensure_ascii=False, sort_keys=True)}
                for issue in issues
            )
        else:
            agencies.append(clean)
    agencies = _deduplicate("agencies", agencies, "agency_id", quarantine)
    agency_ids = {row["agency_id"] for row in agencies}

    listings: list[dict[str, Any]] = []
    for index, raw in enumerate(read_csv(bronze_paths["listings"]), start=2):
        clean, issues = normalize_listing(raw, index, agency_ids)
        if issues:
            quarantine.extend(
                {**issue.to_dict(), "payload_json": json.dumps(raw, ensure_ascii=False, sort_keys=True)}
                for issue in issues
            )
        else:
            listings.append(clean)
    listings = _deduplicate("listings", listings, "listing_id", quarantine)
    listing_ids = {row["listing_id"] for row in listings}

    transactions: list[dict[str, Any]] = []
    for index, raw in enumerate(read_csv(bronze_paths["transactions"]), start=2):
        clean, issues = normalize_transaction(raw, index, listing_ids)
        if issues:
            quarantine.extend(
                {**issue.to_dict(), "payload_json": json.dumps(raw, ensure_ascii=False, sort_keys=True)}
                for issue in issues
            )
        else:
            transactions.append(clean)
    transactions = _deduplicate("transactions", transactions, "transaction_id", quarantine)

    silver_root = paths.lake_dir / "silver"
    outputs = {
        "agencies": silver_root / "agencies" / f"snapshot_date={as_of}" / "agencies.csv",
        "listings": silver_root / "listings" / f"snapshot_date={as_of}" / "listings.csv",
        "transactions": silver_root / "transactions" / f"snapshot_date={as_of}" / "transactions.csv",
    }
    write_csv(outputs["agencies"], agencies, AGENCY_FIELDS)
    write_csv(outputs["listings"], listings, LISTING_FIELDS)
    write_csv(outputs["transactions"], transactions, TRANSACTION_FIELDS)

    quarantine_path = paths.quarantine_dir / f"run_id={run_id}" / "rejected_records.csv"
    write_csv(quarantine_path, quarantine, QUARANTINE_FIELDS)

    metrics = {
        "accepted": {
            "agencies": len(agencies),
            "listings": len(listings),
            "transactions": len(transactions),
        },
        "rejected_rule_violations": len(quarantine),
        "quarantine_path": str(quarantine_path.relative_to(paths.runtime_root)),
    }
    return outputs, metrics
