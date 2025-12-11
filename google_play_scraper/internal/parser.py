import json
import re
from typing import Any


class ScriptDataParser:
    # Regex to find the <script> block
    _SCRIPT_REGEX = re.compile(r">AF_initDataCallback[\s\S]*?</script")
    # Regex to extract the 'ds:X' key
    _KEY_REGEX = re.compile(r"(ds:.*?)'")
    # Regex to extract the JSON data value
    _VALUE_REGEX = re.compile(r"data:([\s\S]*?), sideChannel: {}}\);</")

    # For Service Requests (RPC responses)
    _SERVICE_REGEX = re.compile(r"; var AF_dataServiceRequests[\s\S]*?; var AF_initDataChunkQueue")
    _SERVICE_VALUE_REGEX = re.compile(r"{'ds:[\s\S]*}}")

    @classmethod
    def parse(cls, html_response: str) -> dict[str, list | dict]:
        """
        Parses the HTML response and returns a dictionary where keys are 'ds:x'
        and values are the parsed JSON arrays.
        """
        data_map = {}

        # 1. Parse standard AF_initDataCallback
        matches = cls._SCRIPT_REGEX.findall(html_response)
        for match in matches:
            key_m = cls._KEY_REGEX.search(match)
            val_m = cls._VALUE_REGEX.search(match)

            if key_m and val_m:
                key = key_m.group(1)
                try:
                    data = json.loads(val_m.group(1))
                    data_map[key] = data
                except json.JSONDecodeError:
                    continue

        # 2. Parse service requests (found in some dynamic pages)
        service_match = cls._SERVICE_REGEX.search(html_response)
        if service_match:
            val_m = cls._SERVICE_VALUE_REGEX.search(service_match.group(0))
            if val_m:
                # The service request data is often raw JS object syntax, not valid JSON
                # (e.g. single quotes). However, Google usually sends valid JSON structure
                # inside the value regex. If it fails, we skip.
                # In the Node lib, they use `eval`. In Python, we must be careful.
                # Usually, this is handled by batchexecute response parsing separately.
                pass

        return data_map

    @staticmethod
    def parse_batchexecute_response(response_text: str) -> list[Any]:
        """
        Parses the batchexecute RPC response.
        Handles both clean JSON and chunked/streamed formats (prefixed with lengths).
        """
        if response_text.startswith(")]}'"):
            response_text = response_text[4:].strip()

        # Strategy 1: Try parsing the whole text as JSON
        try:
            return ScriptDataParser._extract_inner_data(json.loads(response_text))
        except json.JSONDecodeError:
            pass

        # Strategy 2: Handle chunked format (Length \n JSON \n Length \n JSON)
        # We look for the chunk containing the standard envelope [["wrb.fr", ...]]
        lines = response_text.splitlines()
        for line in lines:
            line = line.strip()
            # Fast check: valid envelopes usually start with [[
            if not line.startswith("[["):
                continue

            try:
                data = json.loads(line)
                # Verify it is the correct envelope type
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    # Check for "wrb.fr" marker which indicates the payload container
                    if len(data[0]) > 0 and data[0][0] == "wrb.fr":
                        return ScriptDataParser._extract_inner_data(data)
            except json.JSONDecodeError:
                continue

        return []

    @staticmethod
    def _extract_inner_data(outer_json: list) -> list[Any]:
        """Helper to extract the stringified JSON inside the RPC envelope."""
        try:
            # Standard format: [["wrb.fr", "RPC_ID", "INNER_JSON_STRING", ...]]
            inner_data_str = outer_json[0][2]
            if inner_data_str:
                return json.loads(inner_data_str)
        except (IndexError, TypeError, json.JSONDecodeError):
            pass
        return []
