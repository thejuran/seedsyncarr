import type { Page } from '@playwright/test';
import { escapeRegex } from '../helpers';

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

// Config set endpoint — used to throttle lftp downloads so the stop command
// can catch a file in QUEUED/DOWNLOADING state (rate_limit in bytes/sec).
const CONFIG_SET = (section: string, key: string, value: string) =>
    `/server/config/set/${section}/${key}/${encodeURIComponent(value)}`;

// Display labels rendered by transfer-row.component.ts:49-58. Seed helpers
// poll for these strings in td.cell-status .status-badge — never raw enum names.
const LABEL = {
    DOWNLOADED:  'Synced',
    STOPPED:     'Failed',
    DELETED:     'Deleted',
    DOWNLOADING: 'Syncing',
    QUEUED:      'Queued',
} as const;

// Rate limit applied before the STOPPED seed loop to ensure lftp downloads
// slowly enough for the stop command to catch the file mid-transfer.
// 100 bytes/sec is aggressive but reliable on fast Docker networks where
// even 10MB files finish in <100ms at full speed.
const STOPPED_SEED_RATE_LIMIT = '100';

async function expectOk(page: Page, url: string, method: 'POST' | 'DELETE' | 'GET'): Promise<void> {
    let res;
    if (method === 'POST') {
        res = await page.request.post(url);
    } else if (method === 'DELETE') {
        res = await page.request.delete(url);
    } else {
        res = await page.request.get(url);
    }
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

async function setRateLimit(page: Page, bytesPerSec: string): Promise<void> {
    await expectOk(page, CONFIG_SET('lftp', 'rate_limit', bytesPerSec), 'GET');
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
        // Throttle lftp to 100 B/s so the download takes long enough for the
        // stop command to catch it in QUEUED or DOWNLOADING state. Without
        // throttling, even multi-MB files finish in <100ms on fast Docker
        // networks, making the stop race unwinnable.
        await setRateLimit(page, STOPPED_SEED_RATE_LIMIT);
        try {
            const MAX_ATTEMPTS = 5;
            for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
                await expectOk(page, ENDPOINT.queue(file), 'POST');
                const stopRes = await page.request.post(ENDPOINT.stop(file));
                if (stopRes.ok()) {
                    await waitForBadge(page, file, LABEL.STOPPED);
                    return;
                }
                if (attempt < MAX_ATTEMPTS) {
                    await waitForBadge(page, file, LABEL.DOWNLOADED, 30_000);
                    await expectOk(page, ENDPOINT.deleteLocal(file), 'DELETE');
                    await waitForBadge(page, file, LABEL.DELETED);
                }
            }
            throw new Error(
                `Seed STOPPED for '${file}' failed after ${MAX_ATTEMPTS} attempts — ` +
                `stop command never caught the file in QUEUED/DOWNLOADING state.`,
            );
        } finally {
            // Always restore unlimited speed so subsequent seeds (DOWNLOADED,
            // DELETED) are not artificially slow.
            await setRateLimit(page, '0');
        }
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
