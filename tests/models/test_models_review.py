import unittest

from pydantic import ValidationError

from google_play_scraper.models import Review


class ModelsReviewTest(unittest.TestCase):

    def test_minimal_instantiation_defaults(self):
        model = Review(id="r1", user_name="Alice", score=5)

        # Required fields
        self.assertEqual(model.id, "r1")
        self.assertEqual(model.user_name, "Alice")
        self.assertEqual(model.score, 5)

        # Optional fields default to None (or 0 for thumbs_up)
        self.assertIsNone(model.user_image)
        self.assertIsNone(model.date)
        self.assertIsNone(model.title)
        self.assertIsNone(model.text)
        self.assertIsNone(model.reply_date)
        self.assertIsNone(model.reply_text)
        self.assertIsNone(model.version)
        self.assertEqual(model.thumbs_up, 0)

    def test_user_image_url_validation(self):
        # Accept valid http/https URLs
        m1 = Review(id="r2", user_name="Bob", score=4, user_image="https://example.com/u.png")
        self.assertTrue(str(m1.user_image).startswith("https://"))

        m2 = Review(id="r3", user_name="Carol", score=3, user_image="http://example.com/u.jpg")
        self.assertTrue(str(m2.user_image).startswith("http://"))

        # Reject invalid/unsupported URLs
        with self.assertRaises(ValidationError):
            Review(id="r4", user_name="Dan", score=2, user_image="not-a-url")

        # ftp scheme should be rejected for HttpUrl
        with self.assertRaises(ValidationError):
            Review(id="r5", user_name="Eve", score=1, user_image="ftp://example.com/u.png")

    def test_datetime_parsing_for_date_and_reply_date(self):
        m = Review(
            id="r6",
            user_name="Frank",
            score=5,
            date="2021-01-02T03:04:05",
            reply_date="2022-06-07T08:09:10",
        )

        self.assertEqual((m.date.year, m.date.month, m.date.day, m.date.hour, m.date.minute, m.date.second),
                         (2021, 1, 2, 3, 4, 5))
        self.assertEqual(
            (m.reply_date.year, m.reply_date.month, m.reply_date.day, m.reply_date.hour, m.reply_date.minute,
             m.reply_date.second), (2022, 6, 7, 8, 9, 10))

        # Invalid datetime strings should raise ValidationError
        with self.assertRaises(ValidationError):
            Review(id="r7", user_name="Gina", score=1, date="not-a-datetime")

        with self.assertRaises(ValidationError):
            Review(id="r8", user_name="Hank", score=1, reply_date="13-13-2020")

    def test_int_coercion_and_invalid_values(self):
        # Coerce numeric strings to int
        m = Review(id="r9", user_name="Ivy", score="5", thumbs_up="7")
        self.assertEqual(m.score, 5)
        self.assertEqual(m.thumbs_up, 7)

        # Invalid strings for int should raise ValidationError
        with self.assertRaises(ValidationError):
            Review(id="r10", user_name="Jack", score="five")

        with self.assertRaises(ValidationError):
            Review(id="r11", user_name="Kate", score=3, thumbs_up="many")

    def test_required_fields_enforced(self):
        with self.assertRaises(ValidationError):
            Review(user_name="Leo", score=4)  # missing id

        with self.assertRaises(ValidationError):
            Review(id="r12", score=4)  # missing user_name

        with self.assertRaises(ValidationError):
            Review(id="r13", user_name="Mia")  # missing score


if __name__ == "__main__":
    unittest.main()
