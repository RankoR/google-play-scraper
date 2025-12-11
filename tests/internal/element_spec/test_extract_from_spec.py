import unittest

from google_play_scraper.internal.extractor import ElementSpec, extract_from_spec


class TestExtractFromSpec(unittest.TestCase):

    def test_extract_from_spec_multiple(self):
        source = {"a": {"b": 1}, "arr": [0, 1, 2]}
        specs = {
            "one": ElementSpec(["a", "b"]),
            "two": ElementSpec(["arr", 2], transformer=lambda v: v + 10),
        }
        result = extract_from_spec(source, specs)
        self.assertEqual(result, {"one": 1, "two": 12})

    def test_extract_from_spec_includes_none_values(self):
        source = {"a": {"b": 1}}
        specs = {
            "ok": ElementSpec(["a", "b"]),
            "missing": ElementSpec(["a", "z"]),
        }
        result = extract_from_spec(source, specs)
        self.assertEqual(result.get("ok"), 1)
        self.assertIsNone(result.get("missing"))


if __name__ == "__main__":
    unittest.main()
