from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any


LISTING_STATUSES = {"active", "pending", "sold", "withdrawn"}
PROPERTY_TYPES = {"apartment", "villa", "office", "house", "land"}


@dataclass(frozen=True)
class QualityIssue:
    entity: str
    source_row: int
    record_key: str
    rule: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _required(
    entity: str, row_number: int, row: dict[str, Any], fields: tuple[str, ...], key: str
) -> list[QualityIssue]:
    return [
        QualityIssue(entity, row_number, key, f"required_{field}", f"{field} is required")
        for field in fields
        if row.get(field) is None or str(row.get(field)).strip() == ""
    ]


def _number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _integer(value: Any, field: str) -> int:
    numeric = _number(value, field)
    if not numeric.is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(numeric)


def _iso_date(value: Any, field: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc


def normalize_agency(row: dict[str, Any], row_number: int) -> tuple[dict[str, Any], list[QualityIssue]]:
    key = str(row.get("agency_id", "")).strip()
    issues = _required("agencies", row_number, row, ("agency_id", "agency_name", "city"), key)
    clean = {
        "agency_id": key,
        "agency_name": str(row.get("agency_name", "")).strip(),
        "city": str(row.get("city", "")).strip().title(),
        "email": str(row.get("email", "")).strip().lower(),
    }
    return clean, issues


def normalize_listing(
    row: dict[str, Any], row_number: int, agency_ids: set[str]
) -> tuple[dict[str, Any], list[QualityIssue]]:
    key = str(row.get("listing_id", "")).strip()
    required = (
        "listing_id",
        "property_type",
        "city",
        "district",
        "area_sqm",
        "price_mad",
        "status",
        "listed_at",
        "agency_id",
    )
    issues = _required("listings", row_number, row, required, key)
    clean: dict[str, Any] = {
        "listing_id": key,
        "property_type": str(row.get("property_type", "")).strip().lower(),
        "city": str(row.get("city", "")).strip().title(),
        "district": str(row.get("district", "")).strip().title(),
        "status": str(row.get("status", "")).strip().lower(),
        "agency_id": str(row.get("agency_id", "")).strip(),
    }

    for field in ("area_sqm", "price_mad", "latitude", "longitude"):
        try:
            clean[field] = round(_number(row.get(field), field), 6)
        except ValueError as exc:
            clean[field] = 0.0
            issues.append(QualityIssue("listings", row_number, key, f"valid_{field}", str(exc)))

    for field in ("bedrooms", "bathrooms"):
        try:
            clean[field] = _integer(row.get(field), field)
        except ValueError as exc:
            clean[field] = 0
            issues.append(QualityIssue("listings", row_number, key, f"valid_{field}", str(exc)))

    try:
        clean["listed_at"] = _iso_date(row.get("listed_at"), "listed_at")
    except ValueError as exc:
        clean["listed_at"] = ""
        issues.append(QualityIssue("listings", row_number, key, "valid_listed_at", str(exc)))

    if clean["property_type"] not in PROPERTY_TYPES:
        issues.append(
            QualityIssue("listings", row_number, key, "accepted_property_type", "unsupported property type")
        )
    if clean["status"] not in LISTING_STATUSES:
        issues.append(QualityIssue("listings", row_number, key, "accepted_status", "unsupported status"))
    if clean["area_sqm"] < 10:
        issues.append(QualityIssue("listings", row_number, key, "positive_area", "area_sqm must be at least 10"))
    if clean["price_mad"] <= 0:
        issues.append(QualityIssue("listings", row_number, key, "positive_price", "price_mad must be positive"))
    if not 20.0 <= clean["latitude"] <= 36.0 or not -18.0 <= clean["longitude"] <= -0.5:
        issues.append(QualityIssue("listings", row_number, key, "morocco_coordinates", "coordinates fall outside Morocco"))
    if clean["agency_id"] not in agency_ids:
        issues.append(QualityIssue("listings", row_number, key, "known_agency", "agency_id is not present in agencies"))

    clean["price_per_sqm_mad"] = (
        round(clean["price_mad"] / clean["area_sqm"], 2) if clean["area_sqm"] > 0 else 0.0
    )
    clean["quality_checked_at"] = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return clean, issues


def normalize_transaction(
    row: dict[str, Any], row_number: int, listing_ids: set[str]
) -> tuple[dict[str, Any], list[QualityIssue]]:
    key = str(row.get("transaction_id", "")).strip()
    required = ("transaction_id", "listing_id", "transaction_date", "sale_price_mad")
    issues = _required("transactions", row_number, row, required, key)
    clean: dict[str, Any] = {
        "transaction_id": key,
        "listing_id": str(row.get("listing_id", "")).strip(),
        "buyer_type": str(row.get("buyer_type", "")).strip().lower(),
        "payment_method": str(row.get("payment_method", "")).strip().lower(),
    }
    try:
        clean["sale_price_mad"] = round(_number(row.get("sale_price_mad"), "sale_price_mad"), 2)
    except ValueError as exc:
        clean["sale_price_mad"] = 0.0
        issues.append(QualityIssue("transactions", row_number, key, "valid_sale_price", str(exc)))
    try:
        clean["transaction_date"] = _iso_date(row.get("transaction_date"), "transaction_date")
    except ValueError as exc:
        clean["transaction_date"] = ""
        issues.append(QualityIssue("transactions", row_number, key, "valid_transaction_date", str(exc)))
    if clean["sale_price_mad"] <= 0:
        issues.append(QualityIssue("transactions", row_number, key, "positive_sale_price", "sale price must be positive"))
    if clean["listing_id"] not in listing_ids:
        issues.append(QualityIssue("transactions", row_number, key, "known_listing", "listing_id is not present in accepted listings"))
    return clean, issues
