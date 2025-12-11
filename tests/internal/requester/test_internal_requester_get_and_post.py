import unittest
from unittest.mock import patch, Mock

import requests

from google_play_scraper.internal.request import Requester


class RequesterGetAndPostTest(unittest.TestCase):

    def _make_requester(self):
        session = Mock(spec=requests.Session)
        # session will not be used because we mock Requester.request
        return Requester(session=session, throttle=None, default_lang="en", default_country="us")

    @patch.object(Requester, "request", autospec=True)
    def test_get_delegates_with_method_and_args(self, request_mock):
        request_mock.return_value = "OK"

        requester = self._make_requester()
        path = "/some/path"
        params = {"q": "abc"}
        headers = {"X-Test": "1"}

        result = requester.get(path=path, params=params, headers=headers)

        # returned value must be exactly what Requester.request returned
        self.assertEqual(result, "OK")

        # Ensure Requester.request was called once with expected values
        request_mock.assert_called_once()
        args, kwargs = request_mock.call_args

        # First positional argument is `self` (requester instance)
        self.assertIs(args[0], requester)
        # Second positional is method, third is path
        self.assertEqual(args[1], "GET")
        self.assertEqual(args[2], path)

        # Keyword args should contain only params and headers for GET
        self.assertEqual(kwargs.get("params"), params)
        self.assertEqual(kwargs.get("headers"), headers)
        # `data` should not be provided for GET
        self.assertNotIn("data", kwargs)

    @patch.object(Requester, "request", autospec=True)
    def test_get_with_defaults(self, request_mock):
        requester = self._make_requester()
        requester.get(path="/defaults")

        args, kwargs = request_mock.call_args
        self.assertIs(args[0], requester)
        self.assertEqual(args[1], "GET")
        self.assertEqual(args[2], "/defaults")
        # params and headers default to None
        self.assertIn("params", kwargs)
        self.assertIsNone(kwargs.get("params"))
        self.assertIn("headers", kwargs)
        self.assertIsNone(kwargs.get("headers"))
        self.assertNotIn("data", kwargs)

    @patch.object(Requester, "request", autospec=True)
    def test_post_delegates_with_method_and_args(self, request_mock):
        request_mock.return_value = "POSTED"

        requester = self._make_requester()
        path = "/post/path"
        params = {"p": 1}
        data = b"payload"
        headers = {"Content-Type": "text/plain"}

        result = requester.post(path=path, params=params, data=data, headers=headers)

        self.assertEqual(result, "POSTED")

        request_mock.assert_called_once()
        args, kwargs = request_mock.call_args

        self.assertIs(args[0], requester)
        self.assertEqual(args[1], "POST")
        self.assertEqual(args[2], path)
        self.assertEqual(kwargs.get("params"), params)
        self.assertEqual(kwargs.get("data"), data)
        self.assertEqual(kwargs.get("headers"), headers)

    @patch.object(Requester, "request", autospec=True)
    def test_post_with_defaults(self, request_mock):
        requester = self._make_requester()
        requester.post(path="/defaults")

        args, kwargs = request_mock.call_args
        self.assertIs(args[0], requester)
        self.assertEqual(args[1], "POST")
        self.assertEqual(args[2], "/defaults")
        # Defaults are None when not supplied
        self.assertIn("params", kwargs)
        self.assertIsNone(kwargs.get("params"))
        self.assertIn("data", kwargs)
        self.assertIsNone(kwargs.get("data"))
        self.assertIn("headers", kwargs)
        self.assertIsNone(kwargs.get("headers"))


if __name__ == "__main__":
    unittest.main()
