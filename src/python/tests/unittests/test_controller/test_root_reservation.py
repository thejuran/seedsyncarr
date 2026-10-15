import threading
import unittest

from controller.root_reservation import RootReservations


class TestRootReservations(unittest.TestCase):
    """Contract tests for the per-root operation reservation registry."""

    def setUp(self):
        self.reservations = RootReservations()

    def test_acquire_returns_context_manager_and_exit_releases(self):
        with self.reservations.acquire("r", "auto-delete") as token:
            self.assertIsNotNone(token)
            self.assertEqual("r", token.name)
            self.assertEqual("auto-delete", token.holder)
            self.assertEqual("auto-delete", self.reservations.holder_of("r"))
        self.assertIsNone(self.reservations.holder_of("r"))

    def test_conflicting_holder_gets_none(self):
        held = self.reservations.acquire("r", "auto-delete")
        try:
            self.assertIsNotNone(held)
            self.assertIsNone(self.reservations.acquire("r", "queue"))
            self.assertEqual("auto-delete", self.reservations.holder_of("r"))
        finally:
            held.release()

    def test_different_roots_do_not_conflict(self):
        a = self.reservations.acquire("a", "queue")
        b = self.reservations.acquire("b", "delete")
        try:
            self.assertIsNotNone(a)
            self.assertIsNotNone(b)
            self.assertEqual("queue", self.reservations.holder_of("a"))
            self.assertEqual("delete", self.reservations.holder_of("b"))
        finally:
            a.release()
            b.release()

    def test_reacquire_after_release(self):
        first = self.reservations.acquire("r", "queue")
        first.release()
        second = self.reservations.acquire("r", "delete")
        try:
            self.assertIsNotNone(second)
            self.assertEqual("delete", self.reservations.holder_of("r"))
        finally:
            second.release()

    def test_release_is_idempotent_and_owner_checked(self):
        a = self.reservations.acquire("r", "delete")
        a.release()
        a.release()
        self.assertIsNone(self.reservations.holder_of("r"))

        b = self.reservations.acquire("r", "queue")
        try:
            self.assertIsNotNone(b)
            # A stale token can never evict a newer holder
            a.release()
            self.assertEqual("queue", self.reservations.holder_of("r"))
        finally:
            b.release()
        self.assertIsNone(self.reservations.holder_of("r"))

    def test_holder_of_unknown_name_is_none(self):
        self.assertIsNone(self.reservations.holder_of("never-acquired"))

    def test_two_threads_contend_exactly_one_wins(self):
        for _ in range(50):
            barrier = threading.Barrier(2)
            results = []
            results_lock = threading.Lock()

            def _contend(holder):
                barrier.wait(timeout=5)
                token = self.reservations.acquire("r", holder)
                with results_lock:
                    results.append(token)

            threads = [threading.Thread(target=_contend, args=(h,), daemon=True)
                       for h in ("queue", "auto-delete")]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)
                self.assertFalse(t.is_alive())

            winners = [r for r in results if r is not None]
            self.assertEqual(2, len(results))
            self.assertEqual(1, len(winners))
            winners[0].release()
            self.assertIsNone(self.reservations.holder_of("r"))
