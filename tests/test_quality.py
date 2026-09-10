import unittest

from real_estate_platform.quality import normalize_listing, normalize_transaction


class QualityTests(unittest.TestCase):
    def test_valid_listing_is_normalized(self) -> None:
        row = {
            "listing_id": "L100",
            "property_type": "Apartment",
            "city": "casablanca",
            "district": "maarif",
            "latitude": "33.5731",
            "longitude": "-7.5898",
            "bedrooms": "2",
            "bathrooms": "1",
            "area_sqm": "80",
            "price_mad": "1200000",
            "status": "ACTIVE",
            "listed_at": "2026-09-01",
            "agency_id": "AG001",
        }

        clean, issues = normalize_listing(row, 2, {"AG001"})

        self.assertEqual(issues, [])
        self.assertEqual(clean["city"], "Casablanca")
        self.assertEqual(clean["property_type"], "apartment")
        self.assertEqual(clean["price_per_sqm_mad"], 15000.0)

    def test_invalid_listing_is_rejected_by_multiple_rules(self) -> None:
        row = {
            "listing_id": "L101",
            "property_type": "castle",
            "city": "unknown",
            "district": "unknown",
            "latitude": "0",
            "longitude": "0",
            "bedrooms": "2",
            "bathrooms": "1",
            "area_sqm": "4",
            "price_mad": "-1",
            "status": "mystery",
            "listed_at": "bad-date",
            "agency_id": "AG999",
        }

        _, issues = normalize_listing(row, 2, {"AG001"})
        rules = {issue.rule for issue in issues}

        self.assertTrue(
            {
                "accepted_property_type",
                "accepted_status",
                "positive_area",
                "positive_price",
                "morocco_coordinates",
                "known_agency",
                "valid_listed_at",
            }.issubset(rules)
        )

    def test_transaction_requires_known_listing_and_positive_price(self) -> None:
        row = {
            "transaction_id": "T100",
            "listing_id": "L999",
            "transaction_date": "2026-09-01",
            "sale_price_mad": "0",
            "buyer_type": "individual",
            "payment_method": "cash",
        }

        _, issues = normalize_transaction(row, 2, {"L001"})

        self.assertEqual(
            {issue.rule for issue in issues}, {"known_listing", "positive_sale_price"}
        )


if __name__ == "__main__":
    unittest.main()
