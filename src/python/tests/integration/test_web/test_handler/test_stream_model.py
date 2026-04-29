from unittest.mock import patch, ANY
from threading import Timer

from tests.integration.test_web.test_web_app import BaseTestWebApp
from tests.helpers.wsgi_stream import collect_sse_chunks
from web.serialize import SerializeModel
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
        mock_serialize.update_event.return_value = "\n"
        # Use the real UpdateEvent class so the handler can construct events
        mock_serialize_model_cls.UpdateEvent = SerializeModel.UpdateEvent

        # Initial model -- handler sends each file as an ADDED update_event
        self.model_files = [ModelFile("a", True), ModelFile("b", False)]

        collect_sse_chunks(self.web_app)
        self.assertEqual(2, len(mock_serialize.update_event.call_args_list))
        call1, call2 = mock_serialize.update_event.call_args_list
        self.assertEqual(SerializeModel.UpdateEvent.Change.ADDED, call1[0][0].change)
        self.assertEqual(None, call1[0][0].old_file)
        self.assertEqual(ModelFile("a", True), call1[0][0].new_file)
        self.assertEqual(SerializeModel.UpdateEvent.Change.ADDED, call2[0][0].change)
        self.assertEqual(None, call2[0][0].old_file)
        self.assertEqual(ModelFile("b", False), call2[0][0].new_file)

    @patch("web.handler.stream_model.SerializeModel")
    def test_stream_model_serializes_updates(self, mock_serialize_model_cls):
        # Setup mock serialize instance
        mock_serialize = mock_serialize_model_cls.return_value
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
