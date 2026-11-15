import type { APIRequestContext } from '@playwright/test';
import { test, expect } from './fixtures/csp-listener';
import { DashboardPage } from './dashboard.page';

// Multiple path pairs.
//
// The harness starts with the single remote/local path configured by
// setup_seedsyncarr.sh, which the app migrates to one pair named "Default".
// This spec adds a second pair whose remote directory (files-movies) holds a
// file named like one in the first pair, checks that both pairs show up and
// act independently, then removes the pair again so later specs see a single
// pair. Pair changes apply on restart.

const DEFAULT_REMOTE = '/home/remoteuser/files';
const DEFAULT_LOCAL = '/downloads';
const MOVIES = {
    name: 'movies',
    remote_path: '/home/remoteuser/files-movies',
    local_path: '/downloads-movies',
};
// Present in both pairs
const SHARED_FILE = 'joke';
// Present only in the movies pair
const MOVIES_ONLY_FILE = 'movie-only.mkv';

interface PathPair {
    id: string;
    name: string;
    remote_path: string;
    local_path: string;
    enabled: boolean;
    auto_queue: boolean;
}

async function listPairs(request: APIRequestContext): Promise<PathPair[]> {
    const res = await request.get('/server/pathpairs');
    expect(res.ok()).toBeTruthy();
    return (await res.json()).path_pairs as PathPair[];
}

async function isUp(request: APIRequestContext): Promise<boolean> {
    try {
        const res = await request.get('/server/status');
        if (!res.ok()) { return false; }
        return (await res.json()).server?.up === true;
    } catch {
        return false;
    }
}

async function restartApp(request: APIRequestContext): Promise<void> {
    const res = await request.post('/server/command/restart');
    expect(res.ok()).toBeTruthy();
    // Wait for the old process to go away before waiting for the new one
    await expect.poll(() => isUp(request), { timeout: 20_000, intervals: [500] }).toBe(false);
    await expect.poll(() => isUp(request), { timeout: 90_000, intervals: [1_000] }).toBe(true);
}

async function waitForRemoteScan(request: APIRequestContext): Promise<void> {
    await expect.poll(async () => {
        const res = await request.get('/server/status');
        return (await res.json()).controller?.latest_remote_scan_time ?? null;
    }, { timeout: 90_000, intervals: [1_000] }).not.toBeNull();
}

