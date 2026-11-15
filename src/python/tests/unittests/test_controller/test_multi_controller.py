import logging
import unittest
from unittest.mock import MagicMock

from common import PathPair
from controller import Controller
from controller.multi_controller import (
    AutoQueueGroup,
    MultiController,
    WebhookFanout,
    pair_scoped_context,
)


class _Callback(Controller.Command.ICallback):
    def __init__(self):
        self.failure = None

    def on_success(self):
        pass

    def on_failure(self, error: str, error_code: int = 400):
        self.failure = (error, error_code)


def _fake_controller(names=()):
    controller = MagicMock(spec=Controller)
    controller.has_model_file.side_effect = lambda name: name in names
    controller.get_model_files.return_value = []
    return controller


def _command(filename, pair_id=None):
    return Controller.Command(
        Controller.Command.Action.QUEUE, filename, pair_id=pair_id
    )


class TestPairScopedContext(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.context.logger = logging.getLogger("test_pair_scoped_context")
        self.context.config.lftp.remote_path = "/shared/remote"
        self.context.config.lftp.local_path = "/shared/local"
        self.context.config.lftp.remote_address = "host"
        self.context.config.controller.interval_ms_remote_scan = 100
        self.pair = PathPair("tv", "/remote/tv", "/local/tv")

    def test_paths_are_those_of_the_pair(self):
        scoped = pair_scoped_context(self.context, self.pair)
        self.assertEqual("/remote/tv", scoped.config.lftp.remote_path)
        self.assertEqual("/local/tv", scoped.config.lftp.local_path)

    def test_shared_config_is_not_changed(self):
        pair_scoped_context(self.context, self.pair)
        self.assertEqual("/shared/remote", self.context.config.lftp.remote_path)
        self.assertEqual("/shared/local", self.context.config.lftp.local_path)

    def test_other_options_pass_through_live(self):
        scoped = pair_scoped_context(self.context, self.pair)
        self.assertEqual("host", scoped.config.lftp.remote_address)
        self.assertEqual(100, scoped.config.controller.interval_ms_remote_scan)
        self.context.config.lftp.remote_address = "other-host"
        self.assertEqual("other-host", scoped.config.lftp.remote_address)

    def test_pairs_are_independent(self):
        a = pair_scoped_context(self.context, self.pair)
        b = pair_scoped_context(
            self.context, PathPair("movies", "/remote/m", "/local/m")
        )
        self.assertEqual("/local/tv", a.config.lftp.local_path)
        self.assertEqual("/local/m", b.config.lftp.local_path)

    def test_other_context_members_are_shared(self):
        scoped = pair_scoped_context(self.context, self.pair)
        self.assertIs(self.context.status, scoped.status)
        self.assertIs(self.context.args, scoped.args)


class TestFanouts(unittest.TestCase):
    def test_webhook_fanout_reaches_every_manager(self):
        managers = [MagicMock(), MagicMock()]
        WebhookFanout(managers).enqueue_import("Sonarr", "a.mkv", "prov")
        for manager in managers:
            manager.enqueue_import.assert_called_once_with("Sonarr", "a.mkv", "prov")

    def _fanout(self, names_per_pair):
        managers = [MagicMock() for _ in names_per_pair]
        matchers = [
            (lambda n, names=names: n.lower() in names) for names in names_per_pair
        ]
        return WebhookFanout(
            managers, matchers, logging.getLogger("test_fanout")
        ), managers

    def test_webhook_name_in_one_pair_goes_only_to_that_pair(self):
        fanout, managers = self._fanout([{"a.mkv"}, {"b.mkv"}])
        fanout.enqueue_import("Sonarr", "A.mkv", "prov")
        managers[0].enqueue_import.assert_called_once_with("Sonarr", "A.mkv", "prov")
        managers[1].enqueue_import.assert_not_called()

    def test_webhook_name_in_two_pairs_is_dropped_as_ambiguous(self):
        fanout, managers = self._fanout([{"a.mkv"}, {"a.mkv"}, set()])
        with self.assertLogs("test_fanout", level="WARNING") as logs:
            fanout.enqueue_import("Sonarr", "a.mkv", "prov")
        for manager in managers:
            manager.enqueue_import.assert_not_called()
        self.assertIn("ambiguous", logs.output[0])

    def test_unknown_webhook_name_goes_to_every_pair(self):
        fanout, managers = self._fanout([{"a.mkv"}, {"b.mkv"}])
        fanout.enqueue_import("Radarr", "c.mkv", "prov")
        for manager in managers:
            manager.enqueue_import.assert_called_once_with("Radarr", "c.mkv", "prov")

    def test_webhook_fanout_needs_a_matcher_per_manager(self):
        with self.assertRaises(ValueError):
            WebhookFanout([MagicMock(), MagicMock()], [lambda n: True])

    def test_ambiguous_name_arms_no_pair_but_a_unique_name_still_does(self):
        # Real managers: the same name in two pairs must not credit either pair
        from controller import WebhookManager

        managers = [WebhookManager(MagicMock()), WebhookManager(MagicMock())]
        lookup = [
            {"same.mkv": {"same.mkv": "same.mkv"}, "tv.mkv": {"tv.mkv": "tv.mkv"}},
            {"same.mkv": {"same.mkv": "same.mkv"}},
        ]
        matchers = [(lambda n, d=d: n.lower() in d) for d in lookup]
        fanout = WebhookFanout(managers, matchers, logging.getLogger("test_fanout"))
        fanout.enqueue_import("Sonarr", "same.mkv", "prov")
        fanout.enqueue_import("Sonarr", "tv.mkv", "prov")
        self.assertEqual([("tv.mkv", "tv.mkv")], managers[0].process(lookup[0]))
        self.assertEqual([], managers[1].process(lookup[1]))

    def test_auto_queue_group_processes_every_queue(self):
        queues = [MagicMock(), MagicMock()]
        AutoQueueGroup(queues).process()
        for queue in queues:
            queue.process.assert_called_once_with()


class TestMultiController(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_multi_controller")
        self.c1 = _fake_controller({"a", "only1"})
        self.c2 = _fake_controller({"a", "only2"})
        self.multi = MultiController([("p1", self.c1), ("p2", self.c2)], self.logger)

    def test_needs_a_controller(self):
        with self.assertRaises(ValueError):
            MultiController([], self.logger)

    def test_lifecycle_reaches_all(self):
        self.multi.start()
        self.multi.process()
        self.multi.note_shutdown_requested()
        self.multi.exit()
        for c in (self.c1, self.c2):
            c.start.assert_called_once_with()
            c.process.assert_called_once_with()
            c.note_shutdown_requested.assert_called_once_with()
            c.exit.assert_called_once_with()

    def test_exit_continues_after_a_failure(self):
        self.c1.exit.side_effect = RuntimeError("boom")
        self.multi.exit()
        self.c2.exit.assert_called_once_with()

    def test_start_failure_stops_the_others(self):
        c3 = _fake_controller()
        multi = MultiController(
            [("p1", self.c1), ("p2", self.c2), ("p3", c3)], self.logger
        )
        self.c2.start.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            multi.start()
        self.c1.exit.assert_called_once_with()
        c3.stop_lftp.assert_called_once_with()
        c3.start.assert_not_called()
        self.c2.exit.assert_not_called()

    def test_model_files_are_combined(self):
        f1, f2 = MagicMock(), MagicMock()
        self.c1.get_model_files.return_value = [f1]
        self.c2.get_model_files.return_value = [f2]
        self.assertEqual([f1, f2], self.multi.get_model_files())

    def test_listeners_are_added_and_removed_everywhere(self):
        listener = MagicMock()
        self.multi.add_model_listener(listener)
        self.multi.remove_model_listener(listener)
        for c in (self.c1, self.c2):
            c.add_model_listener.assert_called_once_with(listener)
            c.remove_model_listener.assert_called_once_with(listener)

    def test_files_and_listener_are_combined(self):
        f1, f2 = MagicMock(), MagicMock()
        self.c1.get_model_files_and_add_listener.return_value = [f1]
        self.c2.get_model_files_and_add_listener.return_value = [f2]
        listener = MagicMock()
        self.assertEqual(
            [f1, f2], self.multi.get_model_files_and_add_listener(listener)
        )

    def test_resync_discards_once_with_all_locks_held(self):
        events = []

        def resync(name, files):
            def fn(discard):
                events.append(("lock", name))
                discard()
                events.append(("unlock", name))
                return files

            return fn

        f1, f2 = MagicMock(), MagicMock()
        self.c1.resync_model_files.side_effect = resync("p1", [f1])
        self.c2.resync_model_files.side_effect = resync("p2", [f2])
        discard = MagicMock(side_effect=lambda: events.append(("discard", None)))
        self.assertEqual([f1, f2], self.multi.resync_model_files(discard))
        discard.assert_called_once_with()
        self.assertEqual(
            [
                ("lock", "p1"),
                ("lock", "p2"),
                ("discard", None),
                ("unlock", "p2"),
                ("unlock", "p1"),
            ],
            events,
        )

    def test_command_with_pair_id_goes_to_that_pair(self):
        command = _command("a", pair_id="p2")
        self.multi.queue_command(command)
        self.c2.queue_command.assert_called_once_with(command)
        self.c1.queue_command.assert_not_called()

    def test_command_goes_to_the_pair_holding_the_file(self):
        command = _command("only2")
        self.multi.queue_command(command)
        self.c2.queue_command.assert_called_once_with(command)
        self.c1.queue_command.assert_not_called()

    def test_ambiguous_command_is_rejected(self):
        command = _command("a")
        callback = _Callback()
        command.add_callback(callback)
        self.multi.queue_command(command)
        self.c1.queue_command.assert_not_called()
        self.c2.queue_command.assert_not_called()
        self.assertEqual(400, callback.failure[1])
        self.assertIn("more than one path pair", callback.failure[0])

    def test_unknown_file_goes_to_the_first_pair(self):
        command = _command("missing")
        self.multi.queue_command(command)
        self.c1.queue_command.assert_called_once_with(command)

    def test_unknown_pair_is_rejected(self):
        # Must not fall back to another pair: the same name could exist there
        command = _command("a", pair_id="nope")
        callback = _Callback()
        command.add_callback(callback)
        self.multi.queue_command(command)
        self.c1.queue_command.assert_not_called()
        self.c2.queue_command.assert_not_called()
        self.assertEqual(404, callback.failure[1])

    def test_single_controller_gets_everything(self):
        single = MultiController([("p1", self.c1)], self.logger)
        command = _command("a", pair_id="whatever")
        single.queue_command(command)
        self.c1.queue_command.assert_called_once_with(command)
