import unittest

from modules.infra.db import bulk_results


class BulkResultsTests(unittest.TestCase):
    def test_latest_success_filter_is_applied_before_destination_ranking(self) -> None:
        sql = bulk_results._latest_results_for_selector_cte(
            "bulk_run_items",
            "bulk_runs",
            "locations",
            "routes",
            include_destination_set=False,
            item_columns=set(),
            item_status_filter=True,
        )

        self.assertIn("ON r.run_id = i.run_id\n               AND i.status = 'ok'", sql)

    def test_latest_status_query_does_not_pre_filter_status(self) -> None:
        sql = bulk_results._latest_results_for_selector_cte(
            "bulk_run_items",
            "bulk_runs",
            "locations",
            "routes",
            include_destination_set=False,
            item_columns=set(),
            item_status_filter=None,
        )

        self.assertNotIn("AND i.status = 'ok'", sql)
        self.assertNotIn("AND i.status <> 'ok'", sql)


if __name__ == "__main__":
    unittest.main()
