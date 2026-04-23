import { test, expect } from './fixtures/csp-listener';
import { DashboardPage, FileInfo } from './dashboard.page';
import { seedMultiple, seedStatus } from './fixtures/seed-state';

const TEST_FILE = 'clients.jpg';
const DELETED_FILE = 'clients.jpg';        // FIX-01 anchor; pre-seeded DELETED via seed-state (RESEARCH Pitfall 2 rejected 'joke' as a directory)
const DOWNLOADED_FILE = 'documentation.png';  // seeded DOWNLOADED sibling — small 9KB file; ALSO the Delete Local target in Spec 4 (see mapping comment in Task 2)
const STOPPED_FILE = 'illusion.jpg';       // seeded STOPPED sibling — 2MB
const DEFAULT_FILE = 'goose';              // unseeded fixture in DEFAULT state

test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('should have Dashboard nav link active', async () => {
        const activeLink = await dashboardPage.getActiveNavLink();
        expect(activeLink).toBe('Dashboard');
    });

    test('should have a list of files', async () => {
        const golden: FileInfo[] = [
            { name: 'áßç déÀ.mp4', status: '', size: '800 KB' },
            { name: 'clients.jpg', status: '', size: '40 KB' },
            { name: 'crispycat', status: '', size: '2 MB' },
            { name: 'documentation.png', status: '', size: '9 KB' },
            { name: 'goose', status: '', size: '3 MB' },
            { name: 'illusion.jpg', status: '', size: '2 MB' },
            { name: 'joke', status: '', size: '200 KB' },
            { name: 'testing.gif', status: '', size: '9 MB' },
            { name: 'üæÒ', status: '', size: '70 KB' },
        ];
        await dashboardPage.waitForAtLeastFileCount(golden.length);
        const files = await dashboardPage.getFiles();
        // Compare order-independent: display order depends on browser locale's
        // localeCompare, which can differ between amd64/arm64 Chromium builds.
        const byName = (a: FileInfo, b: FileInfo) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
        expect([...files].sort(byName)).toEqual([...golden].sort(byName));
    });

    test('should show and hide action buttons on select', async () => {
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionBar()).toBeVisible();

        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionBar()).not.toBeVisible();
    });

    test('should show action buttons for most recent file selected', async ({ page }) => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('1 selected');

        await dashboardPage.selectFileByName('goose');
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('2 selected');
    });

    test('should have all the action buttons', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);

        await expect(dashboardPage.getActionBar().locator('button.action-btn')).toHaveCount(5);

        for (const name of ['Queue', 'Stop', 'Extract', 'Delete Local', 'Delete Remote'] as const) {
            await expect(dashboardPage.getActionButton(name)).toBeVisible();
        }
    });

    test('should have Queue action enabled for Default state', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();
    });

    test('should have Stop action disabled for Default state', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionButton('Stop')).toBeDisabled();
    });

    test('should expand Done segment to reveal Downloaded and Extracted subs', async () => {
        await expect(dashboardPage.getSubButton('Downloaded')).not.toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).not.toBeVisible();

        await dashboardPage.getSegmentButton('Done').click();

        await expect(dashboardPage.getSubButton('Downloaded')).toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).toBeVisible();
    });

    test('should reveal Pending sub under Active', async () => {
        await expect(dashboardPage.getSubButton('Pending')).not.toBeVisible();

        await dashboardPage.getSegmentButton('Active').click();

        await expect(dashboardPage.getSubButton('Pending')).toBeVisible();
    });

    test('should persist Done filter via URL query param (D-09)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Done').click();

        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
    });

    test('should silently fall back to All and sanitize URL when ?segment= is invalid (D-11)', async ({ page }) => {
        await page.goto('/dashboard?segment=garbage');
        await page.locator('.segment-filters').waitFor({ state: 'visible', timeout: 30000 });

        // Default state: "All" is active
        await expect(dashboardPage.getSegmentButton('All')).toHaveClass(/(^|\s)active(\s|$)/);

        // URL is sanitized — the garbage param is gone
        await expect(page).not.toHaveURL(/segment=garbage/);
    });
});

