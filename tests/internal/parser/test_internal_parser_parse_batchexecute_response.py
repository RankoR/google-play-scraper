import unittest

from google_play_scraper.internal.parser import ScriptDataParser


class ScriptDataParserParseBatchExecuteResponseTest(unittest.TestCase):

    def test_happy_path_clean_json_outer_envelope(self):
        # Clean JSON string representing the standard outer envelope
        text = '[["wrb.fr","RPC","[1,2,3]"]]'
        self.assertEqual(ScriptDataParser.parse_batchexecute_response(text), [1, 2, 3])

    def test_happy_path_with_xssi_prefix_stripped(self):
        # Input starts with prefix ")]}'" and then valid JSON envelope
        text = ")]}'\n[[\"wrb.fr\",\"RPC\",\"[4,5,6]\"]]"
        self.assertEqual(ScriptDataParser.parse_batchexecute_response(text), [4, 5, 6])

    def test_happy_path_chunked_format_only_valid_line_is_parsed(self):
        # Chunked/streamed format with lengths and multiple lines; only the line
        # beginning with [[ and containing "wrb.fr" should be parsed
        chunked = "\n".join([
            "24",
            "[[\"not.wrb\",1,\"[]\"]]",  # starts with [[ but not the desired marker
            "12",
            "[[\"wrb.fr\",\"RPC\",\"[7,8]\"]]",
            "0",
        ])
        self.assertEqual(ScriptDataParser.parse_batchexecute_response(chunked), [7, 8])

    def test_error_clean_json_invalid_then_no_valid_chunk_returns_empty(self):
        # Whole text is not valid JSON; chunked lines either don't start with [[ or invalid
        text = "not a json\n1\n2\n3"  # no line starts with [[
        self.assertEqual(ScriptDataParser.parse_batchexecute_response(text), [])

    def test_error_chunked_lines_invalid_or_wrong_marker_returns_empty(self):
        # Lines start with [[ but are either invalid JSON or wrong marker; should skip all
        lines = "\n".join([
            "[[invalid json]]",  # invalid JSON
            "[[\"other\",\"RPC\",\"[1]\"]]",  # correct JSON shape but not wrb.fr marker
        ])
        self.assertEqual(ScriptDataParser.parse_batchexecute_response(lines), [])


if __name__ == "__main__":
    unittest.main()
