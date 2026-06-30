import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = [
    ROOT / "docs" / "port_ops_model.md",
    ROOT / "docs" / "hoteling_model.md",
    ROOT / "docs" / "tf_support" / "methodology" / "tf_system_boundary.md",
    ROOT / "docs" / "tf_support" / "methodology" / "tf_assumptions_and_approximations.md",
]


class PortOpsProvenanceDocsTests(unittest.TestCase):
    def test_methodology_docs_explain_fallback_source_levels(self) -> None:
        for path in DOC_PATHS:
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertIn("observ", text)
                self.assertIn("weighted", text)
                self.assertIn("documented", text)
                self.assertIn("unavailable", text)
                self.assertIn("zero", text)

    def test_system_boundary_no_longer_says_port_ops_only_if_explicitly_modeled(self) -> None:
        text = (
            ROOT / "docs" / "tf_support" / "methodology" / "tf_system_boundary.md"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("port operations (origin): vessel hoteling", text)
        self.assertNotIn("if explicitly modeled", text)
        self.assertIn("missing values are not interpreted as zero", text)


if __name__ == "__main__":
    unittest.main()
