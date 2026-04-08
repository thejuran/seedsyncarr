# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest

from common import overrides


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
