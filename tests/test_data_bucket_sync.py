import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.infra.data_bucket_sync import build_upload_plan


class DataBucketSyncTests(unittest.TestCase):
    def test_empty_canonical_sea_matrix_is_rejected_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)
            matrix_path = data_root / "sea_matrix.json"
            matrix_path.write_text(
                json.dumps(
                    {
                        "ports": [],
                        "matrix": {},
                        "voyage_fuel_g_per_tnm_directional": {},
                    }
                ),
                encoding="utf-8",
            )

            with patch(
                "modules.infra.data_bucket_sync._relative_object_path",
                return_value="data/sea_matrix.json",
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "no usable positive port-pair distances",
                ):
                    build_upload_plan(data_root=data_root)


if __name__ == "__main__":
    unittest.main()