test.describe('Multiple path pairs', () => {
    test.describe.configure({ mode: 'serial' });

    test.beforeAll(async ({ request }) => {
        // Start from one pair even if an earlier run left the second one behind
        for (const pair of await listPairs(request)) {
            if (pair.name === MOVIES.name) {
                await request.post(`/server/pathpairs/delete/${encodeURIComponent(pair.id)}`);
            }
        }
    });

    test.afterAll(async ({ request }) => {
        let changed = false;
        for (const pair of await listPairs(request)) {
            if (pair.name === MOVIES.name) {
                await request.post(`/server/pathpairs/delete/${encodeURIComponent(pair.id)}`);
                changed = true;
            }
        }
        if (changed) {
            await restartApp(request);
            await waitForRemoteScan(request);
        }
    });

    test('migrates the single configured path to one Default pair', async ({ request }) => {
        const pairs = await listPairs(request);
        expect(pairs).toHaveLength(1);
        expect(pairs[0]).toMatchObject({
            id: 'default',
            name: 'Default',
            remote_path: DEFAULT_REMOTE,
            local_path: DEFAULT_LOCAL,
            enabled: true,
        });
    });

    test('rejects invalid and conflicting pairs', async ({ request }) => {
        const relative = await request.post('/server/pathpairs/create', {
            data: { ...MOVIES, local_path: 'relative/path' },
        });
        expect(relative.status()).toBe(400);

        const sameLocal = await request.post('/server/pathpairs/create', {
            data: { ...MOVIES, local_path: DEFAULT_LOCAL },
        });
        expect(sameLocal.status()).toBe(409);

        const pairs = await listPairs(request);
        expect(pairs).toHaveLength(1);
    });

    test('adds a second pair and applies it after a restart', async ({ request }) => {
        const created = await request.post('/server/pathpairs/create', { data: MOVIES });
        expect(created.status()).toBe(201);
        expect((await created.json()).restart_required).toBe(true);

        const pairs = await listPairs(request);
        expect(pairs.map(p => p.name).sort()).toEqual(['Default', 'movies']);

        await restartApp(request);
        await waitForRemoteScan(request);
    });

    test('shows the files of both pairs, with the same name once per pair', async ({ page }) => {
        const dashboard = new DashboardPage(page);
        await dashboard.navigateTo();
        // 9 files of the first pair and 2 of the second
        await dashboard.waitForAtLeastFileCount(11, 60_000);

        await expect(page.locator('.transfer-table th.col-pair')).toBeVisible();
        const names = (await dashboard.getFiles()).map(f => f.name);
        expect(names.filter(n => n === SHARED_FILE)).toHaveLength(2);
        expect(names).toContain(MOVIES_ONLY_FILE);

        const pairCells = await page.locator('.transfer-table tbody td.cell-pair').allTextContents();
        expect(pairCells.filter(c => c.trim() === 'movies')).toHaveLength(2);
        expect(pairCells.filter(c => c.trim() === 'Default')).toHaveLength(9);
    });

    test('filters the file list by pair', async ({ page }) => {
        const dashboard = new DashboardPage(page);
        await dashboard.navigateTo();
        await dashboard.waitForAtLeastFileCount(11, 60_000);

        const filter = page.locator('select.pair-filter');
        await expect(filter).toBeVisible();
        await filter.selectOption({ label: 'movies' });
        await expect.poll(async () => (await dashboard.getFiles()).map(f => f.name).sort())
            .toEqual([SHARED_FILE, MOVIES_ONLY_FILE].sort());

        await filter.selectOption({ label: 'All pairs' });
        await dashboard.waitForAtLeastFileCount(11);
    });

    test('routes a command to the pair it names', async ({ request }) => {
        // A name that exists in both pairs is ambiguous without a pair
        const ambiguous = await request.post(`/server/command/stop/${encodeURIComponent(SHARED_FILE)}`);
        expect(ambiguous.status()).toBe(400);
        expect(await ambiguous.text()).toContain('more than one path pair');

        // An unknown pair is refused instead of falling back to another pair
        const unknown = await request.post(
            `/server/command/stop/${encodeURIComponent(SHARED_FILE)}?pair_id=nope`);
        expect(unknown.status()).toBe(404);

        // Naming the pair reaches the file of that pair
        const pairs = await listPairs(request);
        const movies = pairs.find(p => p.name === MOVIES.name)!;
        const named = await request.post(
            `/server/command/queue/${encodeURIComponent(MOVIES_ONLY_FILE)}` +
            `?pair_id=${encodeURIComponent(movies.id)}&release_unverified=true`);
        expect(named.status()).toBe(200);
    });

    test('bulk actions carry the pair per file', async ({ request }) => {
        const pairs = await listPairs(request);
        const movies = pairs.find(p => p.name === MOVIES.name)!;
        const res = await request.post('/server/command/bulk', {
            data: {
                action: 'stop',
                files: [
                    { name: SHARED_FILE, pair_id: movies.id },
                    { name: SHARED_FILE, pair_id: 'default' },
                ],
            },
        });
        expect(res.status()).toBe(200);
        const body = await res.json();
        expect(body.results.map((r: { pair_id: string }) => r.pair_id).sort()).toEqual(['default', movies.id].sort());
    });

    test('removes the second pair again', async ({ request }) => {
        const pairs = await listPairs(request);
        const movies = pairs.find(p => p.name === MOVIES.name)!;
        const res = await request.post(`/server/pathpairs/delete/${encodeURIComponent(movies.id)}`);
        expect(res.ok()).toBeTruthy();

        await restartApp(request);
        await waitForRemoteScan(request);
        expect(await listPairs(request)).toHaveLength(1);
    });
});
