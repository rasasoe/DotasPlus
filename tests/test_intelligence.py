import unittest

from app.intelligence import extract_indicators, ioc_matches_asset


class IntelligenceTests(unittest.TestCase):
    def test_extracts_and_normalizes_indicators_from_local_fixture(self):
        body = """
        <html><body>
          Contact Security@Example.COM and review
          https://portal.example.com/leak?id=7 from 192.0.2.10.
          <script>ignored@example.net</script>
        </body></html>
        """

        text, indicators = extract_indicators(body)
        normalized = {
            (item["ioc_type"], item["normalized_value"]) for item in indicators
        }

        self.assertNotIn("ignored@example.net", text)
        self.assertIn(("email", "security@example.com"), normalized)
        self.assertIn(("ip", "192.0.2.10"), normalized)
        self.assertIn(("domain", "portal.example.com"), normalized)

    def test_domain_asset_matches_subdomain_url_and_email(self):
        self.assertTrue(
            ioc_matches_asset(
                "url",
                "https://portal.example.com/leak",
                "domain",
                "example.com",
            )
        )
        self.assertTrue(
            ioc_matches_asset(
                "email", "security@example.com", "domain", "example.com"
            )
        )
        self.assertFalse(
            ioc_matches_asset(
                "domain", "notexample.com", "domain", "example.com"
            )
        )


if __name__ == "__main__":
    unittest.main()
