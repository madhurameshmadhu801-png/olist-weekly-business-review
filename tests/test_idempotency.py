"""Test pipeline idempotency by running twice and asserting identical row counts across all tables."""
import sqlite3
import unittest
from pathlib import Path

from pipeline.config import BASE_DIR
from pipeline.run_pipeline import run_pipeline


class TestPipelineIdempotency(unittest.TestCase):
    """Verifies that running the pipeline multiple times never duplicates or corrupts records."""

    @classmethod
    def setUpClass(cls):
        cls.test_db = BASE_DIR / "test_idempotency.db"
        if cls.test_db.exists():
            cls.test_db.unlink()

    @classmethod
    def tearDownClass(cls):
        # Cleanup temporary test database
        if cls.test_db.exists():
            try:
                cls.test_db.unlink()
            except PermissionError:
                pass

    def _get_all_table_counts(self, db_path: Path) -> dict[str, int]:
        """Inspects SQLite sqlite_master and retrieves exact row counts for all tables."""
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cur.fetchall()]

        counts = {}
        for tbl in sorted(tables):
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            counts[tbl] = cur.fetchone()[0]

        conn.close()
        return counts

    def test_pipeline_idempotency_double_run(self):
        """Runs the pipeline twice consecutively and asserts exact count matching for all tables."""
        # Run 1: Initial load and transform
        summary_run_1 = run_pipeline(db_path=self.test_db, include_reporting=False)
        self.assertEqual(summary_run_1["status"], "SUCCESS")
        counts_run_1 = self._get_all_table_counts(self.test_db)

        # Ensure expected tables exist
        expected_tables = [
            "raw_customers",
            "raw_geolocation",
            "raw_orders",
            "raw_order_items",
            "raw_order_payments",
            "raw_order_reviews",
            "raw_products",
            "raw_sellers",
            "raw_product_category_name_translation",
            "stg_customers",
            "stg_geolocation",
            "stg_orders",
            "stg_order_items",
            "stg_order_payments",
            "stg_order_reviews",
            "stg_products",
            "stg_sellers",
            "mart_orders",
            "mart_order_items_enriched",
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, counts_run_1, f"Table '{tbl}' was not created in Run 1")
            self.assertGreater(counts_run_1[tbl], 0, f"Table '{tbl}' is unexpectedly empty in Run 1")

        # Run 2: Re-run pipeline against the same database
        summary_run_2 = run_pipeline(db_path=self.test_db, include_reporting=False)
        self.assertEqual(summary_run_2["status"], "SUCCESS")
        counts_run_2 = self._get_all_table_counts(self.test_db)

        # Assert identical row counts across all tables
        self.assertEqual(set(counts_run_1.keys()), set(counts_run_2.keys()))
        for tbl, count_1 in counts_run_1.items():
            count_2 = counts_run_2[tbl]
            self.assertEqual(
                count_1,
                count_2,
                f"Idempotency violation in table '{tbl}': Run 1 had {count_1} rows, Run 2 had {count_2} rows!",
            )

        # Assert primary key uniqueness on mart_orders
        conn = sqlite3.connect(self.test_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(order_id), COUNT(DISTINCT order_id) FROM mart_orders")
        total_rows, distinct_orders = cur.fetchone()
        conn.close()

        self.assertEqual(total_rows, distinct_orders, "Duplicate order_id detected in mart_orders!")


if __name__ == "__main__":
    unittest.main()
