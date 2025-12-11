import unittest

from google_play_scraper.internal.parser import ScriptDataParser


class ScriptDataParserParseTest(unittest.TestCase):

    def test_parse_multiple_scripts_collects_data(self):
        html = (
            "<html><head></head><body>"
            # valid script 1
            "<script>AF_initDataCallback({key: 'ds:5', data: [1,2,3], sideChannel: {}});</script>"
            # valid script 2 with object payload
            "<script>AF_initDataCallback({key: 'ds:7', data: {\"a\": 1, \"b\": [4,5]}, sideChannel: {}});</script>"
            # invalid JSON payload should be ignored
            "<script>AF_initDataCallback({key: 'ds:9', data: [1,], sideChannel: {}});</script>"
            "</body></html>"
        )

        result = ScriptDataParser.parse(html)

        self.assertEqual(result.get("ds:5"), [1, 2, 3])
        self.assertEqual(result.get("ds:7"), {"a": 1, "b": [4, 5]})
        self.assertNotIn("ds:9", result)  # invalid JSON ignored

    def test_parse_no_matches_returns_empty_dict(self):
        html = "<html><body><div>No AF_initDataCallback here</div></body></html>"
        self.assertEqual(ScriptDataParser.parse(html), {})

    def test_parse_ignores_invalid_json_without_raising(self):
        html = (
            "<script>AF_initDataCallback({key: 'ds:1', data: [1,], sideChannel: {}});</script>"
        )
        # Should not raise and should return empty dict since the only match is invalid
        self.assertEqual(ScriptDataParser.parse(html), {})

    def test_parse_with_service_block_does_not_crash(self):
        # Include a service block that matches _SERVICE_REGEX and _SERVICE_VALUE_REGEX
        service_block = (
            "; var AF_dataServiceRequests = {'ds:5': {}}; var AF_initDataChunkQueue"
        )
        html = (
            "<html><body>"
            f"{service_block}"
            "<script>AF_initDataCallback({key: 'ds:2', data: [10,20], sideChannel: {}});</script>"
            "</body></html>"
        )

        # Should not raise and should still parse the standard script data
        result = ScriptDataParser.parse(html)
        self.assertEqual(result, {"ds:2": [10, 20]})


if __name__ == "__main__":
    unittest.main()
