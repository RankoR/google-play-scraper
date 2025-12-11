import unittest

from google_play_scraper.models import AppOverview


class ModelsAppOverviewTest(unittest.TestCase):

    def test_minimal_instantiation(self):
        model = AppOverview(app_id="com.example.app", title="Example App")

        self.assertEqual(model.app_id, "com.example.app")
        self.assertEqual(model.title, "Example App")

        # Optional fields should default to None
        self.assertIsNone(model.icon)
        self.assertIsNone(model.developer)
        self.assertIsNone(model.developer_id)
        self.assertIsNone(model.score)
        self.assertIsNone(model.score_text)
        self.assertIsNone(model.price_text)
        self.assertIsNone(model.free)
        self.assertIsNone(model.summary)

    def test_optional_fields_accept_none(self):
        model = AppOverview(
            app_id="id",
            title="t",
            icon=None,
            developer=None,
            developer_id=None,
            score=None,
            score_text=None,
            price_text=None,
            free=None,
            summary=None,
        )

        # All explicitly provided Nones should be preserved
        self.assertIsNone(model.icon)
        self.assertIsNone(model.developer)
        self.assertIsNone(model.developer_id)
        self.assertIsNone(model.score)
        self.assertIsNone(model.score_text)
        self.assertIsNone(model.price_text)
        self.assertIsNone(model.free)
        self.assertIsNone(model.summary)

    def test_score_coercion_from_int_float_and_str(self):
        # int -> float
        m1 = AppOverview(app_id="id1", title="t1", score=4)
        self.assertIsInstance(m1.score, float)
        self.assertEqual(m1.score, 4.0)

        # float -> float
        m2 = AppOverview(app_id="id2", title="t2", score=4.5)
        self.assertEqual(m2.score, 4.5)

        # string with dot -> float
        m3 = AppOverview(app_id="id3", title="t3", score="4.5")
        self.assertEqual(m3.score, 4.5)

        # string with comma -> float
        m4 = AppOverview(app_id="id4", title="t4", score="4,5")
        self.assertEqual(m4.score, 4.5)


if __name__ == "__main__":
    unittest.main()