test.describe.serial('UAT-01: selection and bulk bar', () => {
    let dashboardPage: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        test.setTimeout(120_000);
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        await seedMultiple(page, [
            { file: DELETED_FILE, target: 'DELETED' },
            { file: DOWNLOADED_FILE, target: 'DOWNLOADED' },
            { file: STOPPED_FILE, target: 'STOPPED' },
        ]);
        await ctx.close();
    });

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('UAT-01: per-file selection accumulates and bulk bar reacts', async ({ page }) => {
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        await dashboardPage.selectFileByName(DEFAULT_FILE);
        await expect(dashboardPage.getActionBar()).toBeVisible();
        expect(await dashboardPage.getSelectedCount()).toBe(1);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('1 selected');

        await dashboardPage.selectFileByName(DOWNLOADED_FILE);
        expect(await dashboardPage.getSelectedCount()).toBe(2);
        await expect(page.locator('app-bulk-actions-bar .selection-label')).toHaveText('2 selected');

        await dashboardPage.selectFileByName(STOPPED_FILE);
        expect(await dashboardPage.getSelectedCount()).toBe(3);
    });

    test('UAT-01: shift-range select extends selection to contiguous rows', async () => {
        // Anchor: click first checkbox normally; shift-click a later one.
        // Order is locale-sort dependent on the harness — use files that are definitely visible
        // and rely on the contiguous-range semantic (shift extends from anchor to target).
        await dashboardPage.selectFileByName('clients.jpg');
        await dashboardPage.shiftClickFile('documentation.png');
        // Expect >= 2 selected (exact count depends on row order in the rendered table; this
        // asserts range-extension worked without being fragile to locale-sort divergence).
        const count = await dashboardPage.getSelectedCount();
        expect(count).toBeGreaterThanOrEqual(2);
        await expect(dashboardPage.getActionBar()).toBeVisible();
    });

    test('UAT-01: page-scoped header checkbox selects all visible rows', async ({ page }) => {
        await dashboardPage.clickHeaderCheckbox();

        await expect(dashboardPage.getActionBar()).toBeVisible();
        // Harness loads 9 fixture files in one page (no pagination surface on this data set);
        // header select-all must select every visible row — assert count equals visible row count.
        const visibleRowCount = await page.locator('.transfer-table tbody app-transfer-row').count();
        const selected = await dashboardPage.getSelectedCount();
        expect(selected).toBe(visibleRowCount);
        expect(selected).toBeGreaterThanOrEqual(9);

        // Toggle off — selection clears, bar hides.
        await dashboardPage.clickHeaderCheckbox();
        await expect(dashboardPage.getActionBar()).not.toBeVisible();
    });

    // Spec 4 action/file/variant mapping — each pairing chosen to satisfy backend preconditions
    // so dispatchAndAssert can assert a 'success' toast uniformly per D-05, EXCEPT where the
    // backend contract forbids it (Extract on non-archive fixtures):
    //
    //  Action         Target file            Source state        Backend contract                                        Toast variant
    //  ------         -----------            ------------        ----------------                                        -------------
    //  1 Queue        'testing.gif'          DEFAULT/STOPPED     queue accepted from DEFAULT or STOPPED (remoteSize>0)   success
    //  2 Stop         'testing.gif'          DOWNLOADING         testing.gif is still Syncing from Action 1 (throttled)  success
    //                                        (throttled via       rate_limit=100 ensures file stays Syncing during
    //                                         rate_limit=100)     Action 1 bell interaction and is still Syncing for Stop
    //  3 Extract      DOWNLOADED_FILE        DOWNLOADED          No archive fixtures in harness (RESEARCH Pitfall 3).     (disabled)
    //                 (documentation.png)                         Bulk bar disables Extract when extractable === 0
    //                                                             (isExtractable && isArchive). Assert button disabled,
    //                                                             deselect, and move on.
    //  4 Delete Local DOWNLOADED_FILE        DOWNLOADED          delete_local requires local_size not None               success
    //                 (documentation.png)                         (controller.py:1032-1047). DOWNLOADED guarantees
    //                                                             local_size > 0 → 200 OK + success toast.
    //  5 Delete Remote 'áßç déÀ.mp4'         DEFAULT             delete_remote requires remote_size > 0; DEFAULT         success
    //                                                             harness file satisfies this
    //
    // NOTE: Delete Local target switched from 'illusion.jpg' (STOPPED) to DOWNLOADED_FILE
    //       (documentation.png) because controller.py:1041 requires local_size not None —
    //       DOWNLOADED is the only source state the seed pipeline guarantees local_size > 0
    //       without additional orchestration. STOPPED retains local_size in theory but is
    //       state-timing-dependent on the harness.
    test('UAT-01: bulk bar visibility — 4 actions dispatch + Extract disabled, clear selection, and hide bar', async ({ page }) => {
        // Helper: dispatch one action against a single-file selection, assert UI contract.
        // Bulk actions emit notifications (NotificationService / bell dropdown), not toasts.
        // `notifLevel` 'success' asserts a success notification; 'any' tolerates any level
        // (for Extract on non-archive fixtures per RESEARCH Pitfall 3).
        async function dispatchAndAssert(
            fileName: string,
            action: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote',
            notifKeyword: RegExp,
            notifLevel: 'success' | 'any' = 'success',
        ): Promise<void> {
            await dashboardPage.selectFileByName(fileName);
            await expect(dashboardPage.getActionBar()).toBeVisible();

            await dashboardPage.getActionButton(action).click();

            if (action === 'Delete Local' || action === 'Delete Remote') {
                await dashboardPage.clickConfirmModalConfirm();
            }

            // (a) notification badge dot appears, confirming the backend responded.
            await expect(dashboardPage.getNotificationBadgeDot()).toBeVisible();

            // Open bell and verify notification text.
            await dashboardPage.openNotificationBell();
            if (notifLevel === 'success') {
                await expect(dashboardPage.getNotification('success').first()).toContainText(notifKeyword);
            } else {
                await expect(dashboardPage.getNotification().first()).toBeVisible();
            }
            await dashboardPage.closeNotificationBell();

            // (b) selection cleared — selection-label hidden (getSelectedCount returns 0 when bar not visible)
            await expect(dashboardPage.getActionBar()).not.toBeVisible();
            expect(await dashboardPage.getSelectedCount()).toBe(0);
        }

        // Retry-safe guard: on Playwright retry (retries: 2) the prior attempt may have left
        // testing.gif in DOWNLOADING or DOWNLOADED state, which disables the Queue button.
        // Force-stop any active download so testing.gif returns to a queueable state.
        // Ignore non-OK responses (stop is a no-op if the file is not QUEUED/DOWNLOADING).
        await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
        // Wait briefly for any stop to propagate before proceeding. The file might already be
        // DEFAULT (never queued), STOPPED (just stopped), or DOWNLOADED (finished earlier).
        // We proceed regardless — Queue is enabled for DEFAULT and STOPPED states.
        await page.waitForTimeout(500);

        // Action 1 + 2 share a throttled lftp window.
        //
        // Problem: 'testing.gif' (9 MB) downloads in < 1 s at Docker localhost speeds.
        // After Action 1 dispatches Queue, the file transitions DEFAULT → QUEUED →
        // DOWNLOADING (Syncing) → DOWNLOADED (Synced) before the bell interaction
        // completes (~1-2 s). By the time Action 2 tries to re-queue, the file is
        // DOWNLOADED — Queue is disabled (only DEFAULT/STOPPED are queueable).
        //
        // Fix: throttle lftp to 100 B/s before Action 1's Queue so testing.gif stays
        // in DOWNLOADING (Syncing) throughout Action 1's badge/bell assertions AND
        // is still Syncing when Action 2's Stop is dispatched. This eliminates the
        // re-queue step entirely — Action 2 reuses the same lftp job started by Action 1.
        //
        // The throttle is always restored in the finally block so Actions 3-5 and
        // subsequent tests run at full speed.
        await page.request.get('/server/config/set/lftp/rate_limit/100');
        try {
            // Action 1: Queue testing.gif (now throttled — stays Syncing indefinitely).
            await dashboardPage.selectFileByName('testing.gif');
            await expect(dashboardPage.getActionBar()).toBeVisible();
            await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();
            await dashboardPage.getActionButton('Queue').click();

            // Wait for DOWNLOADING state before checking notification so we confirm the
            // file entered the transfer pipeline (not just acknowledged by the backend).
            await dashboardPage.waitForFileStatus('testing.gif', 'Syncing', 15_000);

            // (a) notification badge dot.
            await expect(dashboardPage.getNotificationBadgeDot()).toBeVisible();

            // Open bell and verify Queue notification text.
            await dashboardPage.openNotificationBell();
            await expect(dashboardPage.getNotification('success').first()).toContainText(/Queued|Re-queued|queued/);
            await dashboardPage.closeNotificationBell();

            // (b) selection cleared.
            await expect(dashboardPage.getActionBar()).not.toBeVisible();
            expect(await dashboardPage.getSelectedCount()).toBe(0);

            // Action 2: Stop — testing.gif is still Syncing (100 B/s throttle keeps it in
            // DOWNLOADING state; Stop requires QUEUED or DOWNLOADING via lftp.kill()).
            await dispatchAndAssert('testing.gif', 'Stop', /Stop|stopped|Stopped/, 'success');
        } finally {
            // Always restore unlimited speed so Actions 3-5 and subsequent tests are not
            // affected by the throttle even if the try block throws.
            await page.request.get('/server/config/set/lftp/rate_limit/0');
        }

        // Action 3: Extract — no harness fixtures are archives (RESEARCH Pitfall 3).
        // The bulk bar disables Extract when extractable === 0 (isExtractable && isArchive).
        // Verify the button is correctly disabled for non-archive files, then deselect.
        await dashboardPage.selectFileByName('documentation.png');
        await expect(dashboardPage.getActionBar()).toBeVisible();
        await expect(dashboardPage.getActionButton('Extract')).toBeDisabled();
        await dashboardPage.selectFileByName('documentation.png'); // deselect
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        // Action 4: Delete Local on DOWNLOADED 'documentation.png'.
        // Per controller.py:1032-1047, delete_local requires local_size not None. DOWNLOADED
        // state guarantees this (extract was a no-op; local_size is untouched). Delete Local
        // opens confirm modal; dispatchAndAssert handles that.
        await dispatchAndAssert('documentation.png', 'Delete Local', /Delete|delete|removed|Removed/, 'success');

        // Action 5: Delete Remote on 'áßç déÀ.mp4' (DEFAULT, remote_size > 0).
        // Delete Remote also opens confirm modal.
        await dispatchAndAssert('áßç déÀ.mp4', 'Delete Remote', /Delete|delete|removed|Removed/, 'success');
    });

    test('UAT-01: FIX-01 union — DELETED row allows Queue (re-queue from remote), alone and mixed with DEFAULT', async ({ page }) => {
        // Part A: DELETED row alone.
        // clients.jpg was pre-seeded to DELETED in beforeAll (queue → Synced → delete_local → Deleted).
        // Retry-safe re-seed: on Playwright retry (retries: 2) prior specs' LRU churn can evict
        // clients.jpg from downloaded_files before this spec asserts. If the guard fails, re-seed
        // DELETED directly rather than flaking on a stale row state.
        try {
            await dashboardPage.waitForFileStatus(DELETED_FILE, 'Deleted', 5_000);
        } catch {
            await seedStatus(page, DELETED_FILE, 'DELETED');
        }

        await dashboardPage.selectFileByName(DELETED_FILE);
        await expect(dashboardPage.getActionBar()).toBeVisible();
        expect(await dashboardPage.getSelectedCount()).toBe(1);

        // FIX-01 core contract: Queue button is enabled for a DELETED-only selection.
        // Pre-fix, Phase 76 documented this as disabled (regression from v1.1.0).
        await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();
        // Delete Remote is also applicable for a DELETED row (remote_size still populated after delete_local).
        await expect(dashboardPage.getActionButton('Delete Remote')).toBeEnabled();

        // Clear selection before Part B (don't dispatch yet — want to prove union behavior first).
        await dashboardPage.clearSelectionViaBar();
        await expect(dashboardPage.getActionBar()).not.toBeVisible();

        // Part B: mixed selection — DELETED + DEFAULT. Union semantics: Queue must still be enabled
        // (applicable to both the DELETED row and the DEFAULT row).
        await dashboardPage.selectFileByName(DELETED_FILE);
        await dashboardPage.selectFileByName(DEFAULT_FILE);
        expect(await dashboardPage.getSelectedCount()).toBe(2);
        await expect(dashboardPage.getActionButton('Queue')).toBeEnabled();

        // Part C: dispatch Queue. Assert UI contract per D-05: success notification + selection cleared + bar hidden.
        await dashboardPage.getActionButton('Queue').click();
        await expect(dashboardPage.getNotificationBadgeDot()).toBeVisible();
        await dashboardPage.openNotificationBell();
        await expect(dashboardPage.getNotification('success').first()).toContainText(/Queued|Re-queued|queued/);
        await dashboardPage.closeNotificationBell();
        await expect(dashboardPage.getActionBar()).not.toBeVisible();
        expect(await dashboardPage.getSelectedCount()).toBe(0);
        // Suppress unused-param warning on `page`; retained in signature to match other specs
        // that destructure it, and to keep future fixture expansion low-friction.
        void page;
    });
});

