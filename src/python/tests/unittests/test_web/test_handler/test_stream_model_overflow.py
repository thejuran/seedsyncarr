"""Phase 124 STRM-01 reproduction and STRM-02 convergence for the model SSE stream."""
import unittest
from unittest.mock import MagicMock

from model import ModelFile
from tests.helpers.model_stream_client import ModelStreamClient, parse_sse_events, server_snapshot
from tests.unittests.test_controller.base import BaseControllerTestCase
from web.handler.stream_model import ModelStreamHandler, WebResponseModelListener
from web.handler.stream_status import StatusListener
from web.serialize import SerializeModel


def _flood(controller, n_adds=1500):
    """
    Mutate the model directly under __model_lock, exactly as production
    model mutations do (e.g. scan results, webhook imports), to simulate
    1 + n_adds events landing on a registered listener's queue without the
    listener (a stalled consumer) ever draining it.
    """
    with controller._Controller__model_lock:
        controller._Controller__model.remove_file("ghost.txt")
        for i in range(n_adds):
            controller._Controller__model.add_file(ModelFile("file-%04d" % i, False))


class TestModelStreamOverflowReproduction(BaseControllerTestCase):
    """STRM-01: reproduce the model-stream overflow at the real boundary (a
    real Controller with a real Model and real __model_lock, a registered
    WebResponseModelListener that is never drained) and record the observed
    divergence between the reconstructed client model and the server model."""

    def test_stalled_listener_overflow_diverges_from_server_model(self):
        self._add_file_to_model("ghost.txt")

        listener = WebResponseModelListener()
        try:
            initial = self.controller.get_model_files_and_add_listener(listener)
            client = ModelStreamClient()
            client.apply_all(parse_sse_events([SerializeModel().model(initial)]))

            # Stalled consumer: 1501 model events produced (1 remove + 1500
            # adds), none drained, while maxsize is 1000.
            _flood(self.controller)

            self.assertEqual(501, listener.get_dropped_count())
            self.assertEqual(1000, listener.get_queue_size())
            self.assertLessEqual(listener.get_queue_size(), listener.get_maxsize())

            # Drain everything the stalled listener actually kept.
            event = listener.get_next_event()
            while event is not None:
                client.apply_all(parse_sse_events([SerializeModel().update_event(event)]))
                event = listener.get_next_event()

            server = server_snapshot(self.controller.get_model_files())

            # Divergence: the client never saw the dropped remove-ghost.txt
            # event, nor the dropped add events for file-0000..file-0499.
            self.assertNotEqual(client.files, server)
            self.assertIn("ghost.txt", client.files)
            self.assertNotIn("ghost.txt", server)
            self.assertEqual(
                ["file-%04d" % i for i in range(500)],
                sorted(set(server) - set(client.files)),
            )
        finally:
            self.controller.remove_model_listener(listener)


class TestModelStreamConvergence(BaseControllerTestCase):
    """STRM-02 (D-07b): real Controller, real __model_lock, real
    ModelStreamHandler -- the actual class a browser tab talks to -- proving
    the wire-reconstructed client model converges to the server's current
    model after a stalled consumer overflows the model stream."""

    def setUp(self):
        super().setUp()
        self._add_file_to_model("ghost.txt")
        self.handler = ModelStreamHandler(self.controller)
        self.handler.setup()

    def tearDown(self):
        self.handler.cleanup()
        super().tearDown()

    def _drain(self, client):
        """Pull get_value() until None, applying each value to client via the
        same wire-format reducer a real browser tab uses. Returns the ordered
        list of event names observed."""
        names = []
        while True:
            value = self.handler.get_value()
            if value is None:
                break
            events = parse_sse_events([value])
            client.apply_all(events)
            names.extend(name for name, _ in events)
        return names

    def test_stalled_tab_converges_to_server_model_after_overflow(self):
        client = ModelStreamClient()
        client.apply_all(parse_sse_events([self.handler.get_value()]))  # initial model-init

        _flood(self.controller)

        # D-05: the queue stays bounded during the stall.
        self.assertLessEqual(
            self.handler.model_listener.get_queue_size(),
            self.handler.model_listener.get_maxsize(),
        )

        self._drain(client)

        self.assertEqual(server_snapshot(self.controller.get_model_files()), client.files)

    def test_first_value_after_overflow_is_model_init(self):
        self.handler.get_value()  # consume initial model-init
        _flood(self.controller)

        value = self.handler.get_value()
        names = [name for name, _ in parse_sse_events([value])]
        self.assertIn("model-init", names)

    def test_no_stale_or_duplicate_events_after_resync(self):
        client = ModelStreamClient()
        client.apply_all(parse_sse_events([self.handler.get_value()]))  # initial model-init

        _flood(self.controller)
        self._drain(client)

        self.assertIsNone(self.handler.get_value())
        self.assertEqual(0, self.handler.model_listener.get_queue_size())

        with self.controller._Controller__model_lock:
            self.controller._Controller__model.add_file(ModelFile("after.txt", False))
            updated = ModelFile("file-0000", False)
            updated.local_size = 7
            self.controller._Controller__model.update_file(updated)

        names = self._drain(client)

        self.assertEqual(["model-added", "model-updated"], names)
        self.assertEqual(server_snapshot(self.controller.get_model_files()), client.files)
        self.assertEqual(0, client.ignored_added)

    def test_overflow_before_initial_init_still_converges(self):
        client = ModelStreamClient()

        _flood(self.controller)

        names = self._drain(client)

        self.assertEqual("model-init", names[0])
        self.assertEqual(2, names.count("model-init"))
        self.assertEqual(server_snapshot(self.controller.get_model_files()), client.files)


class TestStatusStreamSelfHealingEvidence(unittest.TestCase):
    """D-06: the status stream is self-healing under overflow because every
    queued event is already a full Status snapshot, so the next successfully
    delivered snapshot is always fully current even after drops. No
    status-stream production code is changed by this phase."""

    def test_overflowed_status_listener_still_delivers_latest_snapshot(self):
        mock_status = MagicMock()
        snapshots = [MagicMock(name="status-%d" % i) for i in range(1200)]
        mock_status.copy.side_effect = snapshots
        listener = StatusListener(mock_status)

        for _ in range(1200):
            listener.notify()

        self.assertEqual(200, listener.get_dropped_count())

        drained = []
        event = listener.get_next_event()
        while event is not None:
            drained.append(event)
            event = listener.get_next_event()

        self.assertEqual(1000, len(drained))
        self.assertIs(snapshots[-1], drained[-1])
