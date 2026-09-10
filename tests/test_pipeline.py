import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from real_estate_platform.pipeline import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline_builds_medallion_and_gold_marts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            result = run_pipeline(REPO_ROOT, runtime, "2026-09-10")

            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(
                result["stages"]["silver"]["accepted"],
                {"agencies": 4, "listings": 12, "transactions": 8},
            )
            self.assertGreaterEqual(
                result["stages"]["silver"]["rejected_rule_violations"], 9
            )

            latest = json.loads(
                (runtime / "data" / "operations" / "latest_run.json").read_text()
            )
            self.assertEqual(latest["run_id"], result["run_id"])
            self.assertTrue(latest["stages"]["bronze"]["sources"][0]["sha256"])

            database = runtime / "data" / "gold" / "real_estate_analytics.db"
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM dim_property").fetchone()[0], 12
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM fact_transaction").fetchone()[0], 8
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM mart_city_market").fetchone()[0], 5
                )

    def test_same_snapshot_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            run_pipeline(REPO_ROOT, runtime, "2026-09-10")
            run_pipeline(REPO_ROOT, runtime, "2026-09-10")

            database = runtime / "data" / "gold" / "real_estate_analytics.db"
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM fact_listing_snapshot").fetchone()[0],
                    12,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM fact_transaction").fetchone()[0], 8
                )


if __name__ == "__main__":
    unittest.main()
