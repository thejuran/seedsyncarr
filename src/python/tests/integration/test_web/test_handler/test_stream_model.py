from unittest.mock import patch, ANY
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.helpers.wsgi_stream import collect_sse_chunks, open_sse_stream
from tests.helpers.model_stream_client import ModelStreamClient, parse_sse_events, server_snapshot
from web.serialize import SerializeModel
from web.web_app import WebApp
from model import ModelFile


class TestModelStreamHandler(BaseTestWebApp):
    def test_stream_model_fetches_model_and_adds_listener(self):
        collect_sse_chunks(self.web_app)
        self.controller.get_model_files_and_add_listener.assert_called_once_with(ANY)

    def test_stream_model_removes_listener(self):
        collect_sse_chunks(self.web_app)
        self.controller.remove_model_listener.assert_called_once_with(self.model_listener)

    @patch("web.handler.stream_model.SerializeModel")
    def test_stream_model_serializes_initial_model(self, mock_serialize_model_cls):
        # Setup mock serialize instance
        mock_serialize = mock_serialize_model_cls.return_value
        mock_serialize.model.return_value = "\n"
        mock_serialize.update_event.return_value = "\n"
        # Use the real UpdateEvent class so the handler can construct events
        mock_serialize_model_cls.UpdateEvent = SerializeModel.UpdateEvent

        # Initial model -- handler sends all files in a single model-init event
        self.model_files = [ModelFile("a", True), ModelFile("b", False)]

        collect_sse_chunks(self.web_app)
        self.assertEqual(1, len(mock_serialize.model.call_args_list))
        self.assertEqual(
            [ModelFile("a", True), ModelFile("b", False)],
            mock_serialize.model.call_args[0][0]
        )
        # No per-file added events for the initial model
        self.assertEqual(0, len(mock_serialize.update_event.call_args_list))

    @patch("web.handler.stream_model.SerializeModel")
    def test_stream_model_serializes_updates(self, mock_serialize_model_cls):
        # Setup mock serialize instance
        mock_serialize = mock_serialize_model_cls.return_value
        mock_serialize.model.return_value = "\n"
        mock_serialize.update_event.return_value = "\n"
        # Use the real UpdateEvent class
        mock_serialize_model_cls.UpdateEvent = SerializeModel.UpdateEvent

        # Queue updates
        added_file = ModelFile("a", True)
        removed_file = ModelFile("b", False)
        old_file = ModelFile("c", False)
        old_file.local_size = 100
        new_file = ModelFile("c", False)
        new_file.local_size = 200

        def send_updates():
            # model_listener is set during WSGI dispatch in collect_sse_chunks,
            # which completes before the Timer fires at 0.5s
            assert self.model_listener is not None, "listener not set before Timer fired"
            self.model_listener.file_added(added_file)
            self.model_listener.file_removed(removed_file)
            self.model_listener.file_updated(old_file, new_file)
        Timer(0.5, send_updates).start()

        # Stop at 2.0s to allow the 0.5s updates to arrive
        collect_sse_chunks(self.web_app, stop_after_s=2.0)
        self.assertEqual(3, len(mock_serialize.update_event.call_args_list))
        call1, call2, call3 = mock_serialize.update_event.call_args_list
        self.assertEqual(SerializeModel.UpdateEvent.Change.ADDED, call1[0][0].change)
        self.assertEqual(None, call1[0][0].old_file)
        self.assertEqual(added_file, call1[0][0].new_file)
        self.assertEqual(SerializeModel.UpdateEvent.Change.REMOVED, call2[0][0].change)
        self.assertEqual(removed_file, call2[0][0].old_file)
        self.assertEqual(None, call2[0][0].new_file)
        self.assertEqual(SerializeModel.UpdateEvent.Change.UPDATED, call3[0][0].change)
        self.assertEqual(old_file, call3[0][0].old_file)
        self.assertEqual(new_file, call3[0][0].new_file)

    @patch.object(WebApp, "_STREAM_YIELD_INTERVAL_IN_MS", 0)
    @patch.object(WebApp, "_STREAM_POLL_INTERVAL_IN_MS", 5)
    def test_stalled_consumer_converges_after_overflow(self):
        # STRM-02 (D-07b): proves convergence through the real WSGI
        # generator and real SSE serialization (no SerializeModel patch).
        self.model_files = [ModelFile("ghost.txt", False)]
        server = {"ghost.txt": ModelFile("ghost.txt", False)}
        self.controller.resync_model_files.side_effect = \
            lambda discard: (discard(), list(server.values()))[1]

        client = ModelStreamClient()
        response_started, body = open_sse_stream(self.web_app)
        it = iter(body)
        timer = None
        try:
            for _ in range(50):
                chunk = next(it)
                events = parse_sse_events([chunk])
                client.apply_all(events)
                if any(name == "model-init" for name, _ in events):
                    break
            else:
                self.fail("model-init not observed within 50 chunks")

            self.assertIsNotNone(self.model_listener)

            # Stall: 1501 model events land on the listener's queue (1
            # remove + 1500 adds) without ever calling next(it) -- the
            # queue drops 501 of them (production order).
            self.model_listener.file_removed(server.pop("ghost.txt"))
            for i in range(1500):
                new_file = ModelFile("file-%04d" % i, False)
                server[new_file.name] = new_file
                self.model_listener.file_added(new_file)

            self.assertEqual(501, self.model_listener.get_dropped_count())

            # Resume: drain the rest through the real generator/socket path.
            timer = Timer(1.5, self.web_app.stop)
            timer.start()
            rest = list(it)
            client.apply_all(parse_sse_events(rest))

            self.assertEqual(server_snapshot(list(server.values())), client.files)
        finally:
            if timer is not None:
                timer.cancel()
            self.web_app.stop()
            if hasattr(body, "close"):
                body.close()
