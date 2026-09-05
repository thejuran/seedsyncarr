import unittest
from unittest.mock import MagicMock, ANY
import logging
import sys
import json

from common import overrides, PersistError, Config
from controller import AutoQueue, AutoQueuePersist, IAutoQueuePersistListener, AutoQueuePattern
from controller import Controller
from model import IModelListener, ModelFile


class TestAutoQueuePattern(unittest.TestCase):
    def test_pattern(self):
        aqp = AutoQueuePattern(pattern="file.one")
        self.assertEqual(aqp.pattern, "file.one")
        aqp = AutoQueuePattern(pattern="file.two")
        self.assertEqual(aqp.pattern, "file.two")

    def test_equality(self):
        aqp_1 = AutoQueuePattern(pattern="file.one")
        aqp_2 = AutoQueuePattern(pattern="file.two")
        aqp_1b = AutoQueuePattern(pattern="file.one")
        self.assertEqual(aqp_1, aqp_1b)
        self.assertNotEqual(aqp_1, aqp_2)

    def test_to_str(self):
        self.assertEqual(
            "{\"pattern\": \"file.one\"}",
            AutoQueuePattern(pattern="file.one").to_str()
        )
        self.assertEqual(
            "{\"pattern\": \"file'one\"}",
            AutoQueuePattern(pattern="file'one").to_str()
        )
        self.assertEqual(
            "{\"pattern\": \"file\\\"one\"}",
            AutoQueuePattern(pattern="file\"one").to_str()
        )
        self.assertEqual(
            "{\"pattern\": \"fil(eo)ne\"}",
            AutoQueuePattern(pattern="fil(eo)ne").to_str()
        )

    def test_from_str(self):
        self.assertEqual(
            AutoQueuePattern(pattern="file.one"),
            AutoQueuePattern.from_str("{\"pattern\": \"file.one\"}"),
        )
        self.assertEqual(
            AutoQueuePattern(pattern="file'one"),
            AutoQueuePattern.from_str("{\"pattern\": \"file'one\"}"),
        )
        self.assertEqual(
            AutoQueuePattern(pattern="file\"one"),
            AutoQueuePattern.from_str("{\"pattern\": \"file\\\"one\"}"),
        )
        self.assertEqual(
            AutoQueuePattern(pattern="fil(eo)ne"),
            AutoQueuePattern.from_str("{\"pattern\": \"fil(eo)ne\"}"),
        )

    def test_to_and_from_str(self):
        self.assertEqual(
            AutoQueuePattern(pattern="file.one"),
            AutoQueuePattern.from_str(AutoQueuePattern(pattern="file.one").to_str())
        )
        self.assertEqual(
            AutoQueuePattern(pattern="file'one"),
            AutoQueuePattern.from_str(AutoQueuePattern(pattern="file'one").to_str())
        )
        self.assertEqual(
            AutoQueuePattern(pattern="file\"one"),
            AutoQueuePattern.from_str(AutoQueuePattern(pattern="file\"one").to_str())
        )
        self.assertEqual(
            AutoQueuePattern(pattern="fil(eo)ne"),
            AutoQueuePattern.from_str(AutoQueuePattern(pattern="fil(eo)ne").to_str())
        )


class TestAutoQueuePersistListener(IAutoQueuePersistListener):
    @overrides(IAutoQueuePersistListener)
    def pattern_added(self, pattern: AutoQueuePattern):
        pass

    @overrides(IAutoQueuePersistListener)
    def pattern_removed(self, pattern: AutoQueuePattern):
        pass


