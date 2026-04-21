import type { Page } from '@playwright/test';

// Typed seed API — see .planning/phases/77-deferred-playwright-e2e-phases-72-73
// UAT-01 and UAT-02 describe blocks consume these helpers from test.beforeAll.

export type SeedTarget = 'DOWNLOADED' | 'STOPPED' | 'DELETED';

export interface SeedPlanItem {
    file: string;
    target: SeedTarget;
}

// Backend command endpoints (controller.py:66-72). encodeURIComponent on every
// file name — harness fixtures include Unicode names (e.g. 'áßç déÀ.mp4', 'üæÒ').
const ENDPOINT = {
    queue:        (n: string) => `/server/command/queue/${encodeURIComponent(n)}`,
    stop:         (n: string) => `/server/command/stop/${encodeURIComponent(n)}`,
    extract:      (n: string) => `/server/command/extract/${encodeURIComponent(n)}`,
    deleteLocal:  (n: string) => `/server/command/delete_local/${encodeURIComponent(n)}`,
    deleteRemote: (n: string) => `/server/command/delete_remote/${encodeURIComponent(n)}`,
};

// Display labels rendered by transfer-row.component.ts:49-58. Seed helpers
// poll for these strings in td.cell-status .status-badge — never raw enum names.
const LABEL = {
    DOWNLOADED:  'Synced',
    STOPPED:     'Failed',
    DELETED:     'Deleted',
    DOWNLOADING: 'Syncing',
    QUEUED:      'Queued',
} as const;

function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function expectOk(page: Page, url: string, method: 'POST' | 'DELETE'): Promise<void> {
    const res = method === 'POST'
        ? await page.request.post(url)
        : await page.request.delete(url);
    if (!res.ok()) {
        throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
    }
}

// Row-scoped badge polling. Mirrors dashboard.page.ts:53-58 Locator-chain shape
// (anchored ^...$ regex to avoid joke/joke.png prefix collisions). Default 30s
// absorbs LFTP spawn + SSH setup + SSE propagation on the harness.
async function waitForBadge(page: Page, name: string, label: string, timeout = 30_000): Promise<void> {
    const row = page.locator('.transfer-table tbody app-transfer-row', {
        has: page.locator('td.cell-name .file-name', {
            hasText: new RegExp(`^${escapeRegex(name)}$`),
        }),
    });
    await row.locator('td.cell-status .status-badge').filter({ hasText: label }).waitFor({ timeout });
}

export async function queueFile(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.queue(name), 'POST');
}

export async function stopFile(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.stop(name), 'POST');
}

export async function deleteLocal(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.deleteLocal(name), 'DELETE');
}

export async function deleteRemote(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.deleteRemote(name), 'DELETE');
}

export async function extractFile(page: Page, name: string): Promise<void> {
    await expectOk(page, ENDPOINT.extract(name), 'POST');
}

export async function seedStatus(page: Page, file: string, target: SeedTarget): Promise<void> {
    if (target === 'DOWNLOADED') {
        await expectOk(page, ENDPOINT.queue(file), 'POST');
        await waitForBadge(page, file, LABEL.DOWNLOADED);
        return;
    }
    if (target === 'STOPPED') {
        await expectOk(page, ENDPOINT.queue(file), 'POST');
        // WR-02: DOWNLOADING is transient on the harness (Pitfall 4 — LFTP drains the
        // queue on an idle harness within ms for small files like clients.jpg at 40 KB
        // or illusion.jpg at 80 KB). Race DOWNLOADING vs DOWNLOADED: whichever label
        // appears first ends the wait. If we missed the transient window and landed on
        // DOWNLOADED, stop is a no-op and the subsequent STOPPED wait would never
        // resolve — fail fast with a clear, distinguishable error instead of timing
        // out at 30s on an unreachable state.
        const row = page.locator('.transfer-table tbody app-transfer-row', {
            has: page.locator('td.cell-name .file-name', {
                hasText: new RegExp(`^${escapeRegex(file)}$`),
            }),
        });
        await row
            .locator('td.cell-status .status-badge')
            .filter({ hasText: new RegExp(`^(${LABEL.DOWNLOADING}|${LABEL.DOWNLOADED})$`) })
            .waitFor({ timeout: 30_000 });
        // Re-read the badge after the race to detect which branch we landed on.
        const settledLabel = (await row.locator('td.cell-status .status-badge').textContent())?.trim() ?? '';
        if (settledLabel === LABEL.DOWNLOADED) {
            throw new Error(
                `Seed STOPPED for '${file}' missed the transient DOWNLOADING window — ` +
                `file already reached DOWNLOADED ('${LABEL.DOWNLOADED}'). Stop is a no-op from ` +
                `this state; cannot reach STOPPED. Pick a larger fixture or re-queue.`,
            );
        }
        await expectOk(page, ENDPOINT.stop(file), 'POST');
        await waitForBadge(page, file, LABEL.STOPPED);
        return;
    }
    if (target === 'DELETED') {
        // FIX-01 fixture survival: must reach DOWNLOADED first so the file
        // enters the downloaded_files LRU (model_builder.py:516-534
        // _check_deleted_state requires local_size is None AND name in LRU
        // AND state was DEFAULT). Local-delete only — chaining a remote
        // delete purges the row on the next model diff tick.
        await expectOk(page, ENDPOINT.queue(file), 'POST');
        await waitForBadge(page, file, LABEL.DOWNLOADED);
        await expectOk(page, ENDPOINT.deleteLocal(file), 'DELETE');
        await waitForBadge(page, file, LABEL.DELETED);
        return;
    }
    throw new Error(`Unknown seed target: ${target}`);
}

export async function seedMultiple(page: Page, plan: SeedPlanItem[]): Promise<void> {
    // Sequential: harness runs workers: 1 and LFTP contention makes parallel unsafe.
    for (const item of plan) {
        await seedStatus(page, item.file, item.target);
    }
}
