# Phase 122: Safety Acceptance and Logging Fixes - Research

**Researched:** 2026-10-21
**Domain:** (1) Python stdlib logging hierarchy repair for two Bottle web handlers + a decorator module; (2) live acceptance testing of already-shipped safety behaviors on a NAS Docker sandbox using synthetic HMAC-signed webhooks and a real multi-part RAR; (3) incident-record reconciliation against code that has already merged.
**Confidence:** HIGH (every code citation below was read directly from the current working tree; every NAS/sandbox/seedbox fact was confirmed live via read-only SSH during this research session; the GHCR digest-lookup command was executed and returned a real digest)

## Summary

This phase has no new library to adopt — it is 100% verification-and-small-fix work on existing code. LOG-01/LOG-02 are two isolated, mechanical logging-hierarchy fixes with an exact, already-established codebase pattern to copy (`ServerHandler(context)` → `self.logger = context.logger.getChild("ServerActionHandler")`, `src/python/web/handler/server.py:9-10`). SAFE-01 is a live-evidence-gathering exercise against code that has not been rebuilt since Phase 119/120 — the gate, early-credit, and auto-delete-rearm logic already exist and are already unit-tested; this phase's job is to drive them on a **running build** with synthetic material and capture log/state evidence. SAFE-02 is a desk-check against two incident records, one of whose fixes (extract-staging/auto-delete-rearm) **already shipped in 1.7.3** (commit `8142929`, PR #112) and has sat `awaiting_human_verify` ever since — SAFE-01's extraction scenario (D-07) is literally that record's own deferred human-verify step.

I independently confirmed on the NAS during this research session (read-only): the sandbox's current image pin (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a...`), that `webhook_secret` is currently **empty** and `webhook_require_secret = False` in the sandbox (so D-04's "correctly HMAC-signed" webhooks require temporarily setting a secret — and the config-set API **rejects an empty value**, so restoring it requires a file edit + container restart, not an API call), that `rar`/`7z`/`unrar`/`zip` are all installed on the seedbox (`nyx.usbx.me`, reachable key-auth from the NAS) with 5.4 TB free, that `unrar`/`7z` (no `rar`) are installed inside the `seedsyncarr-test` image, and that production's `/volume1/data/torrents/` no longer contains either Days-of-Hope or The Burbs (both already physically gone, even though `controller.persist`'s `downloaded`/`imported`/`imported_children` dicts — which read as permanent historical records, not live-presence indicators — still name them).