class TestAutoQueuePersist(unittest.TestCase):
    def test_add_pattern(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        self.assertEqual({
            AutoQueuePattern(pattern="one"),
            AutoQueuePattern(pattern="two")
        }, persist.patterns)
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="three"))
        self.assertEqual({
            AutoQueuePattern(pattern="one"),
            AutoQueuePattern(pattern="two"),
            AutoQueuePattern(pattern="three")
        }, persist.patterns)

    def test_add_blank_pattern_fails(self):
        persist = AutoQueuePersist()
        with self.assertRaises(ValueError):
            persist.add_pattern(AutoQueuePattern(pattern=""))
        with self.assertRaises(ValueError):
            persist.add_pattern(AutoQueuePattern(pattern=" "))
        with self.assertRaises(ValueError):
            persist.add_pattern(AutoQueuePattern(pattern="   "))

    def test_remove_pattern(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        persist.remove_pattern(AutoQueuePattern(pattern="one"))
        self.assertEqual({AutoQueuePattern(pattern="two")}, persist.patterns)
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="three"))
        persist.remove_pattern(AutoQueuePattern(pattern="two"))
        self.assertEqual({
            AutoQueuePattern(pattern="one"),
            AutoQueuePattern(pattern="three")
        }, persist.patterns)

    def test_listener_pattern_added(self):
        listener = TestAutoQueuePersistListener()
        listener.pattern_added = MagicMock()
        persist = AutoQueuePersist()
        persist.add_listener(listener)
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        listener.pattern_added.assert_called_once_with(AutoQueuePattern(pattern="one"))
        listener.pattern_added.reset_mock()
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        listener.pattern_added.assert_called_once_with(AutoQueuePattern(pattern="two"))
        listener.pattern_added.reset_mock()

    def test_listener_pattern_added_duplicate(self):
        listener = TestAutoQueuePersistListener()
        listener.pattern_added = MagicMock()
        persist = AutoQueuePersist()
        persist.add_listener(listener)
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        listener.pattern_added.assert_called_once_with(AutoQueuePattern(pattern="one"))
        listener.pattern_added.reset_mock()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        listener.pattern_added.assert_not_called()

    def test_listener_pattern_removed(self):
        listener = TestAutoQueuePersistListener()
        listener.pattern_removed = MagicMock()
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        persist.add_pattern(AutoQueuePattern(pattern="three"))
        persist.add_listener(listener)
        persist.remove_pattern(AutoQueuePattern(pattern="one"))
        listener.pattern_removed.assert_called_once_with(AutoQueuePattern(pattern="one"))
        listener.pattern_removed.reset_mock()
        persist.remove_pattern(AutoQueuePattern(pattern="two"))
        listener.pattern_removed.assert_called_once_with(AutoQueuePattern(pattern="two"))
        listener.pattern_removed.reset_mock()

    def test_listener_pattern_removed_non_existing(self):
        listener = TestAutoQueuePersistListener()
        listener.pattern_removed = MagicMock()
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        persist.add_pattern(AutoQueuePattern(pattern="three"))
        persist.add_listener(listener)
        persist.remove_pattern(AutoQueuePattern(pattern="four"))
        listener.pattern_removed.assert_not_called()

    def test_from_str(self):
        content = """
        {{
            "patterns": [
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
                "{}"
            ]
        }}
        """.format(
            AutoQueuePattern(pattern="one").to_str().replace("\\", "\\\\").replace("\"", "\\\""),
            AutoQueuePattern(pattern="two").to_str().replace("\\", "\\\\").replace("\"", "\\\""),
            AutoQueuePattern(pattern="th ree").to_str().replace("\\", "\\\\").replace("\"", "\\\""),
            AutoQueuePattern(pattern="fo.ur").to_str().replace("\\", "\\\\").replace("\"", "\\\""),
            AutoQueuePattern(pattern="fi\"ve").to_str().replace("\\", "\\\\").replace("\"", "\\\""),
            AutoQueuePattern(pattern="si'x").to_str().replace("\\", "\\\\").replace("\"", "\\\"")
        )
        print(content)
        print(AutoQueuePattern(pattern="fi\"ve").to_str())
        persist = AutoQueuePersist.from_str(content)
        golden_patterns = {
            AutoQueuePattern(pattern="one"),
            AutoQueuePattern(pattern="two"),
            AutoQueuePattern(pattern="th ree"),
            AutoQueuePattern(pattern="fo.ur"),
            AutoQueuePattern(pattern="fi\"ve"),
            AutoQueuePattern(pattern="si'x")
        }
        self.assertEqual(golden_patterns, persist.patterns)

    def test_to_str(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        persist.add_pattern(AutoQueuePattern(pattern="th ree"))
        persist.add_pattern(AutoQueuePattern(pattern="fo.ur"))
        persist.add_pattern(AutoQueuePattern(pattern="fi\"ve"))
        persist.add_pattern(AutoQueuePattern(pattern="si'x"))
        print(persist.to_str())
        dct = json.loads(persist.to_str())
        self.assertTrue("patterns" in dct)
        self.assertEqual(
            [
                AutoQueuePattern(pattern="one").to_str(),
                AutoQueuePattern(pattern="two").to_str(),
                AutoQueuePattern(pattern="th ree").to_str(),
                AutoQueuePattern(pattern="fo.ur").to_str(),
                AutoQueuePattern(pattern="fi\"ve").to_str(),
                AutoQueuePattern(pattern="si'x").to_str()
            ],
            dct["patterns"]
        )

    def test_to_and_from_str(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="one"))
        persist.add_pattern(AutoQueuePattern(pattern="two"))
        persist.add_pattern(AutoQueuePattern(pattern="th ree"))
        persist.add_pattern(AutoQueuePattern(pattern="fo.ur"))
        persist.add_pattern(AutoQueuePattern(pattern="fi\"ve"))
        persist.add_pattern(AutoQueuePattern(pattern="si'x"))

        persist_actual = AutoQueuePersist.from_str(persist.to_str())
        self.assertEqual(
            persist.patterns,
            persist_actual.patterns
        )

    def test_persist_read_error(self):
        # bad pattern
        content = """
        {
            "patterns": [
                "bad string"
            ]
        }
        """
        with self.assertRaises(PersistError):
            AutoQueuePersist.from_str(content)

        # empty json
        content = ""
        with self.assertRaises(PersistError):
            AutoQueuePersist.from_str(content)

        # missing keys
        content = "{}"
        with self.assertRaises(PersistError):
            AutoQueuePersist.from_str(content)

        # malformed
        content = "{"
        with self.assertRaises(PersistError):
            AutoQueuePersist.from_str(content)


