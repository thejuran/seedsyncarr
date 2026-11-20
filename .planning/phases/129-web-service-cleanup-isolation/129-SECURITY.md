---
phase: 129
slug: web-service-cleanup-isolation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-11-20
---

# Phase 129 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Verified against the current code at `23f2006e` (after review fixes WR-01 and IN-01..IN-04), not against plan wording. Paths below are relative to `src/python/`: `web/web_app_job.py` is the implementation, `test_web_app_job.py` is `tests/unittests/test_web/test_web_app_job.py`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| job thread -> application log | Three error lines, one warning line and six debug lines written during web-service startup and shutdown | Fixed step names and the join timeout value; tracebacks of shutdown calls (no request data) |
| job thread <-> server thread | `stop()` and `run()` share the server reference and two flags during startup | Server object reference, stop-requested and ended-without-server flags (non-sensitive) |
| process lifetime -> Docker stop grace | A shutdown that outlasts 10 s is killed and the final state save is lost | Shutdown timing (availability / data safety) |
| test process -> child process | One test starts a child Python interpreter | Fixed module-level script, no external input |
| test process -> loopback socket | Real-server tests listen on 127.0.0.1 with an ephemeral port | Test HTTP requests only |

No new input crosses a boundary in production code: the phase diff (`dc0aa172..HEAD`) touches only `web/web_app_job.py` and its unit test file, and adds no route, parameter, file read or network read.

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-129-01 | Denial of service | WebAppJob.cleanup, unbounded join | mitigate | `web/web_app_job.py:81` `thread.join(timeout=self._SERVER_THREAD_JOIN_TIMEOUT_IN_SECS)` is the only join in the file; constant is 5.0 at line 26; warning then continue at 82-84. Pinned by test_web_app_job.py:225 (stuck thread warns and returns), :238 (real stuck thread, elapsed < 1.0 s) and :282 (constant == 5.0). The plan's separate "< 10.0" assertion was removed as tautological by review fix IN-04; the 5.0 pin still enforces it | closed |
| T-129-02 | Denial of service | WebAppJob.cleanup, one failing step skipping the rest | mitigate | `web/web_app_job.py:62-65`, `67-71`, `76-86`: one `try/except Exception` per step. Pinned by test_web_app_job.py:89, :107, :125, :143 | closed |
| T-129-03 | Denial of service | Non-daemon web-server thread | mitigate | `web/web_app_job.py:44-50` `Thread(..., daemon=True)`; pinned by test_web_app_job.py:277 and :273 | closed |
| T-129-04 | Information disclosure | Shutdown log lines | mitigate | `web/web_app_job.py:65,71,86` fixed strings; line 83 formats only the class constant. Exact strings pinned at test_web_app_job.py:17-20 and asserted in the step-failure tests. Tracebacks come from `app.stop()`, `server.stop()` and `thread.join()` only | closed |
| T-129-05 | Repudiation | Cleanup failures swallowed silently | mitigate | All three `except Exception` blocks in `cleanup()` call `logger.exception` (lines 65, 71, 86; count 3 = 3). Order asserted at test_web_app_job.py:158-159. The fourth except in the file (`run()`, line 162, added by WR-01) re-raises unless a stop was requested and otherwise logs at debug, so it is not silent either | closed |
| T-129-06 | Denial of service | Non-daemon paste pool workers | mitigate | `web/web_app_job.py:139` `daemon_threads=True` passed to `httpserver.serve`. Pinned by test_web_app_job.py:404-413; proven by the child-process test at :682 (interpreter exits by itself with a never-stopped server) | closed |
| T-129-07 | Denial of service | stop() before run() stored the server | mitigate | Changed by review fix IN-02, stricter than planned. Stop before startup: `web/web_app_job.py:130-133` returns before `httpserver.serve`, so the port is never bound (test_web_app_job.py:367 mock, :589 real server with a spy on paste's `serve`). Stop during construction: flag and reference read under one lock at 148-150, then `server_close()` and return at 151-159 without serving (test_web_app_job.py:436). Flag is set under the same lock in `stop()` at 177-180, so a stop is never lost | closed |
| T-129-08 | Denial of service | Deadlock from shutdown() or lock held across a blocking call | mitigate | `grep "shutdown("` on `web/web_app_job.py` returns 0 matches. Lock scopes are lines 130-133, 146-147, 148-150, 170-171, 177-180; `server_close()` (158), `serve_forever()` (161) and `socket.close()` (196) all run outside the lock. See observation below on the one debug log call made under the lock | closed |
| T-129-09 | Denial of service | Port still held after a failed server.stop() during in-process restart | accept | See Accepted Risks Log AR-129-01. Related SA-02 is tracked as backlog 999.10 (ROADMAP.md:251) | closed |
| T-129-10 | Tampering | In-flight responses cut off at interpreter exit | accept | See Accepted Risks Log AR-129-02 | closed |
| T-129-11 | Information disclosure | Debug lines in stop() and run() | mitigate | All six debug lines are literal strings with no formatting or interpolation: `web/web_app_job.py:123, 132, 174, 183, 185, 187`. This covers the planned "stop deferred to startup" line (185), the IN-03 "never started; nothing to stop" line (183), the IN-02 "not starting" line (132) and the WR-01 "loop ended after stop()" line (174). Strings pinned at test_web_app_job.py:21-22, asserted at :387 and :400-402 | closed |
| T-129-12 | Elevation of privilege | Child process started by a test | mitigate | test_web_app_job.py:687 `subprocess.run([sys.executable, "-c", NEVER_STOPPED_SERVER_SCRIPT], ...)` with the script a module-level constant (lines 34-54); no shell; `grep -c "shell=True"` prints 0; this is the only subprocess call in the file | closed |
| T-129-13 | Information disclosure | Test listeners reachable from the network | mitigate | Every `MyWSGIRefServer(...)` in the test file binds `host="127.0.0.1", port=0` (lines 44, 322, 535, 571, 592, 622); line 622 is the patched constructor that replaces the 0.0.0.0 from `setup()`. `grep -c '0\.0\.0\.0'` on the test file prints 0. Listeners are closed in the test body or by registered cleanups (:346-354, :632-644); the child's listener ends with the child process | closed |
| T-129-14 | Denial of service | stop() running paste's pool teardown on the job thread | mitigate | `web/web_app_job.py:195-196`: `stop()` only sets `server.running = False` and closes the socket; it never calls `server_close()` or the pool shutdown. Checked in the installed paste source: `serve_forever`'s finally calls `thread_pool.shutdown()` with the default `force_quit_timeout=0`, and the `os._exit(3)` branch sits inside `if force_quit_timeout:`. Proven by test_web_app_job.py:608 (real server, five workers all stuck, elapsed < 1.5 s, `os._exit` patched and asserted unused) and pinned at :420-434 and :466-490 | closed |
| T-129-SC | Tampering | Package installs | accept | See Accepted Risks Log AR-129-03 | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**Unregistered flags:** none. 129-01-SUMMARY.md has no Threat Flags section; 129-02-SUMMARY.md states "None". The post-plan changes (WR-01, IN-02, IN-03) add no input surface and map to T-129-05, T-129-07 and T-129-11.

**Observations (not gaps):**

- The debug log call at `web/web_app_job.py:132` runs while the adapter lock is held. T-129-08's wording says the lock is held "only for the flag and reference snapshot". This cannot deadlock (`stop()` logs outside the lock and nothing in the logging path takes this lock), and it is not one of the three blocking calls the mitigation names. It could delay a concurrent `stop()` by the duration of one log write.
- The WR-01 handler (`web/web_app_job.py:162-174`) treats `OSError`/`ValueError` from the serve loop as a clean exit only when the adapter's own stop-requested flag is set, read under the lock. Without a stop the error propagates (test_web_app_job.py:518). A real serve-loop failure is therefore not hidden.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-129-01 | T-129-09 | If `server.stop()` itself fails, the old listener can still hold the port during an in-app restart. No new recovery behaviour is in this phase's scope (CONTEXT). It is surfaced by the cleanup error and warning lines plus the new server thread's bind traceback on stderr. The stderr-only reporting of a bind failure is SA-02, deferred to backlog 999.10 by owner ruling | Plan 129-02 threat model; owner ruling on SA-02 (STATE.md:150) | 2026-11-20 |
| AR-129-02 | T-129-10 | Workers are now daemon threads, so a request still running after the 5 s bound is cut off at interpreter exit. cleanup() closes the listener and waits up to 5 s first, and SSE streams end on `WebApp.stop()`. Shutdown must never wait indefinitely on the web server (owner decision D-04) | Plan 129-02 threat model (owner decision D-04) | 2026-11-20 |
| AR-129-03 | T-129-SC | No dependency was added or changed: `git diff --stat dc0aa172..HEAD` outside `.planning` lists only `web/web_app_job.py` and its test file | Plans 129-01 and 129-02 threat models; re-verified by bm-security-auditor | 2026-11-20 |
| AR-129-04 | SA-01 (code review) | At an in-app restart, a request still stuck in its handler is force-killed by paste and leaves one idle replacement daemon worker that never exits; these can accumulate across in-app restarts until the next container restart. Pre-existing paste behaviour, rare, and the alternative (`kill_thread_limit: 0`) trades it for a permanently stuck thread | Owner (STATE.md:149) | 2026-11-20 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-20 | 15 | 15 | 0 | bm-security-auditor (fable); test_web_app_job.py 27 passed / 4 subtests |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-20
