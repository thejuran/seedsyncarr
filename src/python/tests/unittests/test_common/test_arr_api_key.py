import unittest

from common import ARR_API_KEY_CHARS
from common import normalize_arr_api_key
from common import is_valid_arr_api_key


# (raw, expected_normalized, expected_valid_after_normalize)
# Shared by the cross-path parity test so Save, Test Connection and the queue
# client are all checked against the same rule table.
RULE_CASES = [
    (None, "", False),
    (123, "", False),
    ("", "", False),
    ("   ", "", False),
    ("\t\r\n", "", False),
    ("abcDEF123", "abcDEF123", True),
    ("  abcDEF123\n", "abcDEF123", True),
    ("\tabcDEF123  ", "abcDEF123", True),
    ("\u00a0abcDEF123\u00a0", "abcDEF123", True),
    ("abc def", "abc def", False),
    ("abc\tdef", "abc\tdef", False),
    ("abc\ndef", "abc\ndef", False),
    ("abc\r\ndef", "abc\r\ndef", False),
    ("a\x00b", "a\x00b", False),
    ("clé", "clé", False),
    ("abc\u00a0def", "abc\u00a0def", False),
    ("!~", "!~", True),
    ("a\x7fb", "a\x7fb", False),
]


class TestArrApiKeyRule(unittest.TestCase):
    def test_normalize_table(self):
        for raw, expected_normalized, _ in RULE_CASES:
            with self.subTest(raw=repr(raw)):
                self.assertEqual(expected_normalized, normalize_arr_api_key(raw))

    def test_valid_after_normalize_table(self):
        for raw, _, expected_valid in RULE_CASES:
            with self.subTest(raw=repr(raw)):
                self.assertIs(expected_valid, is_valid_arr_api_key(normalize_arr_api_key(raw)))

    def test_is_valid_does_not_raise_on_non_str(self):
        self.assertFalse(is_valid_arr_api_key(None))
        self.assertFalse(is_valid_arr_api_key(123))

    def test_is_valid_does_not_trim(self):
        self.assertFalse(is_valid_arr_api_key("  abcDEF123"))

    def test_pattern_is_printable_ascii_without_space(self):
        self.assertEqual(r"[\x21-\x7e]+", ARR_API_KEY_CHARS.pattern)

    def test_rule_table_pins_nbsp_rows(self):
        nbsp = chr(0xA0)
        rows = [row for row in RULE_CASES if isinstance(row[0], str) and nbsp in row[0]]
        self.assertEqual(2, len(rows))
        padded = [row for row in rows if row[1] == "abcDEF123" and row[2] is True]
        inner = [row for row in rows if row[2] is False]
        self.assertEqual(1, len(padded))
        self.assertEqual(1, len(inner))