test.describe.serial('UAT-02: status filter and URL', () => {
    let dashboardPage: DashboardPage;

    test.beforeAll(async ({ browser }) => {
        test.setTimeout(120_000);
        const ctx = await browser.newContext();
        const page = await ctx.newPage();
        const dash = new DashboardPage(page);
        await dash.navigateTo();
        await seedMultiple(page, [
            { file: DELETED_FILE, target: 'DELETED' },
            { file: DOWNLOADED_FILE, target: 'DOWNLOADED' },
            { file: STOPPED_FILE, target: 'STOPPED' },
        ]);
        await ctx.close();
    });

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    // === 4 populated-filter specs (Task 1) ===

    test('UAT-02: status filter pending — Active → Pending shows DEFAULT-state rows', async ({ page }) => {
        await dashboardPage.getSegmentButton('Active').click();
        await dashboardPage.getSubButton('Pending').click();

        // URL written per Phase 73 D-09: ?segment=active&sub=default
        // The sub-filter key is the internal state name "default", not the UI label "Pending".
        await expect(page).toHaveURL(/[?&]segment=active(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=default(&|$)/);

        // Populated: expect >= 1 row visible. DEFAULT bucket contains at least one row —
        // exact composition depends on UAT-01's destructive run order (UAT-01's "all 5
        // actions" spec fires Delete Remote on 'áßç déÀ.mp4', and its Queue/Stop cycle
        // mutates 'testing.gif'; when describe.serial blocks run in file order these
        // rows may be in non-DEFAULT states by the time this spec executes). UAT-02's
        // beforeAll only re-seeds the DELETED/DOWNLOADED/STOPPED fixtures; it does not
        // restore rows that UAT-01 mutated into other states. WR-01.
        const rowCount = await page.locator('.transfer-table tbody app-transfer-row').count();
        expect(rowCount).toBeGreaterThanOrEqual(1);

        // No empty-row placeholder.
        await expect(dashboardPage.getEmptyRow()).not.toBeVisible();
    });

    test('UAT-02: status filter synced — Done → Downloaded shows DOWNLOADED-state rows (Synced badge)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Done').click();
        await dashboardPage.getSubButton('Downloaded').click();

        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=downloaded(&|$)/);

        await expect(dashboardPage.getStatusBadge(DOWNLOADED_FILE)).toContainText('Synced');
        await expect(dashboardPage.getEmptyRow()).not.toBeVisible();
    });

    test('UAT-02: status filter failed — Errors → Failed shows STOPPED-state rows (Failed badge)', async ({ page }) => {
        // Belt-and-braces: UAT-01 may have left lftp in a throttled or active-transfer state
        // that caused illusion.jpg to be re-queued after the beforeAll seed. Re-seed STOPPED
        // if the badge does not already show 'Failed'.
        try {
            await dashboardPage.waitForFileStatus(STOPPED_FILE, 'Failed', 3_000);
        } catch {
            await seedStatus(page, STOPPED_FILE, 'STOPPED');
        }

        await dashboardPage.getSegmentButton('Errors').click();
        await dashboardPage.getSubButton('Failed').click();

        await expect(page).toHaveURL(/[?&]segment=errors(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=stopped(&|$)/);

        await expect(dashboardPage.getStatusBadge(STOPPED_FILE)).toContainText('Failed');
        await expect(dashboardPage.getEmptyRow()).not.toBeVisible();
    });

    test('UAT-02: status filter deleted — Errors → Deleted shows DELETED-state rows (Deleted badge, FIX-01 fixture)', async ({ page }) => {
        // Belt-and-braces: verify beforeAll seed landed before clicking the filter.
        await dashboardPage.waitForFileStatus(DELETED_FILE, 'Deleted', 10_000);

        await dashboardPage.getSegmentButton('Errors').click();
        await dashboardPage.getSubButton('Deleted').click();

        await expect(page).toHaveURL(/[?&]segment=errors(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=deleted(&|$)/);

        await expect(dashboardPage.getStatusBadge(DELETED_FILE)).toContainText('Deleted');
        await expect(dashboardPage.getEmptyRow()).not.toBeVisible();
    });

    // === 4 empty-state filter specs (Task 2) ===

    test('UAT-02: status filter syncing — Active → Syncing empty-state (transient on harness)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Active').click();
        await dashboardPage.getSubButton('Syncing').click();

        await expect(page).toHaveURL(/[?&]segment=active(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=syncing(&|$)/);

        // Pitfall 4: DOWNLOADING is transient — LFTP drains the queue on an idle harness within ms.
        // After beforeAll completes, no files are in DOWNLOADING state. Assert empty-state.
        await expect(dashboardPage.getEmptyRow()).toBeVisible();
        await expect(page.locator('.transfer-table tbody app-transfer-row').filter({ hasNot: page.locator('tr.empty-row') })).toHaveCount(0);
    });

    test('UAT-02: status filter queued — Active → Queued empty-state (transient on harness)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Active').click();
        await dashboardPage.getSubButton('Queued').click();

        await expect(page).toHaveURL(/[?&]segment=active(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=queued(&|$)/);

        // Pitfall 4: QUEUED drains immediately on harness (single LFTP slot, no contention).
        await expect(dashboardPage.getEmptyRow()).toBeVisible();
    });

    test('UAT-02: status filter extracting — Active → Extracting empty-state (no archive fixtures)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Active').click();
        await dashboardPage.getSubButton('Extracting').click();

        await expect(page).toHaveURL(/[?&]segment=active(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=extracting(&|$)/);

        // Pitfall 3: All 9 harness fixtures are image/video/directory — patoolib rejects as non-archives.
        // EXTRACTING is unreachable; assert empty-state.
        await expect(dashboardPage.getEmptyRow()).toBeVisible();
    });

    test('UAT-02: status filter extracted — Done → Extracted empty-state (no archive fixtures)', async ({ page }) => {
        await dashboardPage.getSegmentButton('Done').click();
        await dashboardPage.getSubButton('Extracted').click();

        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=extracted(&|$)/);

        await expect(dashboardPage.getEmptyRow()).toBeVisible();
    });

    // === 2 URL round-trip specs (Task 2) ===

    test('UAT-02: URL round-trip parent — Done segment persists across page.reload()', async ({ page }) => {
        // Start at All (default on navigateTo). Click Done.
        await dashboardPage.getSegmentButton('Done').click();

        // URL writes ?segment=done (no sub selected yet).
        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);

        // Sub-buttons for Done (Downloaded + Extracted) should now be visible per existing expand spec.
        await expect(dashboardPage.getSubButton('Downloaded')).toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).toBeVisible();

        // Reload the page via browser refresh — exercises Angular's ActivatedRoute.queryParamMap hydration.
        // Per D-15: page.reload() NOT page.goto(url). Cold-load via goto is out of scope for this phase.
        await page.reload();

        // Re-await the transfer-table container since navigateTo only runs in beforeEach.
        await page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30_000 });

        // Hydration verified: Done is still active (URL preserved), sub-buttons re-rendered visible.
        await expect(page).toHaveURL(/[?&]segment=done(&|$)/);
        await expect(dashboardPage.getSubButton('Downloaded')).toBeVisible();
        await expect(dashboardPage.getSubButton('Extracted')).toBeVisible();
    });

    test('UAT-02: URL round-trip sub — Errors→Deleted persists across page.reload() (clients.jpg row visible)', async ({ page }) => {
        // Re-guard DELETED fixture — this is the last UAT-02 spec and mutations in earlier specs
        // of the block do not touch clients.jpg, but belt-and-braces.
        await dashboardPage.waitForFileStatus(DELETED_FILE, 'Deleted', 10_000);

        await dashboardPage.getSegmentButton('Errors').click();
        await dashboardPage.getSubButton('Deleted').click();

        await expect(page).toHaveURL(/[?&]segment=errors(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=deleted(&|$)/);

        // Verify filter scoped to Deleted before reload.
        await expect(dashboardPage.getStatusBadge(DELETED_FILE)).toContainText('Deleted');

        // D-15: page.reload() — exercises hydration via queryParamMap.
        await page.reload();
        await page.locator('.transfer-table').waitFor({ state: 'visible', timeout: 30_000 });

        // Post-reload: Errors parent expanded + Deleted sub active + clients.jpg DELETED row visible.
        await expect(page).toHaveURL(/[?&]segment=errors(&|$)/);
        await expect(page).toHaveURL(/[?&]sub=deleted(&|$)/);
        await expect(dashboardPage.getSubButton('Deleted')).toBeVisible();  // sub buttons visible means Errors parent is expanded
        await expect(dashboardPage.getStatusBadge(DELETED_FILE)).toContainText('Deleted');
    });
});
