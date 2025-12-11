import unittest

from google_play_scraper.client import _normalize_histogram


class ClientNormalizeHistogramTest(unittest.TestCase):

    def test_happy_path_extracts_counts_per_star(self):
        # data layout: [None, [string_count, int_count], ...] for stars 1..5
        data = [
            None,
            ["5", 5],
            ["10", 10],
            ["15", 15],
            ["20", 20],
            ["25", 25],
            # extra items beyond the required five should be ignored
            ["extra", 999],
        ]

        result = _normalize_histogram(data)

        self.assertEqual(result, {
            "1": 5,
            "2": 10,
            "3": 15,
            "4": 20,
            "5": 25,
        })

    def test_fewer_than_six_elements_returns_zeros(self):
        # Empty list
        self.assertEqual(_normalize_histogram([]), {str(i): 0 for i in range(1, 6)})

        # Only five elements (len < 6) — should also return all zeros
        short_data = [None, ["5", 5], ["10", 10], ["15", 15], ["20", 20]]
        self.assertEqual(_normalize_histogram(short_data), {str(i): 0 for i in range(1, 6)})

    def test_malformed_elements_indexerror_defaults_to_zero(self):
        # Star 1 entry lacks the integer count at index 1 -> IndexError
        data = [
            None,
            ["5"],  # malformed (missing int count)
            ["10", 10],
            ["15", 15],
            ["20", 20],
            ["25", 25],
        ]

        result = _normalize_histogram(data)
        self.assertEqual(result, {
            "1": 0,  # defaulted due to IndexError
            "2": 10,
            "3": 15,
            "4": 20,
            "5": 25,
        })

    def test_malformed_elements_typeerror_defaults_to_zero(self):
        # Use non-subscriptable or None to trigger TypeError in data[i][1]
        data = [
            None,
            None,  # TypeError
            123,  # TypeError (int is not subscriptable)
            ["15", 15],
            ["20", 20],
            ["25", 25],
        ]

        result = _normalize_histogram(data)
        self.assertEqual(result, {
            "1": 0,
            "2": 0,
            "3": 15,
            "4": 20,
            "5": 25,
        })


if __name__ == "__main__":
    unittest.main()
