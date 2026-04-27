/**
 * Escape special regex characters in a string so it can be used as a literal
 * pattern inside `new RegExp(...)`.
 *
 * Extracted from dashboard.page.ts and fixtures/seed-state.ts (E2EFIX-07).
 */
export function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
