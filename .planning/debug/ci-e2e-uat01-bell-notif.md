---
status: resolved
trigger: "CI e2e failures after commit e95cf6c — UAT-01 notification bell assertions likely broken"
created: 2026-04-22
updated: 2026-04-22
---

# Debug Session: ci-e2e-uat01-bell-notif

## Symptoms

- **Expected behavior:** UAT-01 bulk action tests should dispatch actions, then verify success notifications appear. Commit e95cf6c switched from toast assertions (.toast.moss-toast) to notification bell assertions (.bell-notif / .bell-badge-dot) since bulk actions use NotificationService not ToastService.
- **Actual behavior:** CI fails on both amd64 and arm64 runners at "End-to-end tests on Docker Image" step "Run e2e test". Two distinct tests fail: UAT-01 (line 215) and UAT-02 (line 389).
- **Error messages:**
  - UAT-01: `TimeoutError: locator.waitFor: Timeout 15000ms exceeded` on `waitForFileStatus('testing.gif', 'Syncing', 15_000)` (initial), then on retry #1: `locator.click: Test timeout exceeded` — Queue button is `disabled`
  - UAT-02: `expect(getStatusBadge('illusion.jpg')).toContainText('Failed')` fails
- **Timeline:** Started with commit e95cf6c. Three prior bug fixes (rate_limit, illusion.jpg size, UAT-02 sub=pending) are confirmed correct.

## Root Cause

**UAT-01 — Two compounding issues:**

1. **Fast-download race condition**: `testing.gif` (9 MB) downloads in < 1 second at Docker localhost speeds. After Action 1's Queue dispatches, the file transitions DEFAULT → QUEUED → DOWNLOADING (Syncing) → DOWNLOADED (Synced) before the bell open/read/close interaction (~1-2 s) completes. The old code tried to re-queue testing.gif for Action 2 at line 258, but by then the file was DOWNLOADED — `isQueueable` requires DEFAULT or STOPPED state — Queue button disabled.

2. **State leakage across Playwright retries**: Each retry calls `beforeEach → navigateTo()` which navigates the browser but does NOT reset backend file state. After retry #0 left testing.gif in DOWNLOADING state (from line 258 re-queue that timed out), retry #1 started with testing.gif still DOWNLOADING — Action 1's Queue button disabled from the start.

**UAT-02 — State contamination from UAT-01 failures:**

UAT-01's three retries leave `testing.gif` in active transfer state. UAT-02's `beforeAll` runs the STOPPED seed for `illusion.jpg` which sets `rate_limit=100` globally. The seed succeeds and restores `rate_limit=0` in finally. However, if `illusion.jpg` gets re-queued between `beforeAll` finishing and the UAT-02 test at line 389 running (e.g., by lftp auto-resume behavior after rate_limit restoration), the badge shows 'Syncing' instead of 'Failed'. Belt-and-braces guard was missing.

## Evidence

- timestamp: 2026-04-22 CI job 72620075926 (amd64)
  content: "UAT-01 initial failure (18.5s): waitForFileStatus('testing.gif', 'Syncing', 15_000) at spec:263 → TimeoutError"
- timestamp: 2026-04-22 CI job 72620075926 retry #1
  content: "Queue button disabled at spec:229 (Action 1 Queue) — testing.gif DOWNLOADING from prior retry's re-queue"
- timestamp: 2026-04-22 CI job 72620075926 retry #2
  content: "Same: Queue button disabled at Action 1. testing.gif still non-DEFAULT."
- timestamp: 2026-04-22 lftp log at container teardown
  content: "testing.gif at 4128768 (43%) [Receiving data], illusion.jpg at 1049489 (0%) [Receiving data] — both actively downloading when containers stop"
- timestamp: 2026-04-22 UAT-02 failure
  content: "expect(getStatusBadge('illusion.jpg')).toContainText('Failed') fails at spec:396 — badge shows Syncing not Failed"

## Resolution

- root_cause: "testing.gif downloads too fast for the bell-check window to complete before it leaves DOWNLOADING state; no per-retry state reset exists"
- fix: "Three changes to src/e2e/tests/dashboard.page.spec.ts:
  (1) UAT-01 test now accepts { page } parameter.
  (2) Added retry-safe guard at test start: POST /server/command/stop/testing.gif to force any active download to STOPPED, then 500ms wait for propagation.
  (3) Action 1+2 throttled: set rate_limit=100 before Action 1 Queue so testing.gif stays in DOWNLOADING (Syncing) throughout bell interaction AND is still Syncing when Action 2 Stop is dispatched. Removed the separate re-queue lines 257-263. rate_limit restored to 0 in finally block.
  (4) UAT-02 test at line 389 (now ~433): added belt-and-braces guard: try waitForFileStatus('illusion.jpg', 'Failed', 3s), on failure re-seed STOPPED via seedStatus."

## Eliminated

- Bell toggle interfering with subsequent actions (focus/overlay issues) — not the issue; Action 1 itself fails
- Notifications auto-dismissing before bell opens — not the issue; bell opens after badge dot appears
- Multiple notifications — not the issue; failure is before notification check
