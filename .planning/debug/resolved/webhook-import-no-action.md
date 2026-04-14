---
status: resolved
trigger: "Sonarr/Radarr webhook import is received and enqueued but the file is never tagged as imported and never deleted after safety delay."
created: 2026-02-12T15:30:00Z
updated: 2026-02-12T16:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: 545 unit tests passed (0 failures)
expecting: N/A
next_action: Archive session

## Symptoms

expected: When a file is imported by Sonarr/Radarr, the webhook fires, the file gets tagged as "imported", and after a safety delay, the local file is deleted automatically.
actual: The webhook import is received and logged ("Sonarr webhook import enqueued") but nothing happens after that - no import tag, no deletion.
errors: No error messages visible. Only INFO log for enqueue.
reproduction: File imported by Sonarr via webhook. Log shows enqueue but no subsequent action.
started: Unknown if regression or never worked.

## Eliminated

- hypothesis: Queue is never consumed / process() never called
  evidence: Controller.process() calls __check_webhook_imports() every 0.5s cycle (Job._DEFAULT_SLEEP_INTERVAL_IN_SECS). __check_webhook_imports() drains the queue via WebhookManager.process().
  timestamp: 2026-02-12T15:35:00Z

- hypothesis: Threading issue prevents queue consumption
  evidence: Queue is thread-safe (stdlib queue.Queue). enqueue from web thread, process from controller thread is correct. Model access from same thread as process().
  timestamp: 2026-02-12T15:36:00Z

- hypothesis: Model is empty when webhook is processed
  evidence: __update_model() runs before __check_webhook_imports() in Controller.process(). File was already downloaded by SeedSync (precondition for Sonarr to import), so model has data.
  timestamp: 2026-02-12T15:37:00Z

## Evidence

- timestamp: 2026-02-12T15:33:00Z
  checked: WebhookManager.process() matching logic (webhook_manager.py:40-80)
  found: Matching is case-insensitive exact match of webhook file_name against model_file_names (root-level only). No-match logged at DEBUG level (line 74), invisible at INFO.
  implication: When the match fails, there is ZERO visible feedback. User sees enqueue but never sees failure.

- timestamp: 2026-02-12T15:34:00Z
  checked: Controller.__check_webhook_imports() (controller.py:668-694)
  found: model_file_names = set(self.__model.get_file_names()) -- these are root-level names only. Model.get_file_names() returns self.__files.keys() which are root entries.
  implication: If webhook reports an inner file (child of a directory), it will NEVER match a root-level model name.

- timestamp: 2026-02-12T15:36:00Z
  checked: WebhookHandler._extract_sonarr_title() (webhook.py:84-113)
  found: Extracts os.path.basename(episodeFile.sourcePath). This is the individual episode filename from Sonarr's download directory.
  implication: For files inside a directory download (e.g., Season Pack), basename gives the INNER file name, not the directory name that SeedSync tracks.

- timestamp: 2026-02-12T15:38:00Z
  checked: ModelBuilder.build_model() (model_builder.py:109-136)
  found: Model is built from union of root-level keys: local_files.keys(), remote_files.keys(), lftp_statuses.keys(). Children are nested inside root ModelFile objects.
  implication: Model file names are directory/file names at the top level of the remote path. Individual files inside directories are NOT in get_file_names().

- timestamp: 2026-02-12T15:40:00Z
  checked: Controller.process() ordering (controller.py:191-206)
  found: __update_model() at line 202, __check_webhook_imports() at line 206. Model is current when webhooks are checked.
  implication: Ordering is correct. The issue is the matching logic, not timing.

## Resolution

root_cause: TWO issues combine to cause the bug:
  1. WebhookManager.process() only matched webhook file names against ROOT-LEVEL model file names. Sonarr's sourcePath basename gives the INNER filename (e.g., episode file inside a directory). For directory downloads, the model name is the directory but the webhook name is the file -- they never match.
  2. The no-match case logged at DEBUG level (webhook_manager.py:74), making failures completely invisible at the default INFO log level. The user sees "enqueued" but never sees the match failure.

fix: Two changes applied:
  1. Controller.__check_webhook_imports() now builds a comprehensive name-to-root lookup dict (name_to_root) that maps BOTH root-level names AND all child file names (via BFS traversal) back to their root parent name. This dict is passed to WebhookManager.process().
  2. WebhookManager.process() signature changed from Set[str] to Dict[str, str] (lowered name -> root name). The no-match log was upgraded from DEBUG to WARNING level with additional context (number of names checked).

verification: 545 unit tests passed (0 failures), including 5 new tests:
  - test_child_file_matches_returns_root_name (WebhookManager)
  - test_child_file_match_logs_root_name (WebhookManager)
  - test_webhook_name_lookup_includes_root_names (Controller)
  - test_webhook_name_lookup_includes_child_names (Controller)
  - test_webhook_name_lookup_includes_nested_child_names (Controller)

files_changed:
  - src/python/controller/webhook_manager.py
  - src/python/controller/controller.py
  - src/python/tests/unittests/test_controller/test_webhook_manager.py
  - src/python/tests/unittests/test_controller/test_controller_unit.py
