import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = [
    ROOT / "docs" / "port_ops_model.md",
    ROOT / "docs" / "hoteling_model.md",
    ROOT / "docs" / "tf_support" / "methodology" / "tf_system_boundary.md",
    ROOT / "docs" / "tf_support" / "methodology" / "tf_assumptions_and_approximations.md",
]
DOC_TEXT_PATHS = [
    path
    for root in (ROOT / "docs",)
    for path in root.rglob("*")
    if path.suffix.lower() in {".md", ".tex"}
]

MISLEADING_PATTERNS = tuple(
    " ".join(parts)
    for parts in (
        ("port ops", "is always"),
        ("port operations are", "always fully included"),
        ("complete", "port ops"),
        ("hoteling is", "always", "included"),
        ("missing port-operation data are", "treated as", "zero"),
        ("missing port operation data are", "treated as", "zero"),
        ("missing port ops data are", "treated as", "zero"),
        ("treated as", "zero"),
        ("assumed", "zero"),
        ("cabotage is", "always", "lower"),
        ("cabotage is", "always", "greener"),
        ("cabotage is", "always better"),
        ("cabotage", "is always"),
        ("always", "lower-emission"),
        ("always", "greener"),
    )
)
NEGATING_CONTEXT = (
    "do not",
    "avoid",
    "not ",
    "not-",
    "no ",
    "never",
    "does not",
    "should not",
    "must not",
    "conditional",
    "caution",
    "lower-confidence",
    "prove",
    "não",
    "nao",
    "evitar",
    "não deve",
    "não são",
    "não significa",
)


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

    def test_docs_do_not_make_unconditional_port_ops_or_cabotage_claims(self) -> None:
        failures: list[str] = []
        for path in DOC_TEXT_PATHS:
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                lower = line.lower()
                for pattern in MISLEADING_PATTERNS:
                    if pattern not in lower:
                        continue
                    if any(token in lower for token in NEGATING_CONTEXT):
                        continue
                    failures.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
