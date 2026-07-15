import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.cabotage.antaq_observed_voyages import (
    _build_port_alias_map,
    _read_atracacao_map,
)


class AntaqObservedVoyagesTests(unittest.TestCase):
    def test_atracacao_reader_accepts_real_and_legacy_imo_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_root = Path(temp_dir)
            (raw_root / "2025Atracacao.txt").write_text(
                "IDAtracacao;Nº do IMO\ncall-real;9876543\n",
                encoding="utf-8-sig",
            )
            (raw_root / "2026Atracacao.txt").write_text(
                "IDAtracacao;N do IMO\ncall-legacy;1234567\n",
                encoding="utf-8-sig",
            )

            result = _read_atracacao_map(["2025", "2026"], raw_root)

        self.assertEqual(result["map"]["call-real"]["imo"], "9876543")
        self.assertEqual(result["map"]["call-legacy"]["imo"], "1234567")

    def test_manaus_container_terminals_map_to_canonical_port(self) -> None:
        ports_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "processed"
            / "cabotage_data"
            / "ports_br.json"
        )

        with patch(
            "modules.cabotage.antaq_observed_voyages.resolve_data_asset_path",
            return_value=ports_path,
        ):
            aliases = _build_port_alias_map(ports_path)

        self.assertEqual(aliases["PORTO CHIBATÃO"], "Porto de Manaus")
        self.assertEqual(
            aliases["SUPER TERMINAIS COMÉRCIO E INDÚSTRIA"],
            "Porto de Manaus",
        )
        self.assertEqual(aliases["BRAM006"], "Porto de Manaus")
        self.assertEqual(aliases["BRAM012"], "Porto de Manaus")


if __name__ == "__main__":
    unittest.main()
