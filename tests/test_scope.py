import unittest
from types import SimpleNamespace

from app.tasks import _request_options


class RequestScopeTests(unittest.TestCase):
    def test_surface_source_does_not_set_proxy(self):
        options = _request_options(
            SimpleNamespace(use_tor=False, url="http://fixture/sample.html")
        )
        self.assertNotIn("proxies", options)
        self.assertFalse(options["allow_redirects"])

    def test_tor_source_fails_closed_without_proxy(self):
        from app import tasks

        previous = tasks.settings.TOR_PROXY_URL
        previous_allowlist = tasks.settings.SOURCE_HOST_ALLOWLIST
        tasks.settings.TOR_PROXY_URL = None
        tasks.settings.SOURCE_HOST_ALLOWLIST = ("example.onion",)
        try:
            with self.assertRaisesRegex(RuntimeError, "refusing direct request"):
                _request_options(
                    SimpleNamespace(use_tor=True, url="http://example.onion/feed")
                )
        finally:
            tasks.settings.TOR_PROXY_URL = previous
            tasks.settings.SOURCE_HOST_ALLOWLIST = previous_allowlist

    def test_onion_source_cannot_use_direct_http(self):
        with self.assertRaisesRegex(RuntimeError, "use_tor=true"):
            _request_options(
                SimpleNamespace(use_tor=False, url="http://example.onion/feed")
            )

    def test_tor_proxy_must_preserve_remote_dns(self):
        from app import tasks

        previous = tasks.settings.TOR_PROXY_URL
        previous_allowlist = tasks.settings.SOURCE_HOST_ALLOWLIST
        tasks.settings.TOR_PROXY_URL = "socks5://127.0.0.1:9050"
        tasks.settings.SOURCE_HOST_ALLOWLIST = ("example.onion",)
        try:
            with self.assertRaisesRegex(RuntimeError, "socks5h"):
                _request_options(
                    SimpleNamespace(use_tor=True, url="http://example.onion/feed")
                )
        finally:
            tasks.settings.TOR_PROXY_URL = previous
            tasks.settings.SOURCE_HOST_ALLOWLIST = previous_allowlist

    def test_unapproved_source_host_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "SOURCE_HOST_ALLOWLIST"):
            _request_options(
                SimpleNamespace(use_tor=False, url="https://unapproved.example/feed")
            )


if __name__ == "__main__":
    unittest.main()
