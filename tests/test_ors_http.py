import unittest

from modules.road.ors.http import ORSHttpClient
from modules.road.ors.structures import ORSConfig, RateLimited


class _FakeQuotaResponse:
    status_code = 403
    text = "Daily quota exceeded"
    content = b'{"error":"Daily quota exceeded"}'

    def raise_for_status(self) -> None:
        raise AssertionError("raise_for_status should not run for quota-limited responses")

    def json(self):  # pragma: no cover - not reached in this test
        return {"error": "Daily quota exceeded"}


class ORSHttpClientTests(unittest.TestCase):
    def test_request_treats_quota_403_as_rate_limited(self) -> None:
        client = ORSHttpClient(ORSConfig(api_key="test-key", cache_enabled=False))
        client._session.request = lambda **_kwargs: _FakeQuotaResponse()  # type: ignore[method-assign]

        with self.assertRaises(RateLimited):
            client.request("GET", "/geocode/search", params={"text": "Sao Paulo"})


if __name__ == "__main__":
    unittest.main()
