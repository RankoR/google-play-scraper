import unittest

from google_play_scraper.internal.extractor import ElementSpec


class ElementSpecTest(unittest.TestCase):

    # Happy paths
    def test_extract_from_dict_path(self):
        source = {"a": {"b": 123}}
        spec = ElementSpec(path=["a", "b"])
        self.assertEqual(spec.extract(source), 123)

    def test_extract_from_list_path(self):
        source = [["x", "y"], [10, 20, 30]]
        spec = ElementSpec(path=[1, 2])  # source[1][2] == 30
        self.assertEqual(spec.extract(source), 30)

    def test_extract_applies_transformer(self):
        source = {"n": 7}
        spec = ElementSpec(path=["n"], transformer=lambda v: v * 3)
        self.assertEqual(spec.extract(source), 21)

    def test_extract_uses_fallback_path_when_primary_none(self):
        source = {"primary": None, "alt": {"value": 42}}
        spec = ElementSpec(path=["primary"], fallback_path=["alt", "value"])
        self.assertEqual(spec.extract(source), 42)

    # Edge and error paths
    def test_lookup_wrong_type_returns_none(self):
        # Expecting dict for string key, but encounter a list
        source = [1, 2, 3]
        spec = ElementSpec(path=["not_a_dict_key"])  # first current is a list
        self.assertIsNone(spec.extract(source))

    def test_list_index_out_of_range_returns_none(self):
        source = [10, 20]
        spec = ElementSpec(path=[5])  # out of range
        self.assertIsNone(spec.extract(source))

    def test_unknown_key_type_in_path_returns_none(self):
        class Weird:
            pass

        source = {"a": 1}
        # Although type hints say int|str, runtime may get anything; code should return None
        spec = ElementSpec(path=[Weird()])  # type: ignore[arg-type]
        self.assertIsNone(spec.extract(source))

    def test_early_none_in_chain_returns_none(self):
        source = {"a": None}
        spec = ElementSpec(path=["a", "b"])  # after first hop current is None
        self.assertIsNone(spec.extract(source))

    def test_transformer_exception_is_swallowed(self):
        def boom(_):
            raise ValueError("boom")

        source = {"x": 5}
        spec = ElementSpec(path=["x"], transformer=boom)
        self.assertIsNone(spec.extract(source))


if __name__ == "__main__":
    unittest.main()