class TestAutoQueue(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(TestAutoQueue.__name__)
        self._log_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._log_handler)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self._log_handler.setFormatter(formatter)

        self.context = MagicMock()

        self.context.config = Config()
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.patterns_only = True
        self.context.config.autoqueue.auto_extract = True
        self.context.logger = self.logger
        # No scan clock in this harness: sweep cooldown stays inactive
        self.context.status.controller.latest_remote_scan_time = None
        self.controller = MagicMock()
        self.controller.get_model_files_and_add_listener = MagicMock()
        self.controller.queue_command = MagicMock()
        self.model_listener = None
        self.initial_model = []
        # Track which files are "stopped" for testing
        self.stopped_files = set()
        # Track which files are "downloaded" for testing
        self.downloaded_files = set()

        def get_model():
            return self.initial_model

        harness = self

        class ModelSyncingListener:
            """
            Wraps AutoQueue's model listener so that listener events fired by
            tests also update the harness model list, mirroring the real
            system where the Model is updated first and listeners notified
            after. The level-triggered sweep reads the model via
            get_model_files(), so the two must stay in sync.
            """
            def __init__(self, inner: IModelListener):
                self.__inner = inner

            def file_added(self, file: ModelFile):
                harness.initial_model = \
                    [f for f in harness.initial_model if f.name != file.name] + [file]
                self.__inner.file_added(file)

            def file_updated(self, old_file: ModelFile, new_file: ModelFile):
                harness.initial_model = \
                    [f for f in harness.initial_model if f.name != new_file.name] + [new_file]
                self.__inner.file_updated(old_file, new_file)

            def file_removed(self, file: ModelFile):
                harness.initial_model = \
                    [f for f in harness.initial_model if f.name != file.name]
                self.__inner.file_removed(file)

        def get_model_and_capture_listener(listener: IModelListener):
            self.model_listener = ModelSyncingListener(listener)
            return get_model()

        def is_file_stopped(filename: str) -> bool:
            return filename in self.stopped_files

        def is_file_downloaded(filename: str) -> bool:
            return filename in self.downloaded_files

        self.controller.get_model_files.side_effect = get_model
        self.controller.get_model_files_and_add_listener.side_effect = get_model_and_capture_listener
        self.controller.is_file_stopped.side_effect = is_file_stopped
        self.controller.is_file_downloaded.side_effect = is_file_downloaded

    def tearDown(self):
        self.logger.removeHandler(self._log_handler)

    def _mark_queued(self, name):
        """Simulate the real state transition after a QUEUE command is
        processed (DEFAULT -> QUEUED), so the level-triggered sweep stops
        seeing the file as a candidate -- as it would in the real system."""
        for i, f in enumerate(self.initial_model):
            if f.name == name:
                nf = ModelFile(name, f.is_dir)
                nf.remote_size = f.remote_size
                nf.local_size = f.local_size
                nf.state = ModelFile.State.QUEUED
                self.initial_model[i] = nf

    def test_matching_new_files_are_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        auto_queue = AutoQueue(self.context, persist, self.controller)

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300

        self.model_listener.file_added(file_one)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

        self.model_listener.file_added(file_two)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)

        self.model_listener.file_added(file_three)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Three", command.filename)

        # All at once
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list[-3:]
        commands = [calls[i][0][0] for i in range(3)]
        self.assertEqual(set([Controller.Command.Action.QUEUE]*3), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three"}, {c.filename for c in commands})

    def test_matching_initial_files_are_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()

        calls = self.controller.queue_command.call_args_list
        self.assertEqual(3, len(calls))
        commands = [calls[i][0][0] for i in range(3)]
        self.assertEqual(set([Controller.Command.Action.QUEUE]*3), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three"}, {c.filename for c in commands})

    def test_non_matches(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("Two", True)
        file_one.remote_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_matching_is_case_insensitive(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="FiLe.oNe"))

        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("FiLe.oNe", True)
        file_one.remote_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("FiLe.oNe", command.filename)

    def test_partial_matches(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="file"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("fileone", True)  # at start
        file_one.remote_size = 100
        file_two = ModelFile("twofile", True)  # at end
        file_two.remote_size = 100
        file_three = ModelFile("onefiletwo", True)  # in middle
        file_three.remote_size = 100
        file_four = ModelFile("fionele", True)  # no match
        file_four.remote_size = 100
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        self.model_listener.file_added(file_four)
        auto_queue.process()
        self.assertEqual(3, self.controller.queue_command.call_count)
        commands = [call[0][0] for call in self.controller.queue_command.call_args_list]
        commands_dict = {command.filename: command for command in commands}
        self.assertTrue("fileone" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["fileone"].action)
        self.assertTrue("twofile" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["twofile"].action)
        self.assertTrue("onefiletwo" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["onefiletwo"].action)

    def test_wildcard_at_start_matches(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="*.mkv"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One.mkv", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two.jpg", True)
        file_two.remote_size = 100
        file_three = ModelFile(".mkvFile.Three", True)
        file_three.remote_size = 100
        file_four = ModelFile("FileFour.mkv", True)
        file_four.remote_size = 100
        file_five = ModelFile("FileFive.mkv.more", True)
        file_five.remote_size = 100
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        self.model_listener.file_added(file_four)
        self.model_listener.file_added(file_five)
        auto_queue.process()
        self.assertEqual(2, self.controller.queue_command.call_count)
        commands = [call[0][0] for call in self.controller.queue_command.call_args_list]
        commands_dict = {command.filename: command for command in commands}
        self.assertTrue("File.One.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["File.One.mkv"].action)
        self.assertTrue("FileFour.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFour.mkv"].action)

    def test_wildcard_at_end_matches(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File*"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One.mkv", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two.jpg", True)
        file_two.remote_size = 100
        file_three = ModelFile(".mkvFile.Three", True)
        file_three.remote_size = 100
        file_four = ModelFile("FileFour.mkv", True)
        file_four.remote_size = 100
        file_five = ModelFile("FileFive.mkv.more", True)
        file_five.remote_size = 100
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        self.model_listener.file_added(file_four)
        self.model_listener.file_added(file_five)
        auto_queue.process()
        self.assertEqual(4, self.controller.queue_command.call_count)
        commands = [call[0][0] for call in self.controller.queue_command.call_args_list]
        commands_dict = {command.filename: command for command in commands}
        self.assertTrue("File.One.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["File.One.mkv"].action)
        self.assertTrue("File.Two.jpg" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["File.Two.jpg"].action)
        self.assertTrue("FileFour.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFour.mkv"].action)
        self.assertTrue("FileFive.mkv.more" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFive.mkv.more"].action)

    def test_wildcard_in_middle_matches(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="*mkv*"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One.mkv", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two.jpg", True)
        file_two.remote_size = 100
        file_three = ModelFile(".mkvFile.Three", True)
        file_three.remote_size = 100
        file_four = ModelFile("FileFour.mkv", True)
        file_four.remote_size = 100
        file_five = ModelFile("FileFive.mkv.more", True)
        file_five.remote_size = 100
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        self.model_listener.file_added(file_four)
        self.model_listener.file_added(file_five)
        auto_queue.process()
        self.assertEqual(4, self.controller.queue_command.call_count)
        commands = [call[0][0] for call in self.controller.queue_command.call_args_list]
        commands_dict = {command.filename: command for command in commands}
        self.assertTrue("File.One.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["File.One.mkv"].action)
        self.assertTrue(".mkvFile.Three" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict[".mkvFile.Three"].action)
        self.assertTrue("FileFour.mkv" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFour.mkv"].action)
        self.assertTrue("FileFive.mkv.more" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFive.mkv.more"].action)

    def test_wildcard_matches_are_case_insensitive(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="*.mkv"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One.mKV", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two.jpg", True)
        file_two.remote_size = 100
        file_three = ModelFile(".mkvFile.Three", True)
        file_three.remote_size = 100
        file_four = ModelFile("FileFour.MKV", True)
        file_four.remote_size = 100
        file_five = ModelFile("FileFive.mkv.more", True)
        file_five.remote_size = 100
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        self.model_listener.file_added(file_four)
        self.model_listener.file_added(file_five)
        auto_queue.process()
        self.assertEqual(2, self.controller.queue_command.call_count)
        commands = [call[0][0] for call in self.controller.queue_command.call_args_list]
        commands_dict = {command.filename: command for command in commands}
        self.assertTrue("File.One.mKV" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["File.One.mKV"].action)
        self.assertTrue("FileFour.MKV" in commands_dict)
        self.assertEqual(Controller.Command.Action.QUEUE, commands_dict["FileFour.MKV"].action)

    def test_matching_local_files_are_not_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = None
        file_one.local_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_matching_deleted_files_are_not_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = None
        file_one.state = ModelFile.State.DELETED
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_matching_downloading_files_are_not_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = 0
        file_one.state = ModelFile.State.DOWNLOADING
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()
        file_one_new = ModelFile("File.One", True)
        file_one_new.remote_size = 100
        file_one_new.local_size = 50
        file_one_new.state = ModelFile.State.DOWNLOADING
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_matching_queued_files_are_not_queued(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.state = ModelFile.State.QUEUED
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_matching_downloaded_files_are_not_queued(self):
        # Disable auto-extract
        self.context.config.autoqueue.auto_extract = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_auto_queued_file_not_re_queued_after_stopping(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

        # User stops the download: the real STOP command records the name in
        # stopped_file_names (command_processor._handle_stop) -- simulate that
        self.stopped_files.add("File.One")
        file_one_updated = ModelFile("File.One", True)
        file_one_updated.remote_size = 100
        file_one_updated.local_size = 50
        self.model_listener.file_updated(file_one, file_one_updated)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)

    def test_stopped_files_are_not_queued_on_startup(self):
        """
        Test that STOPPED files (partially downloaded files with local_size > 0)
        are NOT auto-queued on startup. These files were explicitly stopped by the
        user and should not be automatically restarted.
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # File.One is a STOPPED file (partially downloaded)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = 50  # Partially downloaded = STOPPED
        file_one.state = ModelFile.State.DEFAULT

        # File.Two is a new file (not started)
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_two.local_size = None  # Not started = should be queued

        # File.Three is a STOPPED file (partially downloaded)
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_three.local_size = 100  # Partially downloaded = STOPPED
        file_three.state = ModelFile.State.DEFAULT

        self.initial_model = [file_one, file_two, file_three]

        # The real STOP command records names in stopped_file_names; partial
        # local content alone no longer blocks the sweep (postmortem v1.7.0)
        self.stopped_files.update({"File.One", "File.Three"})

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()

        # Only File.Two should be queued (File.One/Three are user-stopped)
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(1, len(calls))
        command = calls[0][0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)

    def test_stopped_files_are_not_queued_when_patterns_only_disabled(self):
        """
        Test that STOPPED files are NOT auto-queued even when patterns_only is disabled.
        When patterns_only=False, all new remote files should be queued, but not STOPPED files.
        """
        self.context.config.autoqueue.patterns_only = False

        persist = AutoQueuePersist()

        # File.One is a STOPPED file
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = 50  # Partially downloaded = STOPPED
        file_one.state = ModelFile.State.DEFAULT

        # File.Two is a new file (not started)
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_two.local_size = None  # Not started

        # File.Three is a new file with local_size = 0 (just started, no data yet)
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_three.local_size = 0  # Just started, no data

        # File.Four is a STOPPED file
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_four.local_size = 200  # Partially downloaded = STOPPED
        file_four.state = ModelFile.State.DEFAULT

        self.initial_model = [file_one, file_two, file_three, file_four]

        # The real STOP command records names in stopped_file_names; partial
        # local content alone no longer blocks the sweep (postmortem v1.7.0)
        self.stopped_files.update({"File.One", "File.Four"})

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()

        # Only File.Two and File.Three should be queued (File.One/Four are user-stopped)
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(2, len(calls))
        commands = [calls[i][0][0] for i in range(2)]
        self.assertEqual(set([Controller.Command.Action.QUEUE] * 2), {c.action for c in commands})
        self.assertEqual({"File.Two", "File.Three"}, {c.filename for c in commands})

    def test_deleted_files_are_not_queued_on_startup(self):
        """
        Test that DELETED files (locally deleted but still remote) are NOT auto-queued
        on startup. These files were previously downloaded and then deleted by the user,
        so they should remain in DELETED state until manually re-queued.
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # File.One is a DELETED file (previously downloaded, then deleted locally)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = None  # No local file
        file_one.state = ModelFile.State.DELETED

        # File.Two is a new file (never downloaded)
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_two.local_size = None  # Not started = should be queued

        # File.Three is a DELETED file
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_three.local_size = None  # No local file
        file_three.state = ModelFile.State.DELETED

        self.initial_model = [file_one, file_two, file_three]

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()

        # Only File.Two should be queued (new file, not DELETED)
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(1, len(calls))
        command = calls[0][0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)

    def test_partial_file_is_queued_after_remote_discovery(self):
        # Postmortem v1.7.0 spec change: a partial local file whose remote copy
        # is bigger IS queued by the sweep once the remote is discovered.
        # User-stopped files are excluded via stopped_file_names, not via the
        # mere presence of local content (which also matches stranded partials).
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)

        # Local discovery only -- no remote copy, nothing to queue
        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Remote discovery -- partial local (100) < remote (200): queue it
        file_one_new = ModelFile("File.One", True)
        file_one_new.local_size = 100
        file_one_new.remote_size = 200
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual("File.One", command.filename)

    def test_new_matching_pattern_queues_existing_files(self):
        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()
        self._mark_queued("File.One")

        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)
        self.controller.queue_command.reset_mock()
        self._mark_queued("File.Two")

        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Three", command.filename)
        self.controller.queue_command.reset_mock()
        self._mark_queued("File.Three")

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_new_matching_pattern_doesnt_queue_local_file(self):
        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100

        self.initial_model = [file_one]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_removed_pattern_doesnt_queue_new_file(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="One"))
        persist.add_pattern(AutoQueuePattern(pattern="Two"))
        auto_queue = AutoQueue(self.context, persist, self.controller)

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        self.model_listener.file_added(file_one)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()
        self._mark_queued("File.One")

        persist.remove_pattern(AutoQueuePattern(pattern="Two"))

        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 100
        self.model_listener.file_added(file_two)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_adding_then_removing_pattern_doesnt_queue_existing_file(self):
        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.remove_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_downloaded_file_with_changed_remote_size_is_queued(self):
        # Disable auto-extract
        self.context.config.autoqueue.auto_extract = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        file_one_updated = ModelFile("File.One", True)
        file_one_updated.remote_size = 200
        file_one_updated.local_size = 100
        file_one_updated.state = ModelFile.State.DEFAULT
        self.model_listener.file_updated(file_one, file_one_updated)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

    def test_no_files_are_queued_when_disabled(self):
        self.context.config.autoqueue.enabled = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        # First with patterns_only ON
        self.context.config.autoqueue.patterns_only = True
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Second with patterns_only OFF
        self.context.config.autoqueue.patterns_only = False
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_all_files_are_queued_when_patterns_only_disabled(self):
        self.context.config.autoqueue.patterns_only = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(5, len(calls))
        commands = [calls[i][0][0] for i in range(5)]
        self.assertEqual(set([Controller.Command.Action.QUEUE]*5), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three", "File.Four", "File.Five"},
                         {c.filename for c in commands})

    def test_all_files_are_queued_when_patterns_only_disabled_and_no_patterns_exist(self):
        self.context.config.autoqueue.patterns_only = False

        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 200
        file_three = ModelFile("File.Three", True)
        file_three.remote_size = 300
        file_four = ModelFile("File.Four", True)
        file_four.remote_size = 400
        file_five = ModelFile("File.Five", True)
        file_five.remote_size = 500

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(5, len(calls))
        commands = [calls[i][0][0] for i in range(5)]
        self.assertEqual(set([Controller.Command.Action.QUEUE]*5), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three", "File.Four", "File.Five"},
                         {c.filename for c in commands})

    def test_matching_new_files_are_extracted(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        auto_queue = AutoQueue(self.context, persist, self.controller)

        file_one = ModelFile("File.One", True)
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.local_size = 100
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.local_size = 200
        file_two.is_extractable = True
        file_three = ModelFile("File.Three", True)
        file_three.state = ModelFile.State.DOWNLOADED
        file_three.local_size = 300
        file_three.is_extractable = True

        self.model_listener.file_added(file_one)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)

        self.model_listener.file_added(file_two)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.Two", command.filename)

        self.model_listener.file_added(file_three)
        auto_queue.process()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.Three", command.filename)

        # All at once
        self.model_listener.file_added(file_one)
        self.model_listener.file_added(file_two)
        self.model_listener.file_added(file_three)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list[-3:]
        commands = [calls[i][0][0] for i in range(3)]
        self.assertEqual(set([Controller.Command.Action.EXTRACT]*3), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three"}, {c.filename for c in commands})

    def test_matching_initial_files_are_extracted(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.local_size = 100
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.local_size = 200
        file_two.is_extractable = True
        file_three = ModelFile("File.Three", True)
        file_three.state = ModelFile.State.DOWNLOADED
        file_three.local_size = 300
        file_three.is_extractable = True
        file_four = ModelFile("File.Four", True)
        file_four.state = ModelFile.State.DOWNLOADED
        file_four.local_size = 400
        file_four.is_extractable = True
        file_five = ModelFile("File.Five", True)
        file_five.state = ModelFile.State.DOWNLOADED
        file_five.local_size = 500
        file_five.is_extractable = True

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()

        calls = self.controller.queue_command.call_args_list
        self.assertEqual(3, len(calls))
        commands = [calls[i][0][0] for i in range(3)]
        self.assertEqual(set([Controller.Command.Action.EXTRACT]*3), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three"}, {c.filename for c in commands})

    def test_new_matching_pattern_extracts_existing_files(self):
        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.is_extractable = True
        file_three = ModelFile("File.Three", True)
        file_three.local_size = 300
        file_three.state = ModelFile.State.DOWNLOADED
        file_three.is_extractable = True
        file_four = ModelFile("File.Four", True)
        file_four.local_size = 400
        file_four.state = ModelFile.State.DOWNLOADED
        file_four.is_extractable = True
        file_five = ModelFile("File.Five", True)
        file_five.local_size = 500
        file_five.state = ModelFile.State.DOWNLOADED
        file_five.is_extractable = True

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()

        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.Two", command.filename)
        self.controller.queue_command.reset_mock()

        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.Three", command.filename)
        self.controller.queue_command.reset_mock()

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_non_extractable_files_are_not_extracted(self):
        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.is_extractable = False

        self.initial_model = [file_one, file_two]

        auto_queue = AutoQueue(self.context, persist, self.controller)

        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()

        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_no_files_are_extracted_when_disabled(self):
        self.context.config.autoqueue.enabled = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_three = ModelFile("File.Three", True)
        file_three.local_size = 300
        file_three.state = ModelFile.State.DOWNLOADED
        file_four = ModelFile("File.Four", True)
        file_four.local_size = 400
        file_four.state = ModelFile.State.DOWNLOADED
        file_five = ModelFile("File.Five", True)
        file_five.local_size = 500
        file_five.state = ModelFile.State.DOWNLOADED

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        # First with patterns_only ON
        self.context.config.autoqueue.patterns_only = True
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Second with patterns_only OFF
        self.context.config.autoqueue.patterns_only = False
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_no_files_are_extracted_when_auto_extract_disabled(self):
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.auto_extract = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_three = ModelFile("File.Three", True)
        file_three.local_size = 300
        file_three.state = ModelFile.State.DOWNLOADED
        file_four = ModelFile("File.Four", True)
        file_four.local_size = 400
        file_four.state = ModelFile.State.DOWNLOADED
        file_five = ModelFile("File.Five", True)
        file_five.local_size = 500
        file_five.state = ModelFile.State.DOWNLOADED

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        # First with patterns_only ON
        self.context.config.autoqueue.patterns_only = True
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Second with patterns_only OFF
        self.context.config.autoqueue.patterns_only = False
        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_all_files_are_extracted_when_patterns_only_disabled(self):
        self.context.config.autoqueue.patterns_only = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Two"))
        persist.add_pattern(AutoQueuePattern(pattern="File.Three"))

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.is_extractable = True
        file_three = ModelFile("File.Three", True)
        file_three.local_size = 300
        file_three.state = ModelFile.State.DOWNLOADED
        file_three.is_extractable = True
        file_four = ModelFile("File.Four", True)
        file_four.local_size = 400
        file_four.state = ModelFile.State.DOWNLOADED
        file_four.is_extractable = True
        file_five = ModelFile("File.Five", True)
        file_five.local_size = 500
        file_five.state = ModelFile.State.DOWNLOADED
        file_five.is_extractable = True

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(5, len(calls))
        commands = [calls[i][0][0] for i in range(5)]
        self.assertEqual(set([Controller.Command.Action.EXTRACT]*5), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three", "File.Four", "File.Five"},
                         {c.filename for c in commands})

    def test_all_files_are_extracted_when_patterns_only_disabled_and_no_patterns_exist(self):
        self.context.config.autoqueue.patterns_only = False

        persist = AutoQueuePersist()

        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        file_two = ModelFile("File.Two", True)
        file_two.local_size = 200
        file_two.state = ModelFile.State.DOWNLOADED
        file_two.is_extractable = True
        file_three = ModelFile("File.Three", True)
        file_three.local_size = 300
        file_three.state = ModelFile.State.DOWNLOADED
        file_three.is_extractable = True
        file_four = ModelFile("File.Four", True)
        file_four.local_size = 400
        file_four.state = ModelFile.State.DOWNLOADED
        file_four.is_extractable = True
        file_five = ModelFile("File.Five", True)
        file_five.local_size = 500
        file_five.state = ModelFile.State.DOWNLOADED
        file_five.is_extractable = True

        self.initial_model = [file_one, file_two, file_three, file_four, file_five]

        auto_queue = AutoQueue(self.context, persist, self.controller)
        auto_queue.process()
        calls = self.controller.queue_command.call_args_list
        self.assertEqual(5, len(calls))
        commands = [calls[i][0][0] for i in range(5)]
        self.assertEqual(set([Controller.Command.Action.EXTRACT]*5), {c.action for c in commands})
        self.assertEqual({"File.One", "File.Two", "File.Three", "File.Four", "File.Five"},
                         {c.filename for c in commands})

    def test_file_is_extracted_after_finishing_download(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File exists remotely and is auto-queued
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.is_extractable = True
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()

        # File starts downloading
        file_one_new = ModelFile("File.One", True)
        file_one_new.remote_size = 100
        file_one_new.local_size = 50
        file_one_new.state = ModelFile.State.DOWNLOADING
        file_one_new.is_extractable = True
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # File finishes downloading
        file_one = file_one_new
        file_one_new = ModelFile("File.One", True)
        file_one_new.remote_size = 100
        file_one_new.local_size = 100
        file_one_new.state = ModelFile.State.DOWNLOADED
        file_one_new.is_extractable = True
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)

    def test_downloaded_file_is_NOT_re_extracted_after_modified(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File is auto-extracted
        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()

        # File is modified
        file_one_new = ModelFile("File.One", True)
        file_one_new.local_size = 101
        file_one_new.state = ModelFile.State.DOWNLOADED
        file_one_new.is_extractable = True
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_downloaded_file_is_NOT_re_extracted_after_failed_extraction(self):
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File.One"))
        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File is auto-extracted
        file_one = ModelFile("File.One", True)
        file_one.local_size = 100
        file_one.state = ModelFile.State.DOWNLOADED
        file_one.is_extractable = True
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.EXTRACT, command.action)
        self.assertEqual("File.One", command.filename)
        self.controller.queue_command.reset_mock()

        # File is extracting
        file_one_new = ModelFile("File.One", True)
        file_one_new.local_size = 101
        file_one_new.state = ModelFile.State.EXTRACTING
        file_one_new.is_extractable = True
        self.model_listener.file_updated(file_one, file_one_new)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Extraction fails and file goes back to DOWNLOADED
        file_one_newer = ModelFile("File.One", True)
        file_one_newer.local_size = 101
        file_one_newer.state = ModelFile.State.DOWNLOADED
        file_one_newer.is_extractable = True
        self.model_listener.file_updated(file_one_new, file_one_newer)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

    def test_stopped_file_not_queued_when_remote_discovered_via_update(self):
        """
        Test that STOPPED files are NOT re-queued when remote scan discovers them
        after local scan (remote_size goes from None to a value).

        This simulates a startup scenario where:
        1. Local scan completes first, finding a partial file (STOPPED)
        2. Remote scan completes later, updating remote_size from None to actual

        The file should NOT be queued because local_size > 0 indicates it was stopped.
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # The file was stopped by the user; the real STOP command records it
        self.stopped_files.add("File.One")

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # Step 1: Local scan finds a partial file (STOPPED file)
        # remote_size is None because remote scan hasn't completed yet
        file_one = ModelFile("File.One", True)
        file_one.remote_size = None  # Remote scan not complete yet
        file_one.local_size = 50  # Partially downloaded = STOPPED
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)
        auto_queue.process()
        # Should not queue because no remote_size yet
        self.controller.queue_command.assert_not_called()

        # Step 2: Remote scan completes, remote_size discovered
        file_one_updated = ModelFile("File.One", True)
        file_one_updated.remote_size = 100  # Now we know the remote size
        file_one_updated.local_size = 50  # Still a STOPPED file
        file_one_updated.state = ModelFile.State.DEFAULT
        self.model_listener.file_updated(file_one, file_one_updated)
        auto_queue.process()
        # Should NOT queue because local_size > 0 indicates STOPPED file
        self.controller.queue_command.assert_not_called()

    def test_new_file_queued_when_remote_discovered_via_update(self):
        """
        Test that new files (no local content) ARE queued when remote scan
        discovers them after local scan.

        This simulates a startup scenario where:
        1. Local scan completes first (file might have local_size = 0 or None)
        2. Remote scan completes later, updating remote_size from None to actual

        The file should be queued because local_size is 0 or None (not a STOPPED file).
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # Step 1: File seen with no remote_size yet
        file_one = ModelFile("File.One", True)
        file_one.remote_size = None
        file_one.local_size = None  # No local file
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)
        auto_queue.process()
        self.controller.queue_command.assert_not_called()

        # Step 2: Remote scan discovers the file
        file_one_updated = ModelFile("File.One", True)
        file_one_updated.remote_size = 100
        file_one_updated.local_size = None  # Still no local file
        file_one_updated.state = ModelFile.State.DEFAULT
        self.model_listener.file_updated(file_one, file_one_updated)
        auto_queue.process()
        # Should queue because local_size is None (new file, not STOPPED)
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

    def test_partial_file_with_bigger_remote_is_queued_by_sweep(self):
        """
        Postmortem v1.7.0 spec change: a DEFAULT file with partial local
        content and a bigger remote copy IS a queue candidate (the sweep),
        unless the user explicitly stopped it (stopped_file_names). With no
        stability window configured, it queues immediately.
        """
        # Disable auto-extract for this test
        self.context.config.autoqueue.auto_extract = False

        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File already exists with remote_size and partial local content
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = 50  # Partial content
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)
        auto_queue.process()
        # Sweep queues the partial file (remote bigger than local, not stopped)
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

    def test_explicitly_stopped_files_are_not_auto_queued(self):
        """
        Test that files tracked as 'stopped' by the controller are NOT auto-queued.

        This tests the fix for files that were queued but stopped before any
        content was downloaded. These files are tracked in stopped_file_names
        and should not be auto-queued on restart.
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # Mark "File.One" as stopped (simulates user stopping a queued file)
        self.stopped_files.add("File.One")

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # New file matches pattern but is marked as stopped
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = None  # No local content (was never downloaded)
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)

        # Also add a file that is NOT stopped
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 100
        file_two.local_size = None
        file_two.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_two)

        auto_queue.process()

        # Only File.Two should be queued (File.One is stopped)
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)

    def test_manually_queued_file_clears_stopped_status(self):
        """
        Test that when a user manually queues a file (simulated by removing from
        stopped_files), it can be auto-queued again after remote update.

        This verifies the workflow: stop file -> restart -> manually queue ->
        remote updates -> should auto-queue.
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # Initially mark file as stopped
        self.stopped_files.add("File.One")

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File exists but is stopped
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = None
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)
        auto_queue.process()

        # Should NOT queue because file is stopped
        self.controller.queue_command.assert_not_called()

        # User manually queues the file (removes from stopped)
        self.stopped_files.discard("File.One")

        # Remote file is updated
        file_one_updated = ModelFile("File.One", True)
        file_one_updated.remote_size = 200  # Size changed
        file_one_updated.local_size = None
        file_one_updated.state = ModelFile.State.DEFAULT
        self.model_listener.file_updated(file_one, file_one_updated)
        auto_queue.process()

        # Now should queue because file is no longer stopped
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.One", command.filename)

    def test_already_downloaded_files_are_not_re_queued(self):
        """
        Test that files tracked as 'downloaded' by the controller are NOT auto-queued,
        even if the local file no longer exists.

        This tests the fix for the Sonarr workflow where:
        1. SeedSyncarr downloads a file
        2. Sonarr moves/deletes the local file
        3. AutoQueue should NOT re-queue because file is in downloaded_file_names
        """
        persist = AutoQueuePersist()
        persist.add_pattern(AutoQueuePattern(pattern="File"))

        # Mark "File.One" as already downloaded (simulates file that was downloaded
        # but then moved/deleted by Sonarr)
        self.downloaded_files.add("File.One")

        auto_queue = AutoQueue(self.context, persist, self.controller)

        # File exists on remote but no local file (Sonarr moved it)
        file_one = ModelFile("File.One", True)
        file_one.remote_size = 100
        file_one.local_size = None  # No local file - Sonarr moved it
        file_one.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_one)

        # Also add a file that was NOT previously downloaded
        file_two = ModelFile("File.Two", True)
        file_two.remote_size = 100
        file_two.local_size = None
        file_two.state = ModelFile.State.DEFAULT
        self.model_listener.file_added(file_two)

        auto_queue.process()

        # Only File.Two should be queued (File.One is in downloaded_files)
        self.controller.queue_command.assert_called_once_with(ANY)
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual("File.Two", command.filename)


class TestAutoQueueCommandOrigin(unittest.TestCase):
    """Auto-queue must mark its QUEUE commands with AUTO origin so the
    controller re-checks stopped/downloaded guards at execution time."""

    def setUp(self):
        self.context = MagicMock()
        self.context.logger = MagicMock()
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.patterns_only = False
        self.context.config.autoqueue.auto_extract = False
        self.context.config.autoqueue.remote_stability_seconds = 0
        self.context.status.controller.latest_remote_scan_time = None
        self.controller = MagicMock()
        self.controller.get_model_files_and_add_listener.return_value = []
        self.controller.is_file_stopped.return_value = False
        self.controller.is_file_downloaded.return_value = False

    def test_queue_commands_have_auto_origin(self):
        from controller import AutoQueue, AutoQueuePersist
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)
        listener = self.controller.get_model_files_and_add_listener.call_args[0][0]
        f = ModelFile("file", False)
        f.remote_size = 1000
        listener.file_added(f)
        self.controller.get_model_files.return_value = [f]
        auto_queue.process()
        self.controller.queue_command.assert_called_once()
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Origin.AUTO, command.origin)


class TestAutoQueueComposedPipeline(unittest.TestCase):
    """
    Composed repro for the 2026-09-05 postmortem (gate-log v1.7.0 001-postmortem):
    a release queued while the seedbox torrent was still writing completes its
    transfer at the snapshot size, the remote keeps growing, and the file must
    be re-queued. Drives the REAL ModelBuilder -> ModelDiffUtil -> Model ->
    listener chain instead of hand-crafted listener events, so any divergence
    between builder-produced files and the unit-test fixtures shows up here.
    """

    FILE = "File.One"

    def setUp(self):
        from model import Model, ModelDiff, ModelDiffUtil
        from controller.model_builder import ModelBuilder
        self.ModelDiff = ModelDiff
        self.ModelDiffUtil = ModelDiffUtil

        self.logger = logging.getLogger(TestAutoQueueComposedPipeline.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.DEBUG)

        self.context = MagicMock()
        self.context.config = Config()
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.patterns_only = False
        self.context.config.autoqueue.auto_extract = False
        self.context.logger = self.logger
        self.context.status.controller.latest_remote_scan_time = None

        self.model = Model()
        self.model.set_base_logger(self.logger)

        self.builder = ModelBuilder()
        self.builder.set_base_logger(self.logger)
        self.builder.set_downloaded_files(set())

        self.controller = MagicMock()
        self.controller.queue_command = MagicMock()
        self.controller.is_file_stopped.side_effect = lambda name: False
        self.controller.is_file_downloaded.side_effect = lambda name: False

        def add_listener_and_get(listener):
            self.model.add_listener(listener)
            return [self.model.get_file(n) for n in self.model.get_file_names()]

        self.controller.get_model_files_and_add_listener.side_effect = add_listener_and_get
        self.controller.get_model_files.side_effect = \
            lambda: [self.model.get_file(n) for n in self.model.get_file_names()]

    def _build_and_apply(self):
        """Mirror ModelPipeline.build_and_apply_model's gate and diff/apply stages."""
        if not self.builder.has_changes():
            return
        new_model = self.builder.build_model()
        for diff in self.ModelDiffUtil.diff_models(self.model, new_model):
            if diff.change == self.ModelDiff.Change.ADDED:
                self.model.add_file(diff.new_file)
            elif diff.change == self.ModelDiff.Change.REMOVED:
                self.model.remove_file(diff.old_file.name)
            elif diff.change == self.ModelDiff.Change.UPDATED:
                self.model.update_file(diff.new_file)

    def _queued_filenames(self):
        return [c[0][0].filename for c in self.controller.queue_command.call_args_list]

    def test_remote_growth_after_transfer_completion_requeues_file(self):
        from system import SystemFile
        from lftp import LftpJobStatus

        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        # Frame 1: remote scan discovers the file (torrent still writing, 100 bytes so far)
        self.builder.set_remote_files([SystemFile(self.FILE, 100, False)])
        self._build_and_apply()
        auto_queue.process()
        self.assertEqual([self.FILE], self._queued_filenames(),
                         "new remote file should be auto-queued")

        # Frame 2: lftp job now queued
        self.builder.set_lftp_statuses([LftpJobStatus(
            1, LftpJobStatus.Type.PGET, LftpJobStatus.State.QUEUED, self.FILE, "")])
        self._build_and_apply()
        auto_queue.process()

        # Frame 3: transfer running; remote grew; partial local appears via active scan
        self.builder.set_remote_files([SystemFile(self.FILE, 110, False)])
        self.builder.set_active_files([SystemFile(self.FILE, 50, False)])
        self._build_and_apply()
        auto_queue.process()

        # Frame 4: transfer completed at the 100-byte snapshot; job gone from lftp;
        # local scan confirms 100 bytes; remote has moved on to 120
        self.builder.set_lftp_statuses([])
        self.builder.set_local_files([SystemFile(self.FILE, 100, False)])
        self.builder.set_remote_files([SystemFile(self.FILE, 120, False)])
        self._build_and_apply()
        auto_queue.process()

        # Frame 5: next remote scan, still growing
        self.builder.set_remote_files([SystemFile(self.FILE, 130, False)])
        self._build_and_apply()
        auto_queue.process()

        # With no stability window configured the sweep may fire on every
        # cycle while the file stays DEFAULT; the behavior under test is that
        # at least one re-queue happened after the initial queue.
        self.assertGreaterEqual(
            self.controller.queue_command.call_count, 2,
            "partial file whose remote grew after transfer completion "
            "must be re-queued (got queue commands for: {})".format(
                self._queued_filenames()))
        for filename in self._queued_filenames():
            self.assertEqual(self.FILE, filename)


class TestAutoQueueStabilityAndSweep(unittest.TestCase):
    """
    Tests for the level-triggered auto-queue sweep (postmortem v1.7.0
    001-postmortem): remote-size stability gating before the initial queue, and
    recovery of stranded partial files whose remote finished growing while no
    model events were delivered (restart / scanner outage / missed edge).

    All timing is driven by the remote scan clock
    (context.status.controller.latest_remote_scan_time), never wall-clock, so a
    paused scanner can never fake stability.
    """

    FILE = "File.One"
    STABILITY = 90

    def setUp(self):
        self.logger = logging.getLogger(TestAutoQueueStabilityAndSweep.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.DEBUG)

        self.context = MagicMock()
        self.context.config = Config()
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.patterns_only = False
        self.context.config.autoqueue.auto_extract = False
        self.context.config.autoqueue.remote_stability_seconds = self.STABILITY
        self.context.logger = self.logger

        self.scan_time = None

        class _ControllerStatus:
            pass

        self.context.status.controller = _ControllerStatus()
        self.context.status.controller.latest_remote_scan_time = None

        self.controller = MagicMock()
        self.controller.queue_command = MagicMock()
        self.model_files = []
        self.stopped_files = set()
        self.downloaded_files = set()
        self.model_listener = None

        def add_listener_and_get(listener):
            self.model_listener = listener
            return list(self.model_files)

        self.controller.get_model_files.side_effect = lambda: list(self.model_files)
        self.controller.get_model_files_and_add_listener.side_effect = add_listener_and_get
        self.controller.is_file_stopped.side_effect = lambda n: n in self.stopped_files
        self.controller.is_file_downloaded.side_effect = lambda n: n in self.downloaded_files

    def tearDown(self):
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)

    def _set_scan(self, scan_time, remote_size, local_size=None,
                  state=ModelFile.State.DEFAULT):
        """Simulate a remote scan result landing in the model at scan_time."""
        f = ModelFile(self.FILE, False)
        f.remote_size = remote_size
        f.local_size = local_size
        f.state = state
        old = self.model_files[0] if self.model_files else None
        self.model_files = [f]
        self.context.status.controller.latest_remote_scan_time = scan_time
        if self.model_listener is not None:
            if old is None:
                self.model_listener.file_added(f)
            elif old.remote_size != f.remote_size or old.local_size != f.local_size \
                    or old.state != f.state:
                self.model_listener.file_updated(old, f)

    def _queued_count(self):
        return self.controller.queue_command.call_count

    def test_new_file_not_queued_until_remote_size_stable(self):
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        # Torrent still writing on the seedbox: size grows scan over scan
        self._set_scan(1000, remote_size=100)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "file must not be queued on first sighting (size not yet stable)")

        self._set_scan(1030, remote_size=110)
        auto_queue.process()
        self._set_scan(1060, remote_size=120)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "file must not be queued while remote size is changing")

        # Size stops changing at t=1060; stability window not yet elapsed
        self._set_scan(1149, remote_size=120)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "file must not be queued before the stability window elapses")

        # Stability window elapsed
        self._set_scan(1150, remote_size=120)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "file must be queued once remote size is stable")
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual(self.FILE, command.filename)

    def test_stranded_partial_with_stable_bigger_remote_is_requeued(self):
        """
        THE incident shape: after a restart (or any missed-event window) the
        model baseline already contains the grown remote size and a partial
        local copy in DEFAULT state. No size-change event will ever fire.
        The file must still be re-queued once the remote is stable.
        """
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=36_161_824_826, local_size=35_643_195_392)
        auto_queue.process()
        self.assertEqual(0, self._queued_count())

        # Scans keep landing; nothing about the file changes
        self._set_scan(1050, remote_size=36_161_824_826, local_size=35_643_195_392)
        auto_queue.process()
        self._set_scan(1090, remote_size=36_161_824_826, local_size=35_643_195_392)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "stranded partial file with stable bigger remote must be re-queued")
        command = self.controller.queue_command.call_args[0][0]
        self.assertEqual(self.FILE, command.filename)

    def test_user_stopped_partial_is_not_swept(self):
        self.stopped_files.add(self.FILE)
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=200, local_size=100)
        auto_queue.process()
        self._set_scan(1200, remote_size=200, local_size=100)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "user-stopped file must never be swept back into the queue")

    def test_downloaded_file_is_not_swept(self):
        self.downloaded_files.add(self.FILE)
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=200, local_size=100)
        auto_queue.process()
        self._set_scan(1200, remote_size=200, local_size=100)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "file tracked as downloaded must not be swept")

    def test_non_default_states_are_not_swept(self):
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=200, local_size=100,
                       state=ModelFile.State.DOWNLOADING)
        auto_queue.process()
        self._set_scan(1200, remote_size=200, local_size=100,
                       state=ModelFile.State.DOWNLOADING)
        auto_queue.process()
        self.assertEqual(0, self._queued_count(),
                         "actively downloading file must not be swept")

    def test_scan_time_as_datetime_is_supported(self):
        """
        Production contract: latest_remote_scan_time is a datetime
        (Controller._update_controller_status stores remote_scan.timestamp,
        which ScannerProcess populates with datetime.now(); the status
        serializer calls .timestamp() on it). The sweep must accept datetime
        scan times, not just numeric epochs (review pass-3 bugs-001: float()
        on a datetime raises TypeError and kills ControllerJob).
        """
        from datetime import datetime as _dt
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        base = 1_700_000_000
        self._set_scan(_dt.fromtimestamp(base), remote_size=120)
        auto_queue.process()
        self.assertEqual(0, self._queued_count())

        self._set_scan(_dt.fromtimestamp(base + self.STABILITY), remote_size=120)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "datetime scan times must gate and queue exactly like epochs")

    def test_disabled_stability_gate_still_applies_cooldown(self):
        """
        With remote_stability_seconds=0 (e2e config) the stability gate is off,
        but the requeue cooldown must still apply while a scan clock exists —
        otherwise the sweep re-queues the same DEFAULT file every process
        cycle until lftp status catches up, stacking duplicate lftp jobs
        (review pass-3 bugs-002).
        """
        self.context.config.autoqueue.remote_stability_seconds = 0
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=200, local_size=None)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "gate disabled: first sighting queues immediately")

        # Same cycle cadence, file still DEFAULT (lftp status not yet observed)
        self._set_scan(1001, remote_size=200, local_size=None)
        auto_queue.process()
        self._set_scan(1002, remote_size=200, local_size=None)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "cooldown must suppress duplicate queue commands while DEFAULT")

    def test_sweep_cooldown_prevents_requeue_spam(self):
        auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        self._set_scan(1000, remote_size=200, local_size=100)
        auto_queue.process()
        self._set_scan(1090, remote_size=200, local_size=100)
        auto_queue.process()
        self.assertEqual(1, self._queued_count())

        # State never leaves DEFAULT (e.g. lftp error) -- scans keep landing
        self._set_scan(1120, remote_size=200, local_size=100)
        auto_queue.process()
        self._set_scan(1200, remote_size=200, local_size=100)
        auto_queue.process()
        self.assertEqual(1, self._queued_count(),
                         "sweep must not re-queue the same file within the cooldown window")

        # Cooldown elapsed (AutoQueue.REQUEUE_COOLDOWN_SECONDS past the attempt)
        self._set_scan(1090 + AutoQueue.REQUEUE_COOLDOWN_SECONDS, remote_size=200, local_size=100)
        auto_queue.process()
        self.assertEqual(2, self._queued_count(),
                         "sweep must retry after the cooldown window elapses")