**One research-session incident to disclose:** a `grep -v -i "...\|api_key"` filter I used to redact a sandbox settings dump failed silently (the NAS's `grep` did not accept the `\|` alternation the way GNU grep does), and the sandbox's `sonarr_api_key` value was printed once into this session's tool output. That value is not reproduced anywhere in this document. It is a sandbox-only Sonarr key (not production, not a seedbox/NAS credential), but as a precaution the plan should offer the owner a one-line rotation of that key as a checkpoint item, and any future config dump during this phase should redact by checking **key presence/length**, never by piping full file contents through a hand-written filter.

**Primary recommendation:** Treat LOG-01/LOG-02 as one small Wave 0 PR (merge to `main` first, per D-01). Treat SAFE-01 as three sandbox sessions (import/credit scenarios, extraction, restart) built on synthetic files placed directly on the seedbox over the already-working SSH path, each wrapped in the same create-dir/`chmod 700`/trap-teardown discipline Phase 120 established (`120-teardown.sh`). Treat SAFE-02 as a desk audit that mostly needs the evidence SAFE-01 produces, plus the two read-only production checks already run during this research session.

## User Constraints (from CONTEXT.md)

<user_constraints>
### Locked Decisions

- **D-01:** Order: the LOG-01/LOG-02 fixes land on `main` first (PR merged, CI green). The SAFE-01 acceptance checks then run on the build of that merge commit. The evidence then covers the code 1.8.0 will ship (including Phase 121), and the newly visible log lines become part of it.
- **D-02:** Deploy that build to `seedsyncarr-test` **only**, as the CI-published `:dev` image **pinned by exact digest** (the merge commit's digest; the NAS cannot build images). Owner-approved exception to the "never `:dev`" rule, for the sandbox only. Before changing it, record the sandbox's current image pin (`ghcr.io/thejuran/seedsyncarr:1.7.6` today). Record the deployed digest in the evidence. At phase end, restore the original pin and verify the restore. Production (`seedsyncarr`, 1.7.6) is never touched.
- **D-03:** If any acceptance check fails: record the failure with evidence, diagnose the cause, and bring the owner the proposed fix and its scope **before** changing any code. Do not rebuild Phase 119 safeguards without the owner's go-ahead. SAFE-01 is not marked passed on a partial run.
- **D-04:** Import and auto-delete are driven by **synthetic material**: fake files in the sandbox's own seedbox folder (`remote_path = ~/v5test`), plus correctly HMAC-signed Sonarr-style `Download` webhooks posted to the sandbox's `/server/webhook/sonarr`, deliberately timed. No tracker grab, and the sandbox Sonarr library is not modified. The real Sonarr-queue completion gate ("Still downloading" hold, then release once Sonarr reports completion) is covered by citing Phase 120's live capture (`120-CAPTURE-NOTES.md`, `120-SON5-EVIDENCE.md`), not re-captured.
- **D-05:** A synthetic root has no Sonarr queue entry, so the gate holds it as "No matching queue entry" (Waiting). The **one-shot manual release** is the intended way to move it forward, which also exercises that safeguard. Use one release per root, and show that the release applies to that transfer only.
- **D-06:** Scenarios to exercise, each with recorded evidence:
  - (a) **Early per-episode credit:** a multi-file root where a child's import webhook arrives while sibling children are still transferring (the Days-of-Hope Case A shape). The child credit is recorded, the root is not committed early, and no auto-delete is armed before commit.
  - (b) **Arm-on-commit:** once the root commits as downloaded with full video coverage, auto-delete arms. After the 300 s delay the local copy is deleted (sandbox has `dry_run = False`).
  - (c) **Pending-notice revalidation / deferral paths:** webhooks for incomplete or not-yet-committed content are not lost, and are re-evaluated rather than dropped.
  - (d) **Restart persistence:** after one child is credited and while its siblings are still pending, restart `seedsyncarr-test` once. Confirm the credit survives the restart and the whole-folder delete still waits for full coverage.
  - (e) **Waiting hold + one-shot manual release** (see D-05).
- **D-07:** **Extraction:** use a **multi-part RAR of roughly 1 GB** (a single dummy `.mkv` inside, split into volumes), matching the Burbs incident shape. The sandbox already has `auto_extract = True` and `use_local_path_as_extract_path = True`. Evidence must show: while extraction runs, the release folder holds only the RAR volumes and the `.seedsyncarr-extracting/<root>/` staging dir grows; the UI/model never lists the staging dir; the full-size file appears in the release folder only at the end. Also exercise the **auto-delete re-arm path**: an import webhook accepted while the root is EXTRACTING produces `Auto-delete deferred for '<root>' (attempt n/24): ... EXTRACTING ...`, followed by `Auto-deleted local file '<root>'` after extraction completes.
- **D-08:** Clean up all synthetic material afterwards: the seedbox `~/v5test` probe files and archive, and the sandbox `/downloads` leftovers. Any temporary sandbox setting changes are restored on every exit path, the Phase 120 teardown discipline.
- **D-09:** **Read-only production inspection is allowed**: `ls`/`stat`, reading `/volume1/docker/seedsync/log/` and `controller.persist`, and GET-only Sonarr/Radarr API calls. No restarts, deletes, config edits, arr commands or writes of any kind on production. Use it to make the remaining-cleanup list factual, e.g. whether the Days of Hope root or The Burbs 77 GB local copy is still on disk. Note: the app-log clock is the NAS host clock + 1h.
- **D-10:** Each record gets a per-finding table: Done-group Case A and Case B; extract-staging Bug 1, Bug 2, and deep-review items D–G. Each row reads **"verified fixed (evidence)"** with a link or quote to the SAFE-01 evidence or test, or **"remaining operator cleanup"**, or (for D–G) **"deferred"**. Also fill the empty `fix:`/`verification:` fields in `done-group-no-auto-delete.md` with the Phase 119 plans and commits that delivered the fixes.
- **D-11:** Remaining production cleanup is handed to the owner as an **exact checklist**: path, size, what to delete or verify, and how to confirm it's done. **Nothing is performed on production in this phase.** Items stay open until the owner confirms.
- **D-12:** **Close rule:** a record is marked resolved and moved to `.planning/debug/resolved/` only when every finding is "verified fixed (evidence)" **and** the owner has confirmed all operator cleanup. Otherwise it stays in `.planning/debug/` with a status like `fixes_verified_cleanup_pending`. Deferred D–G items do not block closing, but each is carried by name to the ROADMAP backlog.
- **D-13:** **Logger scope: all four modules** that log through `logging.getLogger(__name__)` outside the app's `seedsyncarr` logger: `src/python/web/handler/webhook.py`, `src/python/web/handler/controller.py`, `src/python/web/handler/config.py`, `src/python/web/rate_limit.py`. Same cause, same fix. Attach them under the app logger (the context logger / `getChild` pattern used elsewhere, e.g. `web_app.py`), following whatever the codebase already does.
- **D-14:** Before merging, review every newly visible line in those modules and confirm none logs secrets, tokens, auth headers or webhook bodies. Includes the `logger.exception` in the Test Connection path in `config.py`, which must not expose credentials.
- **D-15:** Tests: **webhook** gets the required fail-before/pass-after regression (a Test event produces `<source> webhook test event received` at INFO under the app logger). The other three modules each get a lighter check that their lines reach the app logger.
- **D-16:** **"Dropped" covers every hold removal without proof:** (1) the prune path, a root that left the stability sweep / candidate set (this also covers a hold left behind after a one-shot manual release), and (2) the no-arr-enabled path in `CompletionGate._run` (step 2). "Cleared" is used **only** for the proof-based release in `_record` (verdict proven).
- **D-17:** **Exact wording** (all INFO, values through `sanitize_log_value`):
  - Release (unchanged): `Completion hold cleared for '<root>'`
  - Prune: `Completion hold dropped for '<root>' (no longer a queue candidate)`
  - No arr: `Completion hold dropped for '<root>' (no Sonarr/Radarr integration enabled)`
  Keeping "cleared" unchanged keeps existing log searches and Phase 120 evidence scripts valid.
- **D-18:** The LOG-02 regression test covers both paths: the proof-based release logs "cleared" and not "dropped"; the prune path (and the no-arr path) logs "dropped" and not "cleared". It fails against the current single-message `_clear_hold`.

### Claude's Discretion

- How the synthetic webhooks are built and signed (read the HMAC secret from the sandbox config inside a `umask 077` area; never commit or log it), and how fake files are sized and timed so children finish at different times.
- The RAR creation tooling and volume size (on the seedbox, or locally then uploaded), as long as the shape matches D-07.
- Evidence file layout (e.g. `122-SAFE01-EVIDENCE.md`). Use `<nas-tailscale-ip>`-style placeholders for addresses, and keep secrets out of committed files.
- Internal shape of the `_clear_hold` change (a reason parameter vs separate methods), provided D-17 wording and D-18 tests hold.
- Ordering of the live scenarios, and whether some share a single root.

### Deferred Ideas (OUT OF SCOPE)

- Extract-staging deep-review items D–G stay deferred. Carry each by name to the ROADMAP backlog during SAFE-02 reconciliation (D-12).
- A real-grab end-to-end run on the new build was considered and not chosen. Phase 126's REL-06 NAS smoke test (restart, transfer, integration, cleanup on the 1.8.0 digest) covers the release image.
- Not discussed: research-before-questions was enabled in config but skipped for this phase, because the decisions are project-specific verification choices, not ecosystem questions.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | Extraction, import and auto-delete checks pass on a running build, with recorded evidence (completes the Phase 119 verification whose browser half passed 2026-10-18) | §Architecture Patterns "Live acceptance architecture"; exact log-line wording for every D-06 scenario captured below (`Credited early import of...`, `Import credit for '<root>' applied on commit`, `Auto-delete deferred for '<root>' (attempt n/24)...`); sandbox facts (image pin, settings.cfg, seedbox tool availability) confirmed live this session |
| SAFE-02 | The Done-group and extract-staging incident records each distinguish verified fixes from remaining operator cleanup; neither closes solely because its code shipped | §SAFE-02 reconciliation map (which Phase 119 plan/commit fixed which finding); live read-only production check (`ls /volume1/data/torrents`, `controller.persist` read) already run this session, below |
| LOG-01 | Webhook handler INFO messages (e.g. "webhook test event received") appear in the app log | §Architecture Patterns "Logger-tree fix"; exact current code at `webhook.py:17`, `web_app_builder.py`, existing test pattern at `test_server_handler.py` |
| LOG-02 | The completion gate logs a distinct "dropped" message when a hold is pruned; "cleared" is logged only for a proof-based release | §Architecture Patterns "`_clear_hold` reason split"; exact 3 call sites with line numbers in `completion_gate.py`; existing test scaffolding in `test_completion_gate.py` (`GateTestBase.info()`) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Webhook/controller/config handler logging (LOG-01) | API / Backend (`web/handler/*.py`) | — | Module-level loggers detached from the app's `Context.logger` tree; pure backend wiring fix |
| Rate-limit logging (LOG-01, rate_limit.py) | API / Backend (`web/rate_limit.py`, cross-cutting decorator) | — | Shared decorator used by 4 handlers; needs an injectable logger, not its own tree |
| Completion-gate hold wording (LOG-02) | Backend controller (`controller/completion_gate.py`) | Model stream / UI ("Waiting" badge reads `hold_reason`, unaffected by this wording change) | Internal registry-lifecycle logging; no API or model contract changes |
| Import/auto-delete safety behaviors under test (SAFE-01) | Backend controller (`controller/controller.py`, `auto_delete_manager.py`, `completion_gate.py`) | API (`web/handler/webhook.py` inbound), Storage (seedbox via lftp, NAS local disk) | Already-implemented controller logic; this phase drives it, doesn't move it |
| Synthetic webhook construction & signing (SAFE-01) | Operator/agent tooling (ad hoc scripts on NAS/seedbox) | API (`/server/webhook/sonarr` HMAC verification in `webhook.py`) | Test harness, not shipped code |
| Incident record reconciliation (SAFE-02) | Planning/docs (`.planning/debug/*.md`) | — | No code tier; desk audit against already-existing evidence |

## Standard Stack

No new runtime dependencies. This phase is bug-fix + verification work on the existing stack.

| Tool | Version | Purpose |
|------|---------|---------|
| Python stdlib `logging` | 3.11 (image base) | LOG-01/LOG-02 — `Logger.getChild`, already the established pattern (`context.logger.getChild(...)`) |
| pytest | ^9.0.3 (+ pytest-timeout, pytest-cov) | Existing test runner; `unittest.TestCase` style |
| ruff | 0.15.22 in CI | Separate whole-tree lint gate (`ruff check src/python/`) |
| `rar`/`unrar`/`7z` | present on seedbox `nyx.usbx.me` (verified live, this session: all four of `rar`, `7z`, `unrar`, `zip` resolve via `which`) | Building the D-07 multi-part RAR test archive |
| `unrar`, `7z` (no `rar`) | present inside `seedsyncarr-test` image (verified live: `docker exec seedsyncarr-test which unrar 7z` → `/usr/bin/unrar`, `/usr/bin/7z`) | What `patoolib` actually shells out to inside the container for extraction |
| `curl` + a Python one-liner | any | Anonymous GHCR registry digest lookup (verified live, see Code Examples) |

**Installation:** nothing to install. If the research-time ruff/pytest versions drift before this phase executes, re-verify with `ruff --version` / `pytest --version` inside the poetry venv — don't assume the pinned-in-CI versions above are still current.

## Package Legitimacy Audit

Not applicable. This phase adds zero third-party packages (confirmed: no changes to `src/python/pyproject.toml` are implied by any of D-13 through D-18, and SAFE-01/SAFE-02 are evidence-gathering, not code-adding). `patool` is already a dependency (`pyproject.toml: "patool>=4.0.3"`) and unchanged.

## Architecture Patterns

### System Architecture Diagram — SAFE-01 live acceptance

```
 operator/agent (SSH key auth, already working, verified this session)
      │
      ├──▶ nyx.usbx.me (seedbox, jules1651)             rar/7z/unrar/zip present; 5.4 TB free on /home11
      │      • create ~/v5test/<SyntheticRoot>/child{1..n}.mkv (dd/truncate, staggered sizes)
      │      • create ~/v5test/<RarRoot>/ multi-volume .rar (~1 GB, one dummy .mkv inside)
      │
      └──▶ NAS (ssh nas, docker via `sudo /usr/local/bin/docker ...` only)
             │
             ├─ seedsyncarr-test (:8801 → container :8800)
             │    lftp ◀── mirrors ~/v5test (remote_path) ──▶ /downloads (= /volume1/data/v5test/torrents)
             │    AutoQueue (remote 90s / local 30s stability) ─▶ CompletionGate.evaluate()
             │         no queue entry (synthetic root, sonarr-v5 never grabbed it) ─▶ HOLD "no_queue_entry" ("Waiting")
             │         one-shot manual release: POST /server/command/queue/<file>?release_unverified=true
             │                                   or POST /server/command/bulk {action:queue, release_unverified:true}
             │    Controller.__check_webhook_imports ◀── POST /server/webhook/sonarr (HMAC-signed, D-04)
             │         per-child evidence (child DOWNLOADED, local==remote) → add_imported_child (early credit)
             │         root commits (local>=remote at root level) → "Import credit for '<root>' applied on commit"
             │                                                    → __schedule_auto_delete (300s)
             │    ExtractDispatch (auto_extract=True, use_local_path_as_extract_path=True → out_dir = /downloads)
             │         unrar into /downloads/.seedsyncarr-extracting/<root>/ → os.rename on success
             │    AutoDeleteManager.run_bfs_and_coverage → delete_local only after full video-child coverage
             │
             └─ sonarr-v5 (8990→8989) — NOT used as the source of truth for D-04/D-06/D-07
                  (real-queue gate release is cited from 120-CAPTURE-NOTES.md / 120-SON5-EVIDENCE.md, not re-captured)

 Evidence capture: ssh nas tail/grep /volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log
                    + GET /server/status, /server/files (model JSON) during each scenario
                    + stat/ls on /volume1/data/v5test/torrents and the seedbox path
```

### Recommended session structure (mirrors Phase 120's proven discipline)

```
<capture-dir>/                          # on NAS, e.g. /volume1/docker/v5test/results/safe01-<timestamp>/
├── teardown.sh                         # copied from 120-teardown.sh and extended for:
│                                        #   - webhook_secret restore (file edit + restart, see Pitfalls)
│                                        #   - seedbox ~/v5test synthetic dirs/archive removal
│                                        #   - sandbox /downloads leftover removal
├── state.env (0600)                    # HMAC secret handle (never the value), root names, timestamps
├── log-<scenario>.txt                  # grepped seedsyncarr.log windows per D-06/D-07 scenario
└── model-<scenario>.json               # GET /server/files snapshots (hold_reason, import_status, state)
```
Every script run as `trap '[ "$OK" = 1 ] || bash "$D/teardown.sh"' EXIT INT TERM HUP` with `trap 'exit 130' INT TERM HUP` set FIRST (Phase 120 found the combined trap does not exit on a signal — see `120-CAPTURE-NOTES.md` "Trap flaw found").

### Pattern 1: Logger-tree fix (LOG-01)

**What:** `webhook.py`, `controller.py`, `config.py` currently do `logger = logging.getLogger(__name__)` at module scope (e.g. `web.handler.webhook`), which has no ancestor relationship to the `seedsyncarr` logger that owns the actual `StreamHandler`/`RotatingFileHandler` pair (built once in `Seedsyncarr._create_logger(Constants.SERVICE_NAME, ...)`, `src/python/seedsyncarr.py:329-356`). Messages are emitted but reach no handler — not even stdout.

**The established pattern to copy exactly** (already used by `ServerHandler`, the one handler in this same package that is NOT broken):
```python
# Source: src/python/web/handler/server.py:8-11 (current working tree)
class ServerHandler(IHandler):
    def __init__(self, context: Context):
        self.logger = context.logger.getChild("ServerActionHandler")
```
and `WebAppBuilder` already has the `context` object available (`src/python/web/web_app_builder.py`); it simply never threads it into `ControllerHandler`/`ConfigHandler`/`WebhookHandler`:
```python
# Source: src/python/web/web_app_builder.py (current working tree)
self.controller_handler = ControllerHandler(controller, local_path=context.config.lftp.local_path)
self.config_handler = ConfigHandler(context.config)
self.webhook_handler = WebhookHandler(webhook_manager, context.config)
```
**Fix shape:** add `context: Context` as a constructor parameter to all three handler classes (import `from common import Context` — already imported this way in `server.py`), set `self.logger = context.logger.getChild("<ClassName>")`, replace every module-level `logger.xxx(...)` call in the class body with `self.logger.xxx(...)`, and update `WebAppBuilder` to pass `context` through. The module-level `logger = logging.getLogger(__name__)` line and `import logging` can be removed from each file once nothing references it.

**`rate_limit.py` is different** — it's a decorator factory, not a class, shared by `webhook.py`, `controller.py`, `config.py`, **and `status.py`** (out of scope; `status.py` has no logger of its own and isn't in D-13's list). Minimal, backward-compatible fix: add an optional `logger: Optional[logging.Logger] = None` parameter to `rate_limit()`; fall back to the existing module logger when not supplied (so `status.py`'s unmodified call site, and the existing `test_rate_limit.py` calls like `rate_limit(3, 60.0)(_handler)`, keep working unchanged). In-scope call sites pass `logger=self.logger`:
```python
# web/handler/webhook.py, inside add_routes, after the fix
web_app.add_post_handler(
    "/server/webhook/sonarr",
    self._make_require_secret_guard(
        rate_limit(max_requests=60, window_seconds=60.0, logger=self.logger)(self.__handle_sonarr_webhook)
    )
)
```

**Call-site inventory to update** (found by direct grep this session — plan tasks should touch every one):
- Production: `web/web_app_builder.py` (3 constructor calls)
- `tests/unittests/test_web/test_webhook_handler.py` — 11 `WebhookHandler(...)` constructions
- `tests/unittests/test_web/test_handler/test_config_handler.py` — 6 `ConfigHandler(...)` constructions
- `tests/unittests/test_web/test_handler/test_controller_handler.py` — 4 `ControllerHandler(...)` constructions
- `tests/unittests/test_sonarr5/test_sonarr5_system_status.py` — 1 `ConfigHandler(...)` construction
- `tests/integration/test_web/test_web_app.py` (`BaseTestWebApp`) — **no change needed**; it already constructs `WebAppBuilder(self.context, ...)` with `self.context.logger = <real root logger>`, and `root_logger.getChild("X")` resolves to a plain `logging.getLogger("X")`, which is sufficient for the integration harness's own attached `StreamHandler`.

**Existing test pattern to copy exactly** (`tests/unittests/test_web/test_handler/test_server_handler.py`):
```python
# Source: current working tree
def setUp(self):
    self.mock_context = MagicMock()
    self.handler = ServerHandler(self.mock_context)

def test_restart_logs_info(self):
    self.handler._ServerHandler__handle_action_restart()
    self.handler.logger.info.assert_called()
    log_message = self.handler.logger.info.call_args[0][0]
    self.assertIn("restart", log_message.lower())

def test_constructor_creates_child_logger(self):
    self.mock_context.logger.getChild.assert_called_once_with("ServerActionHandler")
```
This is the exact shape for D-15's "lighter check" on `controller.py`/`config.py`/`rate_limit.py`, and the fail-before/pass-after regression for `webhook.py`'s Test-event line. For webhook.py specifically, D-15 names the literal assertion: after the fix, posting `{"eventType": "Test"}` through `BaseTestWebApp`'s real Bottle stack (or directly through `WebhookHandler` with a `MagicMock` context) must produce exactly one `self.logger.info` call whose formatted message is `"Sonarr webhook test event received"` (or `"Radarr webhook test event received"`). Today (before the fix) this assertion cannot even be written meaningfully against the module logger — the RED state is naturally "the handler's logger attribute doesn't exist" or "`context.logger.getChild` was never called", which is itself the fail-before evidence D-15 wants.

**D-14 secret-safety review of every newly-reachable line** (every line is now reachable in the app log where it previously went nowhere — reviewed this session):
| File:line | Message | Secret risk |
|---|---|---|
| `webhook.py:56` | `"Webhook request rejected: webhook_require_secret is enabled but no webhook_secret is configured."` | None — no values interpolated |
| `webhook.py:98`, `:103` | missing/invalid `X-Webhook-Signature` header | None — doesn't log the header or secret value |
| `webhook.py:142` | `"{} webhook test event received".format(source)` | None — `source` is the literal `"Sonarr"`/`"Radarr"` constant |
| `webhook.py:149` | ignored event type, `sanitize_log_value(str(event_type))` | None — event type is a short enum-like string, sanitized |
| `webhook.py:161` | missing source path, logs `sanitize_log_value(release_title)` | Release title only (e.g. a torrent/episode name), not a credential; already sanitized |
| `controller.py:194` | path-traversal rejection, `repr(file_name)` | File name only; **inconsistent with the rest of the codebase** (uses `repr()` not `sanitize_log_value`) — pre-existing, out of this phase's scope, but worth a one-line note since D-13 touches this exact file anyway |
| `controller.py:352,386,428,434` | bulk-command counts/timings | None — counts and durations only |
| `config.py:198` | `logger.exception("Unexpected error testing %s connection", service_name)` | `service_name` is the literal `"Sonarr"`/`"Radarr"` constant. `logger.exception` logs `str(exc)` + a stack trace of **frames/lines**, not local variable values — Python's default traceback formatter does not print `api_key`/`url` contents. The `api_key` is sent via an HTTP header (`X-Api-Key`), never placed in the URL, so even a `requests` exception's own `str()` (which sometimes includes the request URL) would not surface it. **No change required**, but the plan should add one test that forces this exception path with a known test API-key string and asserts it's absent from the captured log, to pin this invariant rather than merely assert it from reading |
| `rate_limit.py:38` | `"Rate limit exceeded for %s", func.__name__` | `func.__name__` is the wrapped handler's Python function name (e.g. the name-mangled `_ConfigHandler__handle_set_config`), not user input |

**Conclusion: no secret-leak risk found in any of the four modules.** D-14's review can be satisfied by this table plus the one new pinning test on `config.py`'s exception path.

### Pattern 2: `_clear_hold` reason split (LOG-02)

**Exact current code** (`src/python/controller/completion_gate.py`):
```python
# Source: current working tree, line numbers as in repo today
def _run(self, candidates, prune):
    ...
    # (2) No arr enabled: the gate does not apply (D-16).
    if not targets:
        verdicts = {name: Verdict.not_required() for name in candidates}
        for name in list(self._holds):
            if prune or name in candidates:
                self._clear_hold(name)          # line 208 — NO-ARR PATH → must become "dropped"
        return verdicts
    ...
    if prune:
        for name in list(self._holds):
            if name not in candidates:
                self._clear_hold(name)          # line 236 — PRUNE PATH → must become "dropped"
    return verdicts

def _record(self, name, verdict, provisional, targets):
    ...
    if not verdict.held:
        if previous is not None:
            self._clear_hold(name)              # line 416 — PROOF-BASED RELEASE → stays "cleared"
        return
    ...

def _clear_hold(self, name: str):               # line 427 — the single logging point today
    if self._holds.pop(name, None) is not None:
        self.logger.info("Completion hold cleared for '%s'", sanitize_log_value(name))
```

**Recommended shape** (Claude's Discretion per CONTEXT, but this is the lowest-risk option — a `reason` parameter, not a second method, since all 3 call sites already call one private method and no test calls `_clear_hold` directly — confirmed by grep: zero test references to `_clear_hold`):
```python
_RELEASED = None  # sentinel meaning "proof-based release" (or just overload with Optional[str])

def _clear_hold(self, name: str, drop_reason: Optional[str] = None):
    if self._holds.pop(name, None) is not None:
        if drop_reason is None:
            self.logger.info("Completion hold cleared for '%s'", sanitize_log_value(name))
        else:
            self.logger.info("Completion hold dropped for '%s' (%s)", sanitize_log_value(name), drop_reason)
```
Call sites become:
```python
self._clear_hold(name, drop_reason="no Sonarr/Radarr integration enabled")   # line 208
self._clear_hold(name, drop_reason="no longer a queue candidate")            # line 236
self._clear_hold(name)                                                        # line 416, unchanged
```
This keeps D-17's wording exact, keeps `_record`'s call site a one-line no-op diff, and needs no new public API.

**Existing test infrastructure to extend** (`tests/unittests/test_controller/test_completion_gate.py`, `GateTestBase`):
```python
# Source: current working tree
class GateTestBase(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        ...
        self.gate = CompletionGate(self.context, self.client, clock=lambda: self.clock.now)

    def info(self) -> List[str]:
        return [_fmt(c) for c in self.logger.info.call_args_list]   # _fmt renders printf-style call args
```
Two existing tests currently assert "hold cleared" for paths that must become "dropped" after the fix — **these need updating, not just extending**, as part of D-18:
```python
# test_hold_cleared_when_no_longer_candidate (line 997) — PRUNE path.
# After the fix: rename and flip the assertion.
def test_hold_dropped_when_no_longer_candidate(self):
    _decide(self.gate, {ROOT: SIZE, "Other": 1})
    self.gate.evaluate({"Other": 1})
    self.assertEqual(1, sum(1 for line in self.info() if "hold dropped" in line))
    self.assertFalse(any("hold cleared" in line for line in self.info()))

# test_no_targets_clears_existing_holds (line 1038) — NO-ARR path.
# After the fix: rename and flip the assertion the same way, asserting
# "no Sonarr/Radarr integration enabled" appears in the dropped line.
```
`test_hold_cleared_when_proven` (line 989) stays unchanged — it is the D-18 "proof-based release still says cleared, never dropped" half of the regression. Together, the three tests (one unchanged, two flipped) are D-18's full fail-before/pass-after pair: against today's single-message `_clear_hold`, the two renamed tests fail immediately (the string "hold dropped" never appears today).

### Pattern 3: Synthetic HMAC-signed webhook (SAFE-01 / D-04)

The webhook handler verifies `X-Webhook-Signature: hex(HMAC-SHA256(secret, raw_body_bytes))` only when `general.webhook_secret` is non-empty (`webhook.py:_verify_hmac`, current working tree); it's a skip-if-empty check, not a fail-closed one. **Live-confirmed this session: the sandbox's `webhook_secret` is currently empty**, so D-04's "correctly HMAC-signed" requirement means the plan must temporarily set one.

```bash
# Template signing script (never print SECRET; read it from a 0600 var, never echoed)
SECRET="$(dd if=/dev/urandom bs=18 count=1 2>/dev/null | base64)"
# 1. Set it via the existing config API (value must be non-empty — see Pitfalls):
curl -s -X POST http://127.0.0.1:8801/server/config/set \
  -H "Content-Type: application/json" \
  -d "{\"section\":\"general\",\"key\":\"webhook_secret\",\"value\":\"${SECRET}\"}"
# 2. Build and sign a body (template fields verified live from Phase 120's real
#    sanitized Sonarr 5 fixture, src/python/tests/fixtures/sonarr5/webhook_download.json):
BODY='{"eventType":"Download","episodeFile":{"sourcePath":"/data/torrents/<SyntheticRoot>/child1.mkv"},"isUpgrade":false,"downloadId":"0000000000000000000000000000000000000001","instanceName":"Sonarr"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.*= //')
curl -s -X POST http://127.0.0.1:8801/server/webhook/sonarr \
  -H "Content-Type: application/json" -H "X-Webhook-Signature: ${SIG}" \
  -d "$BODY"
```
Only `eventType` and `episodeFile.sourcePath` (Sonarr) / `movieFile.sourcePath` (Radarr) are read by the handler (`_extract_sonarr_title`/`_extract_radarr_title`, current working tree) — the basename of `sourcePath` is matched against the model tree, so the rest of the fixture's fields (series/episode metadata) can be omitted entirely for synthetic bodies; only the basename needs to equal the actual synthetic child file's name on disk.

### Pattern 4: One-shot manual release (D-05)

Exact endpoint shapes (current working tree, `web/handler/controller.py`):
```
POST /server/command/queue/<file_name>?release_unverified=true          # single file
POST /server/command/bulk  {"action":"queue","files":[...],"release_unverified":true}   # bulk
```
`release_unverified` is accepted **only** for `action=queue` on the bulk route (400 otherwise) and is a one-shot `Controller.Command` flag, never persisted (`command_processor.py:193-194`, `controller.py:132-140`) — confirms D-05's "applies to that transfer only" is enforced by the existing code, not something this phase needs to build.

### GHCR `:dev` digest lookup (D-02)

Verified live this session (returned a real, current digest):
```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -I -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  "https://ghcr.io/v2/thejuran/seedsyncarr/manifests/dev" | grep -i docker-content-digest
# -> docker-content-digest: sha256:<...>
```
This matches the precedent already used for 1.7.5 in `119-REL03-EVIDENCE.md` ("the digest was read from the registry API with an anonymous pull token... `gh api .../packages/...` needs `read:packages`, not in the gh token, HTTP 403" — **confirmed still true this session**, same 403). Sequencing per D-01/D-02: merge the LOG-01/LOG-02 PR → confirm the `publish-docker-image-dev` CI job for that merge commit's run succeeded (`gh run list --workflow=ci.yml --branch main` filtered to the merge SHA, job name `Publish Docker Image (:dev)`) → THEN run the digest lookup (the `:dev` tag is mutable and always reflects the latest push to `main`, so lookup order matters) → pin `seedsyncarr-test`'s compose file to `ghcr.io/thejuran/seedsyncarr:dev@sha256:<digest>` → `sudo /usr/local/bin/docker compose -f /volume1/docker/v5test/docker-compose.yml pull seedsyncarr-test && ... up -d seedsyncarr-test` (mirrors the exact pattern in `119-REL03-EVIDENCE.md` lines ~563-567, substituting the dev digest for a release digest).

### Anti-Patterns to Avoid

- **Re-deriving the real-Sonarr-queue gate release behavior synthetically.** D-04 explicitly says cite Phase 120's capture, don't recreate it — a synthetic root has no queue entry by construction, so it can only ever demonstrate the "no_queue_entry" hold + manual-release path, never the queue-based PROVEN release.
- **Restoring `webhook_secret` via the config API.** `ConfigHandler.__handle_set_config` 400s on an empty value (`config.py`, "D-06: missing-or-empty value is 400" — an unrelated historical decision label in that file, not this phase's D-06). Restoring to empty requires editing `settings.cfg` directly and restarting the container — see Pitfalls.
- **Treating `controller.persist`'s `downloaded`/`imported`/`imported_children` dicts as live-presence indicators for SAFE-02.** They read as permanent historical bookkeeping (both Days-of-Hope and The Burbs are still listed even though neither exists on disk anymore, confirmed this session) — use `ls`/`stat` on the actual data path for "is it still there", not persist-dict membership.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sandbox teardown-on-exit discipline | A new ad hoc cleanup script from scratch | Copy/extend `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` and its trap pattern | Already handles Deluge-state idempotency, notification cleanup, and the signal-trap bug Phase 120 found and fixed (`ea8c85c`) |
| Webhook body capture/sink for comparing synthetic vs real shape | A new sink container | `.planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py` + the sanitized fixtures in `src/python/tests/fixtures/sonarr5/` | Already proven live against Sonarr 5; the real `webhook_download.json` fixture is the exact template for the synthetic body's field shape |
| GHCR digest discovery without `read:packages` scope | A new `gh` auth flow or token scope request | The anonymous registry bearer-token + `HEAD`/manifest `Accept` header trick, already proven in `119-REL03-EVIDENCE.md` and re-verified live this session | `gh api .../packages/...` reliably 403s with the current token; no need to request broader `gh` scopes for a research/verification phase |
| Deciding what counts as "evidence" for each D-06/D-07 scenario | Inventing new assertions | The exact log-line strings already in the codebase (quoted throughout this document) — e.g. `"Credited early import of '{}' in '{}' (root still transferring)"`, `"Import credit for '{}' applied on commit"`, `"Auto-delete deferred for '{}' (attempt {}/{}): {}; retrying in {} s"` | These are the actual production strings; evidence should quote them verbatim, not paraphrase |

**Key insight:** every piece of tooling this phase needs (teardown discipline, webhook sink, digest lookup, fixture shapes) was already built and proven during Phase 119/120. This phase's execution risk is almost entirely in *sequencing and timing* (making synthetic files finish transferring at different times, restoring a config value that the API won't let you set back to empty), not in missing tooling.

## Common Pitfalls

### Pitfall 1: `webhook_secret` cannot be restored to empty via the API

**What goes wrong:** The plan sets a temporary `webhook_secret` to exercise HMAC signing (D-04), then tries to restore it via `POST /server/config/set {"value": ""}` at teardown — and gets a 400.
**Why it happens:** `ConfigHandler.__handle_set_config` explicitly rejects `value is None or str(value) == ""` (current working tree) — this is pre-existing, intentional validation, not a bug to fix in this phase.
**How to avoid:** Restore by editing `/volume1/docker/v5test/seedsyncarr/settings.cfg` directly (`sed -i` the `webhook_secret = ` line back to empty) and then restarting `seedsyncarr-test` — since the in-memory `Config` object is the source of truth and is only loaded from the file at process start, the edit has no effect until a restart. Fold this restore into a restart you already need anyway: either D-06(d)'s restart-persistence scenario (if sequenced after the webhook-signing scenarios) or the D-02 end-of-phase sandbox-image-pin restore (`docker compose up -d` recreates the container, which also reloads `settings.cfg`).
**Warning signs:** `GET /server/config/get` still shows a non-empty `webhook_secret` after a file edit but before a restart.

### Pitfall 2: Rate limit budgets are shared and small

**What goes wrong:** The webhook endpoint is rate-limited to 60 requests / 60 s (`webhook.py` route registration), and bulk-command queue actions to 10/60 s (`controller.py:73`). A scenario sequence that fires many synthetic webhooks or many manual releases in quick succession (e.g., scripted retries while debugging) can self-inflict a 429 that looks like a product bug.
**Why it happens:** The rate limiter's window is per-decorated-function-instance (confirmed independent in `test_rate_limit.py`'s `TestRateLimitIndependentClosures`), not per-root, so it's a flat global budget across all synthetic scenarios run against one sandbox session.
**How to avoid:** Space out webhook posts and manual-release calls across scenarios; if a 429 is hit, it's self-inflicted test-harness pressure, not a regression — don't chase it as a bug.

### Pitfall 3: `controller.persist` dicts are historical, not live-presence

**What goes wrong:** Reading `downloaded_file_names`/`imported_file_names`-equivalent dicts (actual keys are `downloaded`, `extracted`, `stopped`, `imported`, `imported_children`, `absent_since` — confirmed live this session) and concluding a root is "still there" because it has an entry.
**Why it happens:** These dicts are append-only bookkeeping (e.g., to prevent a re-import from re-crediting), not reconciled against current disk state on every write.
**How to avoid:** For SAFE-02's "is it still on disk" question, use `ls`/`stat` against the actual data path (confirmed this session: `/volume1/data/torrents/` on production has **neither** Days-of-Hope nor The Burbs present, even though both still appear in all four persist dicts above).

### Pitfall 4: Synthetic roots never reach a queue-based PROVEN verdict

**What goes wrong:** Expecting a synthetic root (no real Sonarr/Radarr grab) to ever clear its hold through the normal queue-evidence path.
**Why it happens:** `CompletionGate` only proves a root when `ArrQueueClient` returns a matching queue record (`completion_gate.py` docstring); a file that was never grabbed through Sonarr/Radarr has no queue entry by construction, so it holds "no_queue_entry" forever.
**How to avoid:** This is expected and is exactly what D-05 wants exercised (the Waiting hold + one-shot manual release path) — don't try to engineer a fake queue entry; the real queue-based release is covered by citation per D-04.

### Pitfall 5: Restart wipes in-memory-only state, not persisted state

**What goes wrong:** Assuming a restart (D-06d) will lose everything and treating any surviving state as suspicious, or the opposite — assuming everything survives.
**Why it happens:** `imported_children`/`downloaded`/`imported` are written to `controller.persist` via `persist_callback` fired synchronously on any import-credit change (`controller.py` — "Persist outside every controller lock... a failure is logged; the periodic save retries"), so credits survive a restart. In-flight lftp transfer state and pending (`_PendingNotice`) webhook notices that haven't yet been credited are **not** persisted — they're rebuilt from a fresh remote/local scan after restart, and a pending notice older than its TTL (`_PENDING_NOTICE_TTL_SECS = 6h`) or past `_PENDING_NOTICE_MAX` (1000) is already-designed to be discarded, not a restart-specific gap.
**How to avoid:** For D-06(d), restart only after a child has actually been credited (i.e., `add_imported_child` has already fired and persisted — confirmed by a log line or persist read before restarting), not mid-transfer.

### Pitfall 6: app-log clock is NAS host clock + 1 h

**What goes wrong:** Comparing a log timestamp directly against `stat` output or Sonarr's own API timestamps and concluding an off-by-one-hour discrepancy is a bug.
**Why it happens:** Documented and reconfirmed across Phase 119/120 evidence (`119-REL03-EVIDENCE.md`'s "Days of Hope... app-log time is EDT; NAS host clock/mtimes are -05, app = host + 1h"; `120-CAPTURE-NOTES.md` throughout).
**How to avoid:** State both clocks explicitly in every evidence excerpt (as 119/120's evidence files already do), and always compute windows from one consistent clock, converting once at the start of analysis.

### Pitfall 7: Hand-written redaction filters can fail silently on the NAS's grep

**What goes wrong:** A `grep -v -i "secret\|token\|...` filter intended to strip a settings dump before printing can silently no-op if the remote shell's `grep` doesn't support the escaped-alternation form the way GNU grep does — and the full unredacted line gets printed into tool output / evidence files.
**Why it happens:** Confirmed this session: a filter of exactly this shape failed on the NAS and printed `sonarr_api_key`'s value once into this research transcript (not reproduced here; flagged for owner rotation as a precaution).
**How to avoid:** Prefer checking *presence/length* of a secret field over printing filtered file contents (e.g. `awk -F"= " '/^webhook_secret/{print length($2)}' settings.cfg` — proven to work correctly this session) and never trust a redaction filter you haven't verified against a known-bad line first.

## Code Examples

### Verified: sandbox current state (read live this session)

```
Image pin:        ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
Compose file:      /volume1/docker/v5test/docker-compose.yml  (separate project "v5test", NOT the main stack's compose file)
webhook_secret:     empty (length 0)
webhook_require_secret: False
auto_extract:       True        remote_stability_seconds: 90    local_stability_seconds: 30
AutoDelete:          enabled=True  dry_run=False  delay_seconds=300
Lftp remote_path:    /home/jules1651/v5test   (= ~/v5test)   local_path: /downloads
extract_path:        /tmp (IGNORED — use_local_path_as_extract_path=True means extraction target is local_path, i.e. /downloads)
Sonarr:              enabled=True  url=http://sonarr-v5:8989
Radarr:              enabled=False
```

### Verified: logger-tree root construction (why the fix works)

```python
# Source: src/python/seedsyncarr.py:329-356 (current working tree)
@staticmethod
def _create_logger(name: str, debug: bool, logdir) -> logging.Logger:
    logger = logging.getLogger(name)   # name = Constants.SERVICE_NAME = "seedsyncarr"
    ...
    handlers = [logging.StreamHandler(sys.stdout)]
    if logdir is not None:
        handlers.append(RotatingFileHandler("{}/{}.log".format(logdir, name), ...))
    for handler in handlers:
        logger.addHandler(handler)
    return logger
```
`Context.logger` is this `"seedsyncarr"` logger. `context.logger.getChild("WebhookHandler")` returns `logging.getLogger("seedsyncarr.WebhookHandler")`, a true descendant that **propagates up** to the handlers attached above. The current `logging.getLogger(__name__)` (`"web.handler.webhook"`) has no such ancestor and propagates only to the root logger, which has no handlers attached in this app — hence the lines vanish, matching Phase 120's live finding of 0 occurrences in the sandbox log history.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single `_clear_hold` message for every hold-removal cause | Reason-qualified "cleared" (proof) vs "dropped" (prune/no-arr) | This phase (LOG-02) | Evidence review (this phase's own SAFE-01 work, and any future incident investigation) can trust the word "cleared" to mean an actual release |
| Module-level `logging.getLogger(__name__)` in 3 handlers + 1 decorator | `context.logger.getChild(ClassName)`, matching `ServerHandler`/`WebApp`/`CompletionGate`/`WebhookManager`/`FileOperationManager` (all of which already use this pattern) | This phase (LOG-01) | The 4 fixed modules become the last stragglers off the module-logger pattern in `web/handler/` and `web/` — after this phase, `status.py` is the only remaining handler with no logger at all (it has nothing to log, so this is fine, not a gap) |
| Extraction wrote directly into the release folder during unrar | Stage into `.seedsyncarr-extracting/<root>/`, publish via `os.rename` only on success | 1.7.3 (PR #112, commit `8142929`) — **already shipped**, never live-verified | SAFE-01's D-07 scenario is this fix's first-ever live verification, 1+ month after it merged |
| A skipped auto-delete (e.g., EXTRACTING) was never retried | Bounded re-arm (`_AUTO_DELETE_MAX_REARMS = 24`, ~2h at 300s) with per-attempt logging | 1.7.3 (same PR #112) — **already shipped**, never live-verified | Same as above; D-07's second half |

**Nothing is deprecated by this phase** — LOG-01/LOG-02 are additive wording/wiring fixes, and SAFE-01/SAFE-02 touch no production code path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rate_limit()`'s optional `logger` parameter (defaulting to the module logger) is the lowest-risk way to bring it under D-13's scope without breaking `status.py` or existing `test_rate_limit.py` calls | Architecture Patterns, Pattern 1 | If the planner instead makes `logger` required, every `rate_limit(...)` call site (including `status.py`, out of scope) needs updating — larger diff than D-13 implies |
| A2 | Adding a `context: Context` parameter to `ControllerHandler`/`ConfigHandler`/`WebhookHandler` (rather than passing `context.logger` alone, or restructuring to take only a logger) is the intended minimal fix, matching `ServerHandler`'s existing signature shape | Architecture Patterns, Pattern 1 | A reviewer could prefer injecting a pre-built child logger directly instead of the whole `Context` object; functionally equivalent, but changes the constructor signature shape the plan should pick one way |
| A3 | `config.py`'s `logger.exception` at line 198 leaks no secrets because Python's default traceback formatting does not print local variable values and the API key travels only in a header, never the URL | Architecture Patterns, Pattern 1 (D-14 table) | If a future `requests` version or an unusual exception type's `__str__` includes header contents, this would be wrong — mitigated by recommending one pinning test rather than relying on the claim alone |

**If this table is empty:** N/A — three assumptions logged above, all low-risk and each with a stated mitigation already folded into the recommended plan shape.

## Open Questions

1. **Exact timing mechanism for "a child webhook arrives while siblings still transfer" (D-06a)**
   - What we know: `num_max_parallel_files_per_download = 4` in the sandbox config allows up to 4 files of one root to transfer in parallel within one lftp `mirror` job; differently-sized children finish at different times within that one job (this is exactly the original Days-of-Hope incident's mechanics — 4 mkv parts of different sizes).
   - What's unclear: whether size-based staggering alone (e.g., child1 = 10 MB, children 2-4 = 300-800 MB each) reliably produces a wide-enough gap on the sandbox's actual seedbox-to-NAS throughput for an agent to reliably fire the webhook for child1 before the root-level local+remote scan has caught up with children 2-4, or whether a belt-and-suspenders approach (write child1 to the seedbox first via SSH, wait for one full scan+transfer cycle to pick it up and go DOWNLOADED, confirm via `GET /server/files`, THEN write children 2-4 and post child1's webhook before they finish) is needed for a deterministic result.
   - Recommendation: plan for the belt-and-suspenders (staged SSH writes + confirm-via-API) approach as primary, since it removes timing-race uncertainty entirely; the size-staggering approach as a secondary/faster option if the first session shows the controller's scan cadence (local 10s / remote 30s in the config, though sandbox shows 90s/30s stability windows — see Code Examples) makes staging unnecessary.

2. **Whether to rotate the sandbox `sonarr_api_key` exposed during this research session**
   - What we know: the value was printed once into this session's tool output due to a redaction-filter failure (Pitfall 7); it is a sandbox-only (not production) Sonarr key.
   - What's unclear: whether the owner considers a sandbox-only key exposure (in a Claude Code tool-output transcript, not a public artifact) worth a rotation checkpoint, given the low blast radius.
   - Recommendation: surface it to the owner as a one-line checkpoint during plan execution (not a blocker) — "rotate `sonarr-v5`'s API key in the sandbox as a precaution; no other system uses it."

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SSH to NAS (`ssh nas`) | All SAFE-01/SAFE-02 work | ✓ (verified live) | key auth, passwordless | — |
| `sudo /usr/local/bin/docker` on NAS | Container inspect/compose/exec | ✓ (verified live) | — | — |
| SSH NAS → seedbox (`nyx.usbx.me`, user `jules1651`) | Placing synthetic files/archives | ✓ (verified live, key auth, passwordless) | — | — |
| `rar`/`7z`/`unrar`/`zip` on seedbox | Building the D-07 RAR archive | ✓ all four (verified live via `which`) | — | — |
| `unrar`/`7z` inside `seedsyncarr-test` image | Confirming what the app actually shells out to | ✓ both (verified live via `docker exec ... which`); no `rar` binary in the image (not needed — app only extracts, never creates archives) | — | — |
| GHCR anonymous digest lookup | D-02 digest pin | ✓ (verified live, returned a real digest for `:dev`) | Docker Registry v2 API | — |
| `gh api .../packages/...` (GHCR via gh CLI) | Alternative digest lookup | ✗ (confirmed live: HTTP 403, token lacks `read:packages`, same as 119-REL03-EVIDENCE.md's prior finding) | — | Anonymous registry bearer-token method above (already the established fallback) |
| Seedbox disk space (`/home11`) | ~1 GB synthetic material | ✓ (verified live: 5.4 TB free of 11 TB) | — | — |

**Missing dependencies with no fallback:** none found.
**Missing dependencies with fallback:** `gh api` package digest lookup → anonymous registry API (already proven, no new tooling needed).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ^9.0.3 (unittest.TestCase style), pytest-timeout (60s/test), pytest-cov (fail_under = 88, informational — CI runs no `--cov`) |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_handler/test_controller_handler.py tests/unittests/test_web/test_rate_limit.py tests/unittests/test_controller/test_completion_gate.py -q -p no:cacheprovider` |
| Full suite command | `cd src/python && poetry run pytest tests/unittests -p no:cacheprovider -q` followed by `ruff check src/python/` (separate CI gate — run both) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | Webhook Test event logs at INFO under the app logger, fails before / passes after | unit | `pytest tests/unittests/test_web/test_webhook_handler.py -k test_event -x` (new assertion) | ❌ Wave 0 (assertion to add) |
| LOG-01 | `controller.py`/`config.py`/`rate_limit.py` lines reach `context.logger.getChild(...)` | unit | `pytest tests/unittests/test_web/test_handler/test_controller_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_rate_limit.py -q` | ❌ Wave 0 (new lighter checks) |
| LOG-02 | Proof-based release logs "cleared", never "dropped" | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k test_hold_cleared_when_proven -x` | ✅ exists, needs no change |
| LOG-02 | Prune / no-arr paths log "dropped", never "cleared" (fail-before/pass-after) | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k "test_hold_dropped_when_no_longer_candidate or test_no_targets" -x` | ❌ Wave 0 (rename+flip 2 existing tests) |
| SAFE-01 | All D-06/D-07 scenarios pass on the running sandbox build | live-evidence (manual, not automatable) | N/A — see `## Code Examples` / Architecture Patterns for the live commands; evidence file is the artifact | N/A — inherently live |
| SAFE-02 | Incident records reconciled with per-finding status | manual desk-check | N/A — depends on SAFE-01 evidence + this session's live production `ls`/persist read (already captured above) | N/A |

### Sampling Rate
- **Per task commit (LOG-01/LOG-02):** quick run command above
- **Per wave merge:** full suite command above
- **Phase gate:** full suite green before `/bm:verify-work`; SAFE-01 evidence file complete and SAFE-02 records updated before phase close

### Wave 0 Gaps
- [ ] `tests/unittests/test_web/test_webhook_handler.py` — add the fail-before/pass-after Test-event-at-INFO assertion (D-15)
- [ ] `tests/unittests/test_web/test_handler/test_controller_handler.py`, `test_config_handler.py` — add lighter "logs reach `self.logger`" checks (D-15); update all constructor call sites for the new `context` parameter
- [ ] `tests/unittests/test_web/test_rate_limit.py` — add a check that a supplied `logger` kwarg is used instead of the module default (existing calls stay unchanged, since the param is optional)
- [ ] `tests/unittests/test_controller/test_completion_gate.py` — rename+flip `test_hold_cleared_when_no_longer_candidate` and `test_no_targets_clears_existing_holds` to assert "dropped" wording (D-18); `test_hold_cleared_when_proven` needs no change
- [ ] `tests/unittests/test_sonarr5/test_sonarr5_system_status.py` — update its one `ConfigHandler(...)` call site for the new `context` parameter (otherwise it breaks, not a new test)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes (webhook endpoints) | Existing HMAC-SHA256 signature (`hmac.compare_digest`, constant-time) + fail-closed `require_secret` guard — unchanged by this phase |
| V5 Input Validation | yes (webhook bodies, config set) | Existing `sanitize_log_value` (CWE-117 log-injection guard) on every webhook-supplied value before logging — this phase's LOG-01 fix makes previously-invisible lines visible, so D-14's review (above) is the control that matters here |
| V6 Cryptography | yes (HMAC signing for synthetic webhooks) | `hmac.new(secret, body, hashlib.sha256)` — existing, unchanged; this phase's test harness reuses the same primitive via `openssl dgst -sha256 -hmac` for signing synthetic requests, never a hand-rolled MAC |
| V7 Error Handling / Logging | yes — this is the core of LOG-01/LOG-02 | Never log secrets/tokens/auth headers (CLAUDE.md, absolute rule); confirmed via the D-14 table above that none of the 4 modules' newly-reachable lines interpolate a secret value |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Log injection via webhook-supplied strings (event type, release title, file name) now reaching a real log sink for the first time (LOG-01) | Tampering | Already mitigated: every interpolated value in the 4 modules' log lines is either a fixed literal (`"Sonarr"`/`"Radarr"`) or passed through `sanitize_log_value` (webhook.py) — confirmed in the D-14 table; no new sanitization needed |
| Misleading evidence from an ambiguous log message during incident response (LOG-02's actual root cause) | Repudiation (an operator can't trust what the log claims happened) | The "cleared" vs "dropped" wording split directly addresses this — this phase's own fix is the mitigation |
| Secret exposure via an imperfect ad hoc redaction filter during live NAS inspection (found this session, Pitfall 7) | Information Disclosure | Prefer presence/length checks over content-filtering when inspecting config files live; never assume a one-off `grep` filter is correct without testing it against a known secret-bearing line first |

## Sources

### Primary (HIGH confidence — read directly from the current working tree or confirmed live via SSH/curl this session)
- `src/python/web/handler/webhook.py`, `controller.py`, `config.py`, `rate_limit.py`, `server.py`, `web_app.py`, `web_app_builder.py` — full read, current working tree
- `src/python/controller/completion_gate.py`, `controller.py` (lines 650-922, 1068-1130), `webhook_manager.py` — full/targeted read, current working tree
- `src/python/common/context.py`, `config.py`, `seedsyncarr.py` (logger construction, lines 329-356) — targeted read
- `src/python/tests/unittests/test_web/test_handler/test_server_handler.py`, `test_webhook_handler.py`, `test_rate_limit.py`, `test_controller/test_completion_gate.py` — full/targeted read for test patterns
- `.planning/debug/done-group-no-auto-delete.md`, `extract-staging-autodel-rearm.md` — full read
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-VERIFICATION.md`, `119-HUMAN-UAT.md`, `119-REL03-EVIDENCE.md`, `119-04-SUMMARY.md`, `119-05-SUMMARY.md`, `119-06-SUMMARY.md` — full/targeted read
- `.planning/phases/120-sonarr-5-compatibility/120-CAPTURE-NOTES.md`, `120-RESEARCH.md`, `deferred-items.md`, `src/python/tests/fixtures/sonarr5/webhook_download.json` + `manifest.json` — full read
- `git log -- src/python/controller/extract/dispatch.py` → commit `8142929` (PR #112, shipped in 1.7.3) — confirmed the extract-staging fix already shipped
- Live NAS/seedbox session (`ssh nas`, `ssh nas 'ssh nyx.usbx.me ...'`): image pins, compose file location, settings.cfg contents (secrets excluded), seedbox tool availability and disk space, production `/volume1/data/torrents/` and `controller.persist` contents, GHCR anonymous digest lookup (both from this machine and reconfirmed concept via NAS), `gh auth status` / `gh api packages` 403
- `.github/workflows/ci.yml` (`publish-docker-image-dev` job, lines 370-409) — full read

### Secondary (MEDIUM confidence)
- None — every claim in this document was either read directly from source or confirmed live.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tooling confirmed present live (rar/7z/unrar on seedbox and in-container, GHCR digest lookup executed successfully)
- Architecture (LOG-01/LOG-02 fix shape): HIGH — exact existing pattern (`ServerHandler`) copied directly from the current working tree; exact call-site line numbers confirmed by direct grep
- SAFE-01 live acceptance mechanics: HIGH for sandbox facts (all confirmed live this session) / MEDIUM for the exact timing approach to stagger synthetic child completion (Open Question 1 — recommend the belt-and-suspenders approach as primary)
- SAFE-02 reconciliation: HIGH — Phase 119 plan-to-fix mapping confirmed by reading plan/summary frontmatter directly; production disk state confirmed live this session

**Research date:** 2026-10-21
**Valid until:** 14 days (sandbox state — image pins, log contents, persist contents — is live infrastructure that can change; the code-level findings (logger tree, `_clear_hold`, extract-staging fix history) are stable until the next phase touches these files)
