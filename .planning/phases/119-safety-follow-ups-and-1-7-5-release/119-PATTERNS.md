# Phase 119: Safety Follow-ups and 1.7.5 Release - Pattern Map

**Mapped:** 2026-10-14
**Files analyzed:** 44 (new + modified, incl. tests/docs/CI)
**Analogs found:** 42 / 44

Scope note: CONTEXT D-16..D-21 supersede RESEARCH Open Questions 1-6. In particular:
- **D-16:** with no arr enabled the gate is bypassed and stability gating applies.
- **D-17:** a responding arr with a strong `outputPath`-basename match and all-completed records proves the item even when the other arr is down. This replaces RESEARCH Assumption A3 "strict".
- **D-19:** remove the checkbox.
- **D-20:** persist the credit immediately.
- **D-21:** roll in #93, #123 and #124.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/controller/arr_queue.py` (NEW) | service (HTTP client) | request-response | `src/python/web/handler/config.py` `_test_arr_connection` (L133-202) | role-match (same API, same headers) |
| `src/python/controller/completion_gate.py` (NEW) | service (cache + verdict + hold registry) | transform / polling w/ backoff | `src/python/controller/lftp_manager.py` (breaker L34-42, L167-198) + `controller/webhook_manager.py` (class shape L17-35) | partial (no existing arr-state cache) |
| `src/python/controller/controller.py` | coordinator | event-driven (cycle) | self: ctor wiring L218-255; webhook gate L553-678; auto-delete L750-897 | exact (in-file) |
| `src/python/controller/auto_queue.py` | service | batch sweep | self L283-337 | exact |
| `src/python/controller/command_processor.py` | controller (command dispatch) | request-response | self `_handle_queue` L104-149 | exact |
| `src/python/controller/lftp_manager.py` | service | request-response | self L74, L127-144, L200-212 | exact |
| `src/python/controller/scan_manager.py` | service | file-I/O | self L46-53 | exact |
| `src/python/controller/model_builder.py` | builder | transform | `set_submitted_files` L91-101, `_set_initial_state` L228-243 | exact |
| `src/python/controller/model_pipeline.py` | pipeline | transform | `feed_model_builder` L147-170 | exact |
| `src/python/model/file.py` | model | CRUD | `import_status` attr L54 + property L237-245 | exact |
| `src/python/web/serialize/serialize_model.py` | serializer | transform | `import_status` key L59-63, L85-86 | exact |
| `src/python/web/handler/controller.py` | route handler | request-response | `_dispatch_command` L76-105; bulk validation L213-280; `_process_bulk_commands` L349-353 | exact |
| `src/python/lftp/lftp.py` | wrapper (pexpect stream) | streaming | self `__run_command` L114-157, `status` L304-335 | exact |
| `src/python/seedsyncarr.py` | app entry (persist loop) | file-I/O | `persist()` L254-259, loop L183-191 | exact |
| `src/python/pyproject.toml` | config | build | self L36-37 (`packages = ["."]`) | exact |
| `.github/workflows/ci.yml` | config (CI) | batch | `lint-python` L73-94 + `publish-pypi` L307-335 | exact |
| `src/angular/src/app/services/files/model-file.ts` | model | transform | `import_status` L18/L40/L59/L84/L123-137 | exact |
| `src/angular/src/app/services/files/view-file.ts` | view-model | transform | `importStatus` L30/L55/L83 | exact |
| `src/angular/src/app/services/files/view-file.service.ts` | service | transform | L418-449 (`new ViewFile({...})`, `mapImportStatus`) | exact |
| `src/angular/src/app/pages/files/transfer-row.component.ts` | component | render | `isSkippedRemote` override L72-90 | exact |
| `src/angular/src/app/pages/files/transfer-row.component.html` | template | render | `file-meta` L8-12, badge L14-20 | exact |
| `src/angular/src/app/services/files/bulk-action-dispatcher.service.ts` | service | request-response + modal | `confirmAndDispatchDeleteLocal` L64-82, `_dispatch` L102-131 | exact |
| `src/angular/src/app/services/server/bulk-command.service.ts` | HTTP service | request-response | `executeBulkAction` L116-151 | exact |
| `src/angular/src/app/common/localization.ts` | constants | n/a | `Modal` L19-47 | exact |
| `src/angular/src/app/pages/settings/options-list.ts` | config (UI) | n/a | remove entry L139-144 | exact |
| `src/e2e/tests/fixtures/seed-state.ts` | test fixture | request-response | `ENDPOINT.queue` L17, `queueFile` L79-80 | exact |
| `docs/CONFIGURATION.md`, `src/python/docs/configuration.md` | docs | n/a | existing `use_temp_file` entries | exact |
| `CHANGELOG.md`, `release-notes.md`, `package.json`, `src/angular/package.json`, `package-lock.json` | release metadata | n/a | `## [1.7.4]` entry; `scripts/verify-release-metadata.mjs` | exact |
| `src/angular/package-lock.json` (#93), `src/python/poetry.lock` + `pyproject.toml` (#123 cryptography, #124 pytz) | deps | n/a | Dependabot PR diffs | exact |
| `tests/unittests/test_controller/test_arr_queue.py` (NEW) | test | request-response | `tests/unittests/test_web/test_handler/test_config_handler.py` L198-265 | role-match |
| `tests/unittests/test_controller/test_completion_gate.py` (NEW) | test | transform | `test_lftp_manager.py` (breaker tests) | partial |
| `tests/unittests/test_lftp/test_lftp_resync.py` (NEW) | test | streaming | `tests/unittests/test_lftp/test_lftp_status_contract.py` L57-130 | exact |
| `tests/unittests/test_controller/test_import_credit.py` (NEW) | test | event-driven | `tests/unittests/test_controller/test_import_ambiguity.py` L1-40 | exact |
| `tests/unittests/test_controller/base.py` | test base | n/a | self L17-58 (patcher list) | exact |
| `test_auto_queue.py`, `test_auto_delete_rearm.py`, `test_lftp_manager.py`, `test_scan_manager.py`, `test_model_builder.py`, `test_serialize_model.py`, `test_controller_handler.py`, `test_controller_unit.py` (extend) | tests | — | self | exact |
| Angular specs: `transfer-row.component.spec.ts`, `bulk-action-dispatcher.service.spec.ts`, `view-file.service.spec.ts`, `model-file.spec.ts`, config specs (`use_temp_file`) | tests | — | self | exact |
| CI `verify-python-package` inline member-path checker | script | batch | none | **no analog** |
| Immediate-persist callback (D-20) wiring | callback | file-I/O | `force_local_scan_callback` injection (controller.py L153-158) | partial |

---

## Pattern Assignments

### `src/python/controller/arr_queue.py` (NEW: service, request-response)

**Analog:** `src/python/web/handler/config.py` L133-202 (`_test_arr_connection`)

**Copy:** the request shape, the header auth, `allow_redirects=False` and the exception ladder. **Do not copy:**
- the `_validate_url` SSRF call (L146-152). It rejects private IPs, and the NAS arrs are on 192.168.x (RESEARCH Pitfall 4). Keep only an `http`/`https` scheme check (L64-65 logic).
- the HTTPResponse building.

**Request pattern** (L154-163):
```python
url = raw_url.rstrip("/")
response = requests.get(
    "{}/api/v3/system/status".format(url),
    headers={"X-Api-Key": api_key},
    timeout=10,
    allow_redirects=False
)
```
→ New endpoint: `/api/v3/queue/details`. Timeout `(3.05, 10)`. Cap the response size at about 8 MB.

**Error ladder** (L187-202). This is the shape to mirror. In the new module, every branch returns "unavailable" (`None`) instead of an HTTP body:
```python
except requests.ConnectionError: ...
except requests.Timeout: ...
except Exception:
    logger.exception("Unexpected error testing %s connection", service_name)
```
In the new module, log **exception type name only**, never `logger.exception` (traceback could include URL/headers). Per user CLAUDE.md, never log the key, headers, body or URL.

**Config access** (L204-216):
```python
self.__config.sonarr.sonarr_url, self.__config.sonarr.sonarr_api_key
self.__config.radarr.radarr_url, self.__config.radarr.radarr_api_key
```
`common/config.py` L338-358: `Sonarr`/`Radarr` sections. The api_key is declared with `secret=True` (L341, L352), and `enabled` is a property of the same section.

**Logger/ctor shape:** copy `WebhookManager.__init__` (`controller/webhook_manager.py` L31-34):
```python
def __init__(self, context: Context):
    self.__context = context
    self.logger = context.logger.getChild("WebhookManager")
```

---

### `src/python/controller/completion_gate.py` (NEW: service, polling + cache + backoff)

**Analog A (backoff on the monotonic clock):** `controller/lftp_manager.py` L34-42 and L167-198
```python
STATUS_STALL_THRESHOLD_SECS = 30.0
STATUS_BACKOFF_SECS = 60.0
...
start = time.monotonic()
if start < self.__status_backoff_until:
    return None
...
self.__status_backoff_until = time.monotonic() + LftpManager.STATUS_BACKOFF_SECS
```
For each arr, use `next_fetch_at` plus a backoff step of 30→60→120→240→300 s cap, reset on success (D-13). Constants go at class level, as in LftpManager.

**Analog B (log on transition, not every cycle):** `AutoQueue.process` debug-vs-info discipline (`auto_queue.py` L236-246), together with the D-11 rule. Keep `holds: Dict[str, str]`, and INFO-log only on start, reason change and clear.

**Sanitize names in logs:** `from common import sanitize_log_value`, as everywhere (e.g. `webhook_manager.py` L4, L12).

**Verdict algorithm:** take it from RESEARCH §"Exact matching rule" and Pattern 1, **amended by D-16/D-17**:
- No arr enabled → bypass. Return a "not required" verdict, and stability gating alone applies.
- A responding arr may prove the item on its own, through a strong `outputPath`-basename match with every record `completed` and `sizeleft == 0`, even if the other enabled arr is unavailable.
- A "{Arr} unavailable" hold applies only when no available arr proves the item.

**Construction location:** `Controller.__init__`, next to the other managers, so that `patch('controller.controller.CompletionGate')` works (D-05 comment, controller.py L218-226).

---

### `src/python/controller/controller.py` (MODIFIED)

**1. Construct the gate (and ArrQueueClient)** next to the other collaborators. Analog L218-226:
```python
# Command dispatch collaborator — receives already-constructed manager instances
# (D-05: mock.patch targets resolve against controller.controller where they are
# constructed; CommandProcessor constructs none of them)
self.__command_processor = CommandProcessor(
    lftp_manager=self.__lftp_manager,
    file_op_manager=self.__file_op_manager,
    persist=self.__persist,
    logger=self.logger,
)
```
Add `completion_gate=self.__completion_gate` to the CommandProcessor kwargs, and import at the top beside L9-17 (`from .completion_gate import CompletionGate`).

**2. Public verdict API for AutoQueue** (same-thread). Analog is the simple query methods `is_file_stopped`/`is_file_downloaded` (L324-352). Add `evaluate_completion(names)` / `completion_verdict(name)`.

**3. `Command` gains `release_unverified`.** Analog L100-105:
```python
def __init__(self, action: Action, filename: str,
             origin: "Controller.Command.Origin" = None):
    self.action = action
    self.filename = filename
    self.origin = origin if origin is not None else Controller.Command.Origin.USER
    self.callbacks = []
```
→ add `release_unverified: bool = False` kwarg + attribute. It lives only on the object and is never persisted (D-08).

**4. DEL-01 guard in `__execute_auto_delete`.** Insert under `__model_lock`, after the state guard (L836-837), in the same `defer_reason` style:
```python
if file.state not in deletable_states:
    defer_reason = "file is in state {}".format(str(file.state))
```
→ `elif file_name in self.__lftp_manager.submitted_unobserved_file_names(): defer_reason = "transfer submitted, awaiting lftp status"`.
- The re-arm path is already wired (L887-891 → `__defer_auto_delete` L710-739, bounded by `_AUTO_DELETE_MAX_REARMS` L32).
- Optionally add the reason string to `_AUTO_DELETE_DEFER_REASONS` (L36-39) style.

**5. IMP-03 early credit in `__check_webhook_imports`.** The modification point is the "no transfer evidence" `continue` at L630-637:
```python
if not has_evidence:
    self.logger.warning(
        "Ignoring webhook import for '{}': not downloaded "
        "by SeedSyncarr (no transfer evidence)".format(
            sanitize_log_value(root_name)
        )
    )
    continue
```
Child credit must use only the existing call at L660-661:
```python
if matched_name.lower() != root_name.lower():
    self.__persist.add_imported_child(root_name, matched_name.lower())
```
Do not add to `downloaded_file_names` or `imported_file_names` (Pitfall 8).
- The child lookup can reuse the BFS at L590-597.
- Arm-on-commit goes into the cycle. Copy the schedule-outside-lock block at L676-678:
```python
if self.__context.config.autodelete.enabled:
    for root_name in accepted_roots:
        self.__schedule_auto_delete(root_name)
```

**6. D-20 immediate persist.** Today `ControllerPersist` is saved only by `seedsyncarr.py` `persist()` (L254-259), every `MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS = 30` (`common/constants.py` L10) via the loop at L186-191.
- Inject a callback in the same style as `force_local_scan_callback` (controller.py L153-158):
```python
self.__file_op_manager = FileOperationManager(
    context=self.__context,
    mp_logger=self.__mp_logger,
    force_local_scan_callback=self.__scan_manager.force_local_scan,
    force_remote_scan_callback=self.__scan_manager.force_remote_scan
)
```
  For example, `Controller(..., persist_callback=...)` wired at `seedsyncarr.py` L145, calling `self.controller_persist.to_file(self.controller_persist_path)`. Invoke it **outside** `__model_lock`.
- `Persist.to_file` (`common/persist.py` L59-104) is atomic: it uses a unique `mkstemp` temp file + `os.replace`, so concurrent writers never corrupt the file.
- **Planner flag:** `to_str()` reads persist collections that the controller thread mutates. Serialize the immediate save against the 30 s loop (one lock around `to_file`) or call it from the controller thread only, after the mutation window closes.

---

### `src/python/controller/auto_queue.py` (MODIFIED: sweep gate)

**Analog:** self, L311-337. The gate goes **between** the stopped/downloaded filter and the cooldown stamp (Pitfall 3):
```python
for name, pattern in sweep_matches:
    is_stopped = self.__controller.is_file_stopped(name)
    is_downloaded = self.__controller.is_file_downloaded(name)
    ...
    if is_stopped or is_downloaded:
        continue
    # <-- NEW: completion gate verdict; HOLD -> continue (no cooldown stamp)
    if scan_time is not None:
        last_attempt = self.__last_queue_attempt.get(name)
        if last_attempt is not None and \
                scan_time - last_attempt < AutoQueue.REQUEUE_COOLDOWN_SECONDS:
            continue
        self.__last_queue_attempt[name] = scan_time
    files_to_queue.append((name, pattern))
```
- Batch the evaluation: collect the candidate names first, then call `self.__controller.evaluate_completion(names)` once. That gives one fetch per arr per cycle (D-13).
- D-16: when no arr is enabled, the verdict is "not required" and the existing stability checks in `sweep_accept` (L283-304) remain the gate.

---

### `src/python/controller/command_processor.py` (MODIFIED: `_handle_queue`)

**Analog:** self, L120-149. Mirror the AUTO execution-time guard (L123-133) and add the gate re-check:
```python
is_auto = getattr(command, "origin", None) is not None and \
    command.origin.name == 'AUTO'
if is_auto:
    if file.name in self.__persist.stopped_file_names or \
            file.name in self.__persist.downloaded_file_names:
        self.logger.info(
            "Skipping auto-queue of '{}': guarded at execution time".format(
                sanitize_log_value(file.name)
            )
        )
        return True, None, None
```
- AUTO and not proven → `return True, None, None` (quiet skip, hold remains).
- USER, not proven, `getattr(command, "release_unverified", False)` false → `return False, "Completion could not be verified: <label>", 428`.
- USER with the flag → WARNING log "Manual release of unverified '<name>' (<reason>)", then the existing submit path L135-147.

Keep duck-typing via `getattr`: the class docstring (L64-67) forbids importing `Controller.Command`. Inject the gate through `__init__` (L37-54), following the existing kwargs pattern.

---

### `src/python/controller/lftp_manager.py` (MODIFIED: forced temp file + lock + ordering)

**Forced temp (IMP-01/D-18)**, L74-75 today:
```python
self.__lftp.use_temp_file = context.config.lftp.use_temp_file
self.__lftp.temp_file_name = "*" + Constants.LFTP_TEMP_FILE_SUFFIX
```
→ `self.__lftp.use_temp_file = True`. Log once if the config value is False (D-19: the key is accepted but ignored).

**Lock around the submitted set (DEL-01, Pitfall 6).** Today the set is unguarded: L94, `add` L144, `discard` L165, `clear` L183, `sorted()` L212. Copy the lock idiom from controller.py L209 (`self.__auto_delete_lock = threading.Lock()`) and wrap every access.
- `submitted_unobserved_file_names()` must keep returning a new sorted list (snapshot contract, docstring L200-212).
- Update the class docstring at L22-31, which says the set is "only touched from the controller thread". That is no longer true.

**Add-before-queue ordering**, L142-144 today:
```python
self.__sync_rate_limit()
self.__lftp.queue(file_name, is_dir)
self.__submitted_unobserved.add(file_name)
```
→ add under the lock, then call `queue`. Discard on `LftpError` and re-raise.

---

### `src/python/controller/scan_manager.py` (MODIFIED)

**Analog:** self, L46-53:
```python
self.__active_scanner = ActiveScanner(
    context.config.lftp.local_path,
    use_temp_file=context.config.lftp.use_temp_file
)
self.__local_scanner = LocalScanner(
    local_path=context.config.lftp.local_path,
    use_temp_file=context.config.lftp.use_temp_file
)
```
→ `use_temp_file=True` in both places.

---

### `src/python/controller/model_builder.py` + `model_pipeline.py` (MODIFIED: hold reasons)

**Analog:** `set_submitted_files`, model_builder.py L91-101 (change-detected, cache-invalidating):
```python
def set_submitted_files(self, submitted_files: Iterable[str]) -> None:
    new_submitted_files = set(submitted_files)
    if new_submitted_files != self.__submitted_files:
        self.__submitted_files = new_submitted_files
        self.__cached_model = None
```
- Add `set_hold_reasons(Dict[str, str])` with the same shape.
- Initialize it in `__init__` beside L34 and clear it in `clear()` (L103-112).
- Apply it after the final state is computed, to root files in `DEFAULT` only. The state is set in `_set_initial_state` (L228-243).

**Feed site:** `model_pipeline.py` L167-170:
```python
self._model_builder.set_submitted_files(self._lftp_manager.submitted_unobserved_file_names())
```
→ add `self._model_builder.set_hold_reasons(<gate>.holds)`. The gate must then be injected into `ModelPipeline`; follow the kwargs pattern at controller.py L245-255.

---

### `src/python/model/file.py` (MODIFIED)

**Analog:** `import_status`, attr L54 + property/setter L237-245 (setter calls `_check_frozen`, type-checks).
- Add `self.__hold_reason = None` in `__init__`.
- Add a property/setter that accepts `Optional[str]`.
- `__eq__` (L87-122) compares every `__dict__` key except the excluded four, so the new attribute participates in diffs automatically and needs no further change.

### `src/python/web/serialize/serialize_model.py` (MODIFIED)

**Analog:** L59 and L85-86:
```python
__KEY_FILE_IMPORT_STATUS = "import_status"
...
json_dict[SerializeModel.__KEY_FILE_IMPORT_STATUS] = \
    SerializeModel.__VALUES_FILE_IMPORT_STATUS[model_file.import_status]
```
→ `__KEY_FILE_HOLD_REASON = "hold_reason"`. Emit a stable code (`sonarr_unavailable`, `radarr_unavailable`, `ambiguous_match`, `still_downloading`, `no_queue_entry`) or `None`.

---

### `src/python/web/handler/controller.py` (MODIFIED: `release_unverified`)

**Single endpoint.** `_dispatch_command` L76-105 builds `Controller.Command(action, file_name)` at L96. Add a keyword for the flag, and read `request.query.get("release_unverified") == "true"` only in `__handle_action_queue` (L107-111).

**Bulk validation.** Mirror the strict type checks at L250-260:
```python
if not isinstance(files, list):
    return HTTPResponse(
        body=json.dumps({"error": "files must be an array"}),
        status=400,
        content_type="application/json"
    )
```
→ `release_unverified = body.get("release_unverified", False)`; reject with 400 unless it is `isinstance(..., bool)` (V5). Reject it for any action other than `queue`.

**Bulk command construction**, L349-353:
```python
command = Controller.Command(action, file_name)
callback = WebResponseActionCallback()
command.add_callback(callback)
self.__controller.queue_command(command)
```
→ pass the flag through. Per-file `error_code` already flows to the client (L386-392). 428 reaches the browser as `error_code: 428`.

---

### `src/python/lftp/lftp.py` (MODIFIED: XFER-06 resync)

**Analog:** self.
- State flag, beside L53-55:
```python
# Set when the most recent command's expect timed out, i.e. its output
# is an incomplete observation. Only status() consults it.
self.__last_command_timed_out = False
```
  → add `self.__synced = True`.
- Both TIMEOUT sites (L122-124 and L143-145) set `self.__synced = False`.
- At the top of `__run_command` (after the `@with_check_process` decorator, L114-118), call the resync, which raises `LftpError("lftp command stream not synchronized")` on failure.
- Expect pattern: `self.__expect_pattern` (L49).
- `status()` (L304-335) must catch that error and return `None`, without touching `__consecutive_status_errors` (docstring L313-317: timeouts neither count nor reset).
- `queue()` (L337+) lets it raise. `LftpManager.queue` then discards the name (see above), and `CommandProcessor` returns 500 (L148-149).
- Sentinel code: RESEARCH Pattern 4 (quote-split `echo`, `secrets.token_hex(8)`, `re.escape(...).encode()`). Import `secrets` beside L1-6.

---

### `src/python/pyproject.toml` (MODIFIED: REL-02)

The current lines L36-37 are the root cause:
```toml
[tool.hatch.build.targets.wheel]
packages = ["."]
```
→ replace with the `only-include` wheel and sdist blocks from RESEARCH Pattern 7, which were verified locally.
- Bump `version` at L7 and L43 to `1.7.5`.
- D-21: bump `cryptography` (L19, L56) and `pytz` (L15, L53) only as the Dependabot PRs #123 and #124 do, and regenerate `poetry.lock`.

### `.github/workflows/ci.yml` (MODIFIED: `verify-python-package` job)

**Job skeleton analog:** `lint-python` (L73-94). It runs on every push/PR, uses pinned `actions/checkout@de0fac2…` and `actions/setup-python@a309ff8…` with 3.12, and needs no Docker.

**Build step analog:** `publish-pypi` L329-331:
```yaml
- name: Build package
  run: pip install build && python -m build
  working-directory: src/python
```
- New steps: `pip install build twine` → `python -m build` → `twine check dist/*` (non-strict) → inline Python member-path check (no analog; zipfile/tarfile scan for `./` or `..`) → venv install and `seedsyncarr --help`.
- Add the job to the `needs:` of `publish-pypi` (L312) and `build-docker-image` (L121).
- Keep SHA-pinned actions and the `timeout-minutes` convention.

---

### Angular: `model-file.ts`, `view-file.ts`, `view-file.service.ts`

**Analog:** `import_status` plumbing end to end.
- `model-file.ts`:
  - JSON interface L18 `import_status?: string | null;`
  - IModelFile L40
  - default L59
  - class field L84
  - `fromJson` L123-137, with a fallback for older backends
- `view-file.ts`: `importStatus` at L30 (interface), L55 (default) and L83 (field).
- `view-file.service.ts` L439:
```ts
importStatus: ViewFileService.mapImportStatus(modelFile.import_status)
```
→ add `hold_reason: string | null` (model) and `holdReason: string | null` (view). Map the code to the verbatim label through `Localization` (D-10 labels).

### `src/angular/src/app/pages/files/transfer-row.component.ts` + `.html`

**Analog:** the `isSkippedRemote` override (L72-90), the same "special-case before BADGE_LABELS lookup" pattern:
```ts
get badgeLabel(): string {
    if (this.isSkippedRemote) { return "Skipped (remote)"; }
    const status = this.file.status ?? ViewFile.Status.DEFAULT;
    return TransferRowComponent.BADGE_LABELS[status] ?? "—";
}
```
- Add `get isHeld()` (`status === DEFAULT && holdReason`), returning label "Waiting" and class `badge bg-secondary`.
- Leave `BADGE_LABELS` and `BADGE_CLASSES` (L49-69) **unchanged**. Memory note: badge labels live in three places (component, e2e specs, seed-state LABEL table), so grep `src/e2e` for "Waiting".
- Template: put the reason in the `file-meta` line (html L8-12), following the existing `file-meta-dot` separator pattern, and add `[title]` on the badge span (L15).
- `hostAriaLabel` (L39-42) already uses `badgeLabel`.

### `src/angular/src/app/services/files/bulk-action-dispatcher.service.ts`

**Analog:** `confirmAndDispatchDeleteLocal` (L64-82), the confirm flow:
```ts
const body = Localization.Modal.BULK_DELETE_LOCAL_MESSAGE(fileNames.length)
             + this._buildPreviewSuffix(fileNames);
const confirmed = await this._confirmModalService.confirm({
    title: Localization.Modal.BULK_DELETE_LOCAL_TITLE,
    body,
    okBtn: "Delete",
    okBtnClass: "btn btn-outline-danger",
    skipCount: skipCount > 0 ? skipCount : undefined
});
```
- `dispatchQueue` (L44-49) → after the result, collect `result.response.results.filter(r => r.error_code === 428)`.
- If there are any, confirm with body `"Completion could not be verified. Transfer and release this item anyway?"` (verbatim, D-08) plus `_buildPreviewSuffix`.
- On OK, re-dispatch only those files with the flag.
- The `_inProgress` gate (L107-111) must be released before the re-dispatch. `_dispatch` currently clears it in `next`, so chain the confirm after it.
- 428 is non-transient per `isTransientFailure` (bulk-command.service.ts L87-91).

### `src/angular/src/app/services/server/bulk-command.service.ts`

**Analog:** self L116-119:
```ts
public executeBulkAction(action: BulkAction, files: string[]): Observable<BulkActionResult> {
    return new Observable<BulkActionResult>(observer => {
        const body = {action, files};
```
→ add an optional `options?: {releaseUnverified?: boolean}` and emit `release_unverified: true` only when it is set.

### `src/angular/src/app/common/localization.ts`

**Analog:** `Modal` class L19-47 (`*_TITLE` / `*_MESSAGE` constants).
- Add `RELEASE_UNVERIFIED_TITLE` and `RELEASE_UNVERIFIED_MESSAGE` (verbatim D-08 text).
- Add a `Hold` class with the five labels:
  - "Sonarr unavailable"
  - "Radarr unavailable"
  - "Ambiguous match"
  - "Still downloading"
  - "No matching queue entry"

### `src/angular/src/app/pages/settings/options-list.ts` (D-19)

Delete the entry at L139-144:
```ts
{
    type: OptionType.Checkbox,
    label: "Rename unfinished/downloading files",
    valuePath: ["lftp", "use_temp_file"],
    description: "Unfinished and downloading files will be named *.lftp"
},
```
- Keep `config.ts` L36/L52 `use_temp_file` (the backend still serializes the key).
- The config specs (`config.spec.ts` L27/64, `config.service.spec.ts` L77/109) stay valid.
- Python `Config.Lftp.use_temp_file` (`common/config.py` L276, L294) stays parseable.

### `src/e2e/tests/fixtures/seed-state.ts` (Pitfall 2)

**Analog:** self, L17:
```ts
queue:        (n: string) => `/server/command/queue/${encodeURIComponent(n)}`,
```
- D-16: the e2e harness has no arr enabled, so the gate is bypassed and seeding should keep working unchanged.
- Add `?release_unverified=true` only if the e2e config enables an arr. The planner should check this, not assume it.

---

### Tests

**`test_lftp_resync.py` (NEW).** Analog: `test_lftp_status_contract.py` L86-130 `_make_lftp_with_scripted_process`.
- It drives the REAL `Lftp.__run_command` over a mocked pexpect: `patch('pexpect.spawn')`, a scripted `_expect` side effect, `_TimedOut` items, and recorded `sendline`s.
- Extend that harness, or use the byte-buffer `_FakeStream` from RESEARCH §Code Examples, so a stale prompt after a timeout is observable.

**`test_arr_queue.py` (NEW).** Analog: `test_config_handler.py` L198-265:
```python
@patch('web.handler.config.requests')
...
mock_requests.get.return_value = mock_response
mock_requests.ConnectionError = requests.ConnectionError
mock_requests.Timeout = requests.Timeout
```
- Patch `controller.arr_queue.requests` the same way. Re-bind the exception classes on the mock, or the `except` clauses break.
- Assert that no log call contains the api key.

**`test_import_credit.py` (NEW).** Analog: `test_import_ambiguity.py` L1-40. It uses a real `WebhookManager` and a real `ModelFile` tree (`_leaf`/`_pack` helpers, "build tree before `Model.add_file` freezes it"), with `BaseAutoDeleteTestCase` as the base.

**DEL-01 tests.** Extend `test_auto_delete_rearm.py`, using its helpers (L22-71): `_make_file`, `_set_model_file`, `_fire`, `_pending`, `_rearms` and `_deferred_line(file_name, attempt, reason, ...)`. Set `self.mock_lftp_manager.submitted_unobserved_file_names.return_value = [ROOT]`.

**`base.py`.** Add `self.patcher_cg = patch('controller.controller.CompletionGate')` to the patcher list (L17-30, stop in tearDown L49-55). Default the verdict to PROVEN / not-required, so existing tests keep their meaning.
- Same treatment for `ArrQueueClient` if it is constructed in the Controller.
- **Caution:** `test_auto_queue.py` uses `self.controller = MagicMock()` (L301-354). A new `controller.completion_verdict(...)` / `evaluate_completion(...)` returns a truthy MagicMock unless it is stubbed in `setUp`. Stub it explicitly in both `TestAutoQueue` (L280) and `TestAutoQueueCommandOrigin` (L1767).

---

## Shared Patterns

### Log sanitization (CWE-117)
**Source:** `from common import sanitize_log_value` (command_processor.py L3, controller.py L20).
**Apply to:** every log line containing a root, child, `outputPath` or `title` (gate holds, manual release WARNING, credit INFO, resync).
```python
"Skipping auto-queue of '{}': guarded at execution time".format(sanitize_log_value(file.name))
```

### Secrets never logged
**Source:** user CLAUDE.md + `config.py` `secret=True` (L341, L352).
**Apply to:** arr_queue.py and completion_gate.py. Log `type(e).__name__` or the status code only. No URL, headers, body or key.

### Collaborator construction (mock-patch binding)
**Source:** controller.py L218-255 "D-05" comments.
**Apply to:** CompletionGate / ArrQueueClient. Construct them in `Controller.__init__` and inject them into CommandProcessor and ModelPipeline. Collaborators never construct managers.

### (success, msg, code) triple + HTTP status mapping
**Source:** command_processor.py L56-73. Codes 404/409/500 are documented in `ICallback.on_failure` (controller.py L86-98).
**Apply to:** the 428 path. Add 428 to the `on_failure` docstring code list. Do not reuse 409 (RESEARCH A6).

### Retriable defer, not ad-hoc timers
**Source:** `__defer_auto_delete` (controller.py L710-739) + `_AUTO_DELETE_MAX_REARMS` (L32).
**Apply to:** the DEL-01 guard.

### Atomic persistence
**Source:** `Persist.to_file` (common/persist.py L59-104).
**Apply to:** the D-20 immediate credit save. Do not write a new writer.

### Lock discipline
**Source:** the controller.py lock-order comment, L741-748 ("`__model_lock` THEN `__auto_delete_lock`").
**Apply to:**
- The new LftpManager lock: a leaf lock, never held while calling out.
- The D-20 persist call: outside `__model_lock`.

### Monotonic-clock backoff
**Source:** lftp_manager.py L175-198.
**Apply to:** CompletionGate per-arr refresh/backoff.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| CI inline wheel/sdist member-path checker | script | batch | No packaging-verification step exists. Use the RESEARCH Pattern 7 description (zipfile/tarfile scan for `./` / `..`) |
| Arr queue verdict/matching logic inside `completion_gate.py` | service | transform | No existing arr-state consumer. Use the RESEARCH §"Exact matching rule" amended by D-16/D-17 |

## Conventions

Derived with `gsd-tools verify conventions --derive --scope src/python`, plus manual reading. The tool's heuristics are JS-oriented. On this Python tree they count `snake_case` module names as "other/camel" and report a spurious "cjs" export axis, so the table records the observed Python and Angular conventions, with the tool's numbers where they are meaningful.

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| File-name casing | Python `snake_case.py`; Angular `kebab-case.<kind>.ts` (tool: contested, 0.40 share) | 0.40 (tool) | 0.986 | contested hotspot (tool artifact; per-directory consistent) |
| Identifier casing | Python: `snake_case` funcs, `PascalCase` classes, `UPPER` constants, `__name` private members; TS: camelCase | 0.55 (tool) | 0.605 | contested hotspot (language split) |
| Export style | Python: no `__all__` needed, package `__init__` re-exports (`from lftp import Lftp`); TS: named `export class` | 1.00 (tool "cjs" = artifact) | 0 | named contract |
| Import style | Python: explicit (no wildcards, 73/73); relative within a package (`from .lftp_manager import ...`), absolute across packages (`from common import ...`) | 0.65 relative | 0.935 | contested hotspot (intentional intra/inter-package split) |

**Contested hotspots (author's choice):**
- The prototype intentional split is the CJS<->SDK dual resolver: `bin/lib/**` is CJS, `sdk/src/**` is ESM. Each half is internally consistent per directory, and the axis is contested only repo-wide.
- The same logic applies here. Inside `src/python/controller/`, use relative sibling imports (`from .arr_queue import ArrQueueClient`) and absolute cross-package imports (`from common import Context, sanitize_log_value`), exactly as controller.py L9-23 does.
- In `src/python/lftp/`, use `from .job_status_parser import ...` + `from common import ...` (lftp.py L8-9).
- Match the directory's local style.

## Metadata

**Analog search scope:**
- `src/python/{controller,lftp,model,web,common}`
- `src/python/tests/unittests/{test_controller,test_lftp,test_web}`
- `src/angular/src/app/{services,pages,common}`
- `src/e2e/tests/fixtures`
- `.github/workflows`
- `docs`

**Files scanned:** ~40
**Pattern extraction date:** 2026-10-14
