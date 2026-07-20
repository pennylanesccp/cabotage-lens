import unittest
from dataclasses import dataclass

import requests

from modules.cabotage.geografos_distance_references import (
    GEOGRAFOS_SOURCE_LABEL,
    build_geografos_direct_port_pair_url,
    candidate_geografos_direct_port_pair_urls,
    fetch_geografos_distance_reference,
    fetch_geografos_direct_distance_reference,
    parse_geografos_direct_distance_html,
    port_slug,
)


SANTOS_VILA_HTML = """
<!doctype html>
<html>
  <body>
    <h1>Distância Marítima Entre o Porto Santos - SP e o Porto Vila do Conde - PA.</h1>
    <h2>Porto de Origem: Santos - SP</h2>
    <p>Porto do Destino: Vila do Conde - PA</p>
    <p>Distância: 4.495 Km ou 2.427 Milhas Náuticas</p>
  </body>
</html>
"""


@dataclass
class _Response:
    text: str
    status_code: int = 200
    url: str = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, responses: dict[str, _Response]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs: object) -> _Response:
        self.requests.append((url, dict(kwargs)))
        return self.responses.get(url, _Response("", status_code=404, url=url))


class GeografosDistanceReferenceTests(unittest.TestCase):
    def test_parse_direct_port_pair_html_reads_port_names_km_and_nm(self) -> None:
        parsed = parse_geografos_direct_distance_html(SANTOS_VILA_HTML)

        self.assertEqual(parsed["page_origin_port"], "Santos - SP")
        self.assertEqual(parsed["page_destination_port"], "Vila do Conde - PA")
        self.assertEqual(parsed["distance_km"], 4495.0)
        self.assertEqual(parsed["reported_distance_nm"], 2427.0)

    def test_parse_rejects_html_without_the_direct_pair_distance(self) -> None:
        with self.assertRaisesRegex(ValueError, "origin, destination, and km/nm"):
            parse_geografos_direct_distance_html("<html><body>Publicidade</body></html>")

    def test_candidate_urls_try_both_directions_and_normalize_port_labels(self) -> None:
        candidates = candidate_geografos_direct_port_pair_urls(
            "Porto de Santos - SP",
            "Vila do Conde",
        )

        self.assertEqual(
            candidates,
            (
                "https://www.geografos.com.br/viagem-maritima-entre-portos-brasil/"
                "distancia-entre-porto-santos-e-porto-vila-do-conde.php",
                "https://www.geografos.com.br/viagem-maritima-entre-portos-brasil/"
                "distancia-entre-porto-vila-do-conde-e-porto-santos.php",
            ),
        )
        self.assertEqual(port_slug("Pecém - CE"), "pecem")
        self.assertEqual(port_slug("porto-santos"), "santos")
        self.assertEqual(
            build_geografos_direct_port_pair_url("santos", "vila-do-conde"),
            candidates[0],
        )

    def test_fetch_uses_reverse_page_when_it_is_the_verified_source(self) -> None:
        forward, reverse = candidate_geografos_direct_port_pair_urls("santos", "vila-do-conde")
        reverse_html = SANTOS_VILA_HTML.replace(
            "Porto de Origem: Santos - SP",
            "Porto de Origem: Vila do Conde - PA",
        ).replace(
            "Porto do Destino: Vila do Conde - PA",
            "Porto do Destino: Santos - SP",
        )
        session = _Session(
            {
                forward: _Response("", status_code=404, url=forward),
                reverse: _Response(reverse_html, url=reverse),
            }
        )

        reference = fetch_geografos_direct_distance_reference(
            "santos",
            "vila-do-conde",
            session=session,
            timeout_s=7.0,
            retrieved_at="2026-07-19",
        )

        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(reference["distance_km"], 4495.0)
        self.assertEqual(reference["reported_distance_nm"], 2427.0)
        self.assertEqual(reference["source"], "geografos_reference")
        self.assertEqual(reference["source_label"], GEOGRAFOS_SOURCE_LABEL)
        self.assertEqual(reference["source_type"], "external_reference")
        self.assertEqual(reference["source_url"], reverse)
        self.assertEqual(reference["retrieved_at"], "2026-07-19")
        self.assertTrue(reference["symmetric"])
        self.assertEqual(reference["requested_origin_slug"], "santos")
        self.assertEqual(reference["requested_destination_slug"], "vila-do-conde")
        self.assertEqual(reference["matched_page_origin_slug"], "vila-do-conde")
        self.assertEqual(reference["matched_page_destination_slug"], "santos")
        self.assertEqual(reference["matched_candidate_direction"], "reverse")
        self.assertEqual(len(session.requests), 2)
        self.assertEqual(session.requests[0][1]["timeout"], 7.0)

    def test_fetch_tries_registered_slug_aliases_until_a_page_matches(self) -> None:
        forward, _ = candidate_geografos_direct_port_pair_urls("santos", "vila-do-conde")
        session = _Session({forward: _Response(SANTOS_VILA_HTML, url=forward)})

        reference = fetch_geografos_distance_reference(
            ["porto-santos", "porto-brssz"],
            ["porto-vila-do-conde", "porto-brvlc"],
            session=session,
            retrieved_at="2026-07-19",
        )

        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(reference["distance_km"], 4495.0)
        self.assertEqual(reference["requested_origin_slug_candidates"], ["santos", "brssz"])
        self.assertEqual(
            reference["requested_destination_slug_candidates"],
            ["vila-do-conde", "brvlc"],
        )

    def test_fetch_rejects_a_page_whose_pair_does_not_match_its_candidate_url(self) -> None:
        forward, reverse = candidate_geografos_direct_port_pair_urls("santos", "vila-do-conde")
        unrelated_html = SANTOS_VILA_HTML.replace("Vila do Conde", "Pecém")
        session = _Session(
            {
                forward: _Response(unrelated_html, url=forward),
                reverse: _Response(unrelated_html, url=reverse),
            }
        )

        reference = fetch_geografos_direct_distance_reference(
            "santos",
            "vila-do-conde",
            session=session,
            retrieved_at="2026-07-19",
        )

        self.assertIsNone(reference)
        self.assertEqual(len(session.requests), 2)


if __name__ == "__main__":
    unittest.main()
