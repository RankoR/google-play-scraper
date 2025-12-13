import unittest
from unittest.mock import Mock, patch

import httpx

from google_play_scraper.exceptions import (
    AppNotFound,
    QuotaExceeded,
    GooglePlayError,
)
from google_play_scraper.internal.request import Requester


class RequesterRequestTest(unittest.TestCase):

    def _make_requester(self, session=None, throttle=None, lang="en", country="us"):
        if session is None:
            session = Mock(spec=httpx.Client)
        return Requester(session=session, throttle=throttle, default_lang=lang, default_country=country)

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_happy_path_builds_url_merges_headers_and_params_and_returns_text(self, _wait_mock):
        session = Mock(spec=httpx.Client)
        response = Mock()
        response.raise_for_status.return_value = None
        response.text = "OK"
        session.request.return_value = response

        requester = self._make_requester(session=session)

        custom_headers = {"Content-Type": "text/plain", "X-Test": "1"}
        params = {"q": "abc"}
        data = b"payload"

        result = requester.request(
            method="GET",
            path="/test/path",
            params=params.copy(),
            data=data,
            headers=custom_headers.copy(),
        )

        # Should return response.text
        self.assertEqual(result, "OK")

        # throttle wait should be called
        _wait_mock.assert_called_once_with(requester)

        # URL should be BASE_URL + path
        expected_url = f"{Requester.BASE_URL}/test/path"

        # Verify call to session.request
        session.request.assert_called_once()
        call_kwargs = session.request.call_args.kwargs
        self.assertEqual(call_kwargs["method"], "GET")
        self.assertEqual(call_kwargs["url"], expected_url)
        self.assertEqual(call_kwargs["data"], data)

        # Headers: defaults + overrides (custom overrides default Content-Type and adds X-Test)
        sent_headers = call_kwargs["headers"]
        self.assertEqual(sent_headers["Origin"], Requester.BASE_URL)
        self.assertIn("User-Agent", sent_headers)
        self.assertEqual(sent_headers["Content-Type"], "text/plain")
        self.assertEqual(sent_headers.get("X-Test"), "1")

        # Params should include defaults (hl/gl) when not provided, and keep provided ones
        sent_params = call_kwargs["params"]
        self.assertEqual(sent_params["q"], "abc")
        self.assertEqual(sent_params["hl"], "en")
        self.assertEqual(sent_params["gl"], "us")

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_params_respect_provided_hl_gl(self, _wait_mock):
        session = Mock(spec=httpx.Client)
        response = Mock()
        response.raise_for_status.return_value = None
        response.text = "OK"
        session.request.return_value = response

        requester = self._make_requester(session=session, lang="en", country="us")

        params = {"hl": "fr", "gl": "ca", "x": 1}
        requester.request("GET", "/p", params=params)

        call_kwargs = session.request.call_args.kwargs
        sent_params = call_kwargs["params"]
        # Provided hl and gl must be preserved
        self.assertEqual(sent_params["hl"], "fr")
        self.assertEqual(sent_params["gl"], "ca")
        self.assertEqual(sent_params["x"], 1)

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_http_error_404_raises_app_not_found_with_url(self, _wait_mock):
        session = Mock(spec=httpx.Client)
        response = Mock()
        request = httpx.Request("GET", "https://example.test")
        http_err = httpx.HTTPStatusError(
            message="Not Found",
            request=request,
            response=httpx.Response(404, request=request),
        )
        response.raise_for_status.side_effect = http_err
        session.request.return_value = response

        requester = self._make_requester(session=session)

        with self.assertRaises(AppNotFound) as ctx:
            requester.request("GET", "/notfound")

        self.assertIn(f"{Requester.BASE_URL}/notfound", str(ctx.exception))

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_http_error_429_or_503_raise_quota_exceeded(self, _wait_mock):
        for code in (429, 503):
            with self.subTest(code=code):
                session = Mock(spec=httpx.Client)
                response = Mock()
                request = httpx.Request("GET", "https://example.test")
                http_err = httpx.HTTPStatusError(
                    message="HTTP error",
                    request=request,
                    response=httpx.Response(code, request=request),
                )
                response.raise_for_status.side_effect = http_err
                session.request.return_value = response

                requester = self._make_requester(session=session)

                with self.assertRaises(QuotaExceeded):
                    requester.request("GET", "/quota")

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_http_error_other_raises_google_play_error_with_code(self, _wait_mock):
        session = Mock(spec=httpx.Client)
        response = Mock()
        request = httpx.Request("GET", "https://example.test")
        http_err = httpx.HTTPStatusError(
            message="Server error",
            request=request,
            response=httpx.Response(500, request=request),
        )
        response.raise_for_status.side_effect = http_err
        session.request.return_value = response

        requester = self._make_requester(session=session)

        with self.assertRaises(GooglePlayError) as ctx:
            requester.request("GET", "/err")

        self.assertIn("HTTP Error 500", str(ctx.exception))

    @patch.object(Requester, "_wait_for_throttle", autospec=True)
    def test_request_exception_translates_to_google_play_error(self, _wait_mock):
        session = Mock(spec=httpx.Client)
        # Simulate network-level exception from session.request itself
        session.request.side_effect = httpx.TimeoutException("read timed out")

        requester = self._make_requester(session=session)

        with self.assertRaises(GooglePlayError) as ctx:
            requester.request("GET", "/timeout")

        self.assertIn("Network error: ", str(ctx.exception))


    @patch("google_play_scraper.internal.request.time.sleep")
    @patch("google_play_scraper.internal.request.time.time")
    def test_wait_for_throttle_no_throttle_no_sleep_and_updates_time(self, mock_time, mock_sleep):
        # time.time will be called twice inside _wait_for_throttle
        mock_time.side_effect = [100.0, 100.0]
        requester = self._make_requester(throttle=None)

        # sanity precondition
        self.assertEqual(requester._throttle_delay, 0)

        requester._wait_for_throttle()

        # Should not sleep when throttle is disabled
        mock_sleep.assert_not_called()
        # Last request time should be updated to the last time.time() value
        self.assertEqual(requester._last_request_time, 100.0)

    @patch("google_play_scraper.internal.request.time.sleep")
    @patch("google_play_scraper.internal.request.time.time")
    def test_wait_for_throttle_sleeps_for_remaining_delay(self, mock_time, mock_sleep):
        # throttle=2 => delay=0.5s
        requester = self._make_requester(throttle=2)
        requester._last_request_time = 10.0

        # First call computes elapsed (10.1 - 10.0 = 0.1), should sleep 0.4
        # Second call sets the new last_request_time
        mock_time.side_effect = [10.1, 10.5]

        requester._wait_for_throttle()

        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args.args[0]
        self.assertAlmostEqual(sleep_arg, 0.4, places=6)
        self.assertEqual(requester._last_request_time, 10.5)

    @patch("google_play_scraper.internal.request.time.sleep")
    @patch("google_play_scraper.internal.request.time.time")
    def test_wait_for_throttle_no_sleep_if_elapsed_greater_or_equal_delay(self, mock_time, mock_sleep):
        # throttle=1 => delay=1.0s
        requester = self._make_requester(throttle=1)
        requester._last_request_time = 10.0

        # elapsed = 1.0, should not sleep
        mock_time.side_effect = [11.0, 11.0]

        requester._wait_for_throttle()

        mock_sleep.assert_not_called()
        self.assertEqual(requester._last_request_time, 11.0)


if __name__ == "__main__":
    unittest.main()
