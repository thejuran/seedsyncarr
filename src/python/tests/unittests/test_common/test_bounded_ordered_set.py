# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest

from common import BoundedOrderedSet


class TestBoundedOrderedSet(unittest.TestCase):
    """Tests for BoundedOrderedSet class."""

    def test_basic_add_and_contains(self):
        """Test basic add and membership testing."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')
        bset.add('c')

        self.assertIn('a', bset)
        self.assertIn('b', bset)
        self.assertIn('c', bset)
        self.assertNotIn('d', bset)

    def test_len(self):
        """Test length calculation."""
        bset = BoundedOrderedSet(maxlen=10)
        self.assertEqual(0, len(bset))

        bset.add('a')
        self.assertEqual(1, len(bset))

        bset.add('b')
        self.assertEqual(2, len(bset))

        bset.add('a')  # Duplicate
        self.assertEqual(2, len(bset))

    def test_discard(self):
        """Test discard removes items."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')

        bset.discard('a')
        self.assertNotIn('a', bset)
        self.assertIn('b', bset)
        self.assertEqual(1, len(bset))

        # Discard non-existent item should not raise
        bset.discard('nonexistent')

    def test_remove(self):
        """Test remove raises KeyError for non-existent items."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')

        bset.remove('a')
        self.assertNotIn('a', bset)

        with self.assertRaises(KeyError):
            bset.remove('nonexistent')

    def test_clear(self):
        """Test clear removes all items."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')
        bset.add('c')

        bset.clear()
        self.assertEqual(0, len(bset))
        self.assertNotIn('a', bset)

    def test_eviction_when_full(self):
        """Test that oldest item is evicted when maxlen is reached."""
        bset = BoundedOrderedSet(maxlen=3)
        bset.add('a')  # ['a']
        bset.add('b')  # ['a', 'b']
        bset.add('c')  # ['a', 'b', 'c']

        evicted = bset.add('d')  # ['b', 'c', 'd'], 'a' evicted

        self.assertEqual('a', evicted)
        self.assertNotIn('a', bset)
        self.assertIn('b', bset)
        self.assertIn('c', bset)
        self.assertIn('d', bset)
        self.assertEqual(3, len(bset))

    def test_eviction_count(self):
        """Test that eviction count is tracked correctly."""
        bset = BoundedOrderedSet(maxlen=2)
        self.assertEqual(0, bset.total_evictions)

        bset.add('a')
        bset.add('b')
        self.assertEqual(0, bset.total_evictions)

        bset.add('c')  # 'a' evicted
        self.assertEqual(1, bset.total_evictions)

        bset.add('d')  # 'b' evicted
        self.assertEqual(2, bset.total_evictions)

    def test_no_eviction_for_duplicate(self):
        """Test that adding duplicate does not cause eviction."""
        bset = BoundedOrderedSet(maxlen=2)
        bset.add('a')
        bset.add('b')

        evicted = bset.add('a')  # Duplicate

        self.assertIsNone(evicted)
        self.assertEqual(0, bset.total_evictions)
        self.assertEqual(2, len(bset))

    def test_iteration_order(self):
        """Test that iteration follows insertion order."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('c')
        bset.add('a')
        bset.add('b')

        items = list(bset)
        self.assertEqual(['c', 'a', 'b'], items)

    def test_iteration_order_after_eviction(self):
        """Test iteration order is correct after evictions."""
        bset = BoundedOrderedSet(maxlen=3)
        bset.add('a')
        bset.add('b')
        bset.add('c')
        bset.add('d')  # 'a' evicted

        items = list(bset)
        self.assertEqual(['b', 'c', 'd'], items)

    def test_difference_update(self):
        """Test difference_update removes specified items."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')
        bset.add('c')
        bset.add('d')

        bset.difference_update({'b', 'd', 'nonexistent'})

        self.assertEqual({'a', 'c'}, bset.as_set())

    def test_equality_with_set(self):
        """Test equality comparison with regular set."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')

        self.assertEqual({'a', 'b'}, bset)
        self.assertEqual(bset, {'a', 'b'})

    def test_equality_with_bounded_ordered_set(self):
        """Test equality comparison with another BoundedOrderedSet."""
        bset1 = BoundedOrderedSet(maxlen=10)
        bset1.add('a')
        bset1.add('b')

        bset2 = BoundedOrderedSet(maxlen=5)  # Different maxlen
        bset2.add('b')  # Different order
        bset2.add('a')

        # Content equality regardless of maxlen or order
        self.assertEqual(bset1, bset2)

    def test_as_list(self):
        """Test as_list returns items in insertion order."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('c')
        bset.add('a')
        bset.add('b')

        self.assertEqual(['c', 'a', 'b'], bset.as_list())

    def test_as_set(self):
        """Test as_set returns regular set."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        bset.add('b')

        result = bset.as_set()
        self.assertIsInstance(result, set)
        self.assertEqual({'a', 'b'}, result)

    def test_copy(self):
        """Test copy creates independent copy."""
        bset1 = BoundedOrderedSet(maxlen=5)
        bset1.add('a')
        bset1.add('b')

        bset2 = bset1.copy()

        # Same content
        self.assertEqual(bset1, bset2)
        self.assertEqual(bset1.maxlen, bset2.maxlen)

        # Eviction count is reset
        self.assertEqual(0, bset2.total_evictions)

        # Independent
        bset2.add('c')
        self.assertNotIn('c', bset1)

    def test_from_iterable(self):
        """Test from_iterable class method."""
        bset = BoundedOrderedSet.from_iterable(['a', 'b', 'c'], maxlen=10)

        self.assertEqual(['a', 'b', 'c'], bset.as_list())

    def test_from_iterable_with_eviction(self):
        """Test from_iterable evicts when iterable exceeds maxlen."""
        bset = BoundedOrderedSet.from_iterable(['a', 'b', 'c', 'd', 'e'], maxlen=3)

        # Only last 3 items should be kept
        self.assertEqual(['c', 'd', 'e'], bset.as_list())
        self.assertEqual(2, bset.total_evictions)

    def test_bool_false_when_empty(self):
        """Test bool returns False for empty set."""
        bset = BoundedOrderedSet(maxlen=10)
        self.assertFalse(bset)

    def test_bool_true_when_not_empty(self):
        """Test bool returns True for non-empty set."""
        bset = BoundedOrderedSet(maxlen=10)
        bset.add('a')
        self.assertTrue(bset)

    def test_default_maxlen(self):
        """Test default maxlen is used when not specified."""
        bset = BoundedOrderedSet()
        self.assertEqual(BoundedOrderedSet.DEFAULT_MAXLEN, bset.maxlen)

    def test_maxlen_must_be_positive(self):
        """Test that maxlen must be positive."""
        with self.assertRaises(ValueError):
            BoundedOrderedSet(maxlen=0)

        with self.assertRaises(ValueError):
            BoundedOrderedSet(maxlen=-1)

    def test_repr(self):
        """Test string representation."""
        bset = BoundedOrderedSet(maxlen=3)
        bset.add('a')
        bset.add('b')

        repr_str = repr(bset)
        self.assertIn("BoundedOrderedSet", repr_str)
        self.assertIn("maxlen=3", repr_str)

    def test_maxlen_one(self):
        """Test BoundedOrderedSet with maxlen=1."""
        bset = BoundedOrderedSet(maxlen=1)
        bset.add('a')
        self.assertIn('a', bset)

        bset.add('b')
        self.assertNotIn('a', bset)
        self.assertIn('b', bset)
        self.assertEqual(1, bset.total_evictions)


class TestBoundedOrderedSetIntegration(unittest.TestCase):
    """Integration tests for BoundedOrderedSet with realistic scenarios."""

    def test_file_tracking_scenario(self):
        """Test a realistic file tracking scenario."""
        # Simulate tracking downloaded files with a small limit
        tracker = BoundedOrderedSet(maxlen=5)

        # Download some files
        for i in range(1, 6):
            tracker.add(f"file{i}.txt")

        self.assertEqual(5, len(tracker))
        self.assertEqual(0, tracker.total_evictions)

        # Download more files - oldest should be evicted
        tracker.add("file6.txt")
        tracker.add("file7.txt")

        self.assertEqual(5, len(tracker))
        self.assertEqual(2, tracker.total_evictions)
        self.assertNotIn("file1.txt", tracker)
        self.assertNotIn("file2.txt", tracker)
        self.assertIn("file7.txt", tracker)

        # Delete some files
        tracker.difference_update({"file4.txt", "file5.txt"})
        self.assertEqual(3, len(tracker))

        # Serialization round-trip
        items_list = tracker.as_list()
        restored = BoundedOrderedSet.from_iterable(items_list, maxlen=5)
        self.assertEqual(tracker, restored)


if __name__ == "__main__":
    unittest.main()
