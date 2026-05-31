import unittest

from common import overrides
from common import sanitize_log_value


class _Base:
    def existing_method(self):
        pass


class _GrandParent:
    def inherited_method(self):
        pass


class _Parent(_GrandParent):
    pass


class TestOverrides(unittest.TestCase):

    def test_valid_override_succeeds(self):
        # Should not raise any exception
        @overrides(_Base)
        def existing_method(self):
            return "overridden"
        self.assertTrue(callable(existing_method))

    def test_decorated_method_still_callable(self):
        class _Child(_Base):
            @overrides(_Base)
            def existing_method(self):
                return "result"
        instance = _Child()
        self.assertEqual("result", instance.existing_method())

    def test_works_with_unittest_testcase(self):
        # Should not raise any exception
        @overrides(unittest.TestCase)
        def setUp(self):
            pass
        self.assertTrue(callable(setUp))

    def test_works_with_inherited_method(self):
        # inherited_method exists on _Parent via _GrandParent
        @overrides(_Parent)
        def inherited_method(self):
            pass
        self.assertTrue(callable(inherited_method))

    def test_non_class_raises_assertion_error(self):
        with self.assertRaises(AssertionError) as cm:
            @overrides("not_a_class")
            def some_method(self):
                pass
        self.assertIn("Overrides parameter must be a class type", str(cm.exception))

    def test_non_existent_method_raises_assertion_error(self):
        with self.assertRaises(AssertionError) as cm:
            @overrides(_Base)
            def nonexistent_method(self):
                pass
        self.assertIn("Method does not override super class", str(cm.exception))

    def test_integer_raises_assertion_error(self):
        with self.assertRaises(AssertionError):
            @overrides(42)
            def method(self):
                pass

    def test_function_raises_assertion_error(self):
        def some_func():
            pass
        with self.assertRaises(AssertionError):
            @overrides(some_func)
            def method(self):
                pass


class TestSanitizeLogValue(unittest.TestCase):
    """Unit tests for sanitize_log_value (CWE-117 log injection guard)."""

    def test_plain_string_unchanged(self):
        self.assertEqual("hello world", sanitize_log_value("hello world"))

    def test_printable_unicode_unchanged(self):
        self.assertEqual("naïve – Mövie 2024", sanitize_log_value("naïve – Mövie 2024"))

    def test_newline_escaped(self):
        self.assertEqual("line1\\nline2", sanitize_log_value("line1\nline2"))

    def test_carriage_return_escaped(self):
        self.assertEqual("line1\\rline2", sanitize_log_value("line1\rline2"))

    def test_crlf_both_escaped(self):
        self.assertEqual("line1\\r\\nline2", sanitize_log_value("line1\r\nline2"))

    def test_empty_string(self):
        self.assertEqual("", sanitize_log_value(""))

    def test_multiple_newlines(self):
        self.assertEqual("a\\nb\\nc", sanitize_log_value("a\nb\nc"))

    def test_escape_char_neutralized(self):
        result = sanitize_log_value("ansi\x1b[31mRED")
        self.assertNotIn("\x1b", result)
        self.assertIn("\\x1b", result)

    def test_nul_and_c0_control_neutralized(self):
        result = sanitize_log_value("a\x00b\x07c")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x07", result)
        self.assertIn("\\x00", result)
        self.assertIn("\\x07", result)

    def test_tab_neutralized(self):
        result = sanitize_log_value("a\tb")
        self.assertNotIn("\t", result)
        self.assertIn("\\x09", result)

    def test_del_neutralized(self):
        result = sanitize_log_value("a\x7fb")
        self.assertNotIn("\x7f", result)
        self.assertIn("\\x7f", result)
