from datetime import datetime
import unittest
from google_play_scraper.client import _ts_to_date


class ClientTsToDateTest(unittest.TestCase):

    def test_positive_integer_returns_datetime_fromtimestamp(self):
        # Use a fixed Unix timestamp
        ts = 1_600_000_000  # 2020-09-13T12:26:40Z
        expected = datetime.fromtimestamp(ts)

        result = _ts_to_date(ts)

        self.assertIsInstance(result, datetime)
        self.assertEqual(result, expected)

    def test_zero_returns_none(self):
        self.assertIsNone(_ts_to_date(0))

    def test_falsy_values_return_none(self):
        # Although the function is annotated for int, it should handle falsy inputs defensively
        self.assertIsNone(_ts_to_date(None))
        self.assertIsNone(_ts_to_date(False))
