import unittest

import httpx

from google_play_scraper.client import _build_proxy_mounts


class ClientProxyMountsTest(unittest.TestCase):
    def test_supports_requests_style_proxy_keys(self):
        mounts = _build_proxy_mounts(
            {"http": "http://localhost:8000", "https": "http://localhost:8001"}
        )

        self.assertEqual(set(mounts.keys()), {"http://", "https://"})

    def test_supports_scheme_style_proxy_keys(self):
        mounts = _build_proxy_mounts(
            {"http://": "http://localhost:8000", "https://": "http://localhost:8001"}
        )

        self.assertEqual(set(mounts.keys()), {"http://", "https://"})

    def test_https_only_proxy_creates_only_https_mount(self):
        mounts = _build_proxy_mounts({"https": "http://localhost:8001"})

        self.assertEqual(set(mounts.keys()), {"https://"})

    def test_async_proxy_mounts_use_async_transport(self):
        mounts = _build_proxy_mounts(
            {"https": "http://localhost:8001"}, async_client=True
        )

        self.assertIsInstance(mounts["https://"], httpx.AsyncHTTPTransport)
