import unittest

from pydantic import ValidationError

from google_play_scraper.models import AppDetails


class ModelsAppDetailsTest(unittest.TestCase):

    def test_defaults_on_minimal_instantiation(self):
        model = AppDetails(app_id="com.example.app", title="Example App")

        # Inherited required fields
        self.assertEqual(model.app_id, "com.example.app")
        self.assertEqual(model.title, "Example App")

        # Key defaults
        self.assertEqual(model.description, "")
        self.assertEqual(model.description_html, "")
        self.assertEqual(model.installs, "0")
        self.assertEqual(model.min_installs, 0)
        self.assertEqual(model.max_installs, 0)
        self.assertEqual(model.ratings, 0)
        self.assertEqual(model.reviews, 0)
        self.assertEqual(model.price, 0.0)
        self.assertTrue(model.available)
        self.assertFalse(model.offers_iap)
        self.assertEqual(model.android_version, "VARY")

        # Collections default factories
        self.assertEqual(model.histogram, {})
        self.assertEqual(model.screenshots, [])
        self.assertEqual(model.comments, [])

        # Optional None defaults (spot-check a few)
        self.assertIsNone(model.currency)
        self.assertIsNone(model.developer_email)
        self.assertIsNone(model.developer_website)
        self.assertIsNone(model.privacy_policy)
        self.assertIsNone(model.header_image)
        self.assertIsNone(model.video)
        self.assertIsNone(model.updated)

    def test_coercion_of_install_ratings_reviews_from_strings(self):
        model = AppDetails(
            app_id="id",
            title="t",
            min_installs="5,000,000+",
            max_installs="10,000,000+",
            ratings="1,234",
            reviews="56,789",
        )

        self.assertEqual(model.min_installs, 5000000)
        self.assertEqual(model.max_installs, 10000000)
        self.assertEqual(model.ratings, 1234)
        self.assertEqual(model.reviews, 56789)

        # Invalid strings should default to 0 via coercion
        model2 = AppDetails(
            app_id="id2",
            title="t2",
            min_installs="N/A",
            max_installs="-",
            ratings="abc",
            reviews="?",
        )
        self.assertEqual(model2.min_installs, 0)
        self.assertEqual(model2.max_installs, 0)
        self.assertEqual(model2.ratings, 0)
        self.assertEqual(model2.reviews, 0)

    def test_price_coercion_and_invalid_defaults(self):
        # Comma decimal should be converted to dot
        model = AppDetails(app_id="id", title="t", price="0,99")
        self.assertAlmostEqual(model.price, 0.99, places=2)

        # Dot decimal stays as-is, str acceptable
        model2 = AppDetails(app_id="id2", title="t2", price="1.49")
        self.assertAlmostEqual(model2.price, 1.49, places=2)

        # Invalid string defaults to 0.0
        model3 = AppDetails(app_id="id3", title="t3", price="free")
        self.assertEqual(model3.price, 0.0)

    def test_url_fields_validation_accept_valid_and_reject_invalid(self):
        # Accept valid http(s) URLs
        valid = AppDetails(
            app_id="id",
            title="t",
            icon="https://example.com/icon.png",
            developer_website="https://example.com",
            privacy_policy="http://example.com/privacy",
            header_image="https://example.com/header.jpg",
            screenshots=[
                "https://example.com/s1.png",
                "http://example.com/s2.png",
            ],
            video="https://cdn.example.com/video.mp4",
        )

        self.assertTrue(str(valid.icon).startswith("https://"))
        self.assertTrue(str(valid.developer_website).startswith("https://"))
        self.assertTrue(str(valid.privacy_policy).startswith("http"))
        self.assertEqual(len(valid.screenshots), 2)
        self.assertTrue(all(str(u).startswith("http") for u in valid.screenshots))
        self.assertTrue(str(valid.video).startswith("https://"))

        # Reject invalid URLs
        with self.assertRaises(ValidationError):
            AppDetails(app_id="id", title="t", icon="not-a-url")

        with self.assertRaises(ValidationError):
            AppDetails(app_id="id", title="t", developer_website="ftp://example.com")

        with self.assertRaises(ValidationError):
            AppDetails(app_id="id", title="t", privacy_policy="//relative/path")

        with self.assertRaises(ValidationError):
            AppDetails(app_id="id", title="t", screenshots=["https://ok", "bad-url"])


if __name__ == "__main__":
    unittest.main()
