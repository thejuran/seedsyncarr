# Phase 74: Storage capacity tiles - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 74-storage-capacity-tiles
**Areas discussed:** Tile layout & slots, Number formatting, Threshold warnings, Refresh & failure UX

---

## Tile layout & slots

### Q: When capacity is available, how should the main number row read?

| Option | Description | Selected |
|--------|-------------|----------|
| % as value, 'of X GB' as unit | stat-value = '65%', stat-unit = 'of 185 GB'. Cleanest mapping into existing slots. | ✓ |
| % with inline 'of X GB' in value slot | stat-value = '65% of 185 GB' as one string. One-line read but loses big-number visual. | |
| X GB as value, '% of total' as unit | stat-value = '120 GB', stat-unit = '65% of 185'. Lead with absolute used bytes. | |

**User's choice:** % as value, 'of X GB' as unit (recommended)

### Q: Where does the 'used' detail go?

| Option | Description | Selected |
|--------|-------------|----------|
| New sub-line below progress bar | '120 GB used' under the bar, like Download Speed's 'Peak: …'. | ✓ |
| New sub-line above progress bar | Between value row and progress bar; pushes bar down. | |
| Skip — percentage + total is enough | Saves vertical space; used bytes is derivable. | |

**User's choice:** New sub-line below progress bar (recommended)

### Q: What does the progress bar represent in capacity mode?

| Option | Description | Selected |
|--------|-------------|----------|
| used / total | Bar width = used/total×100. Matches design spec. | ✓ |
| used / total, but keep existing fill color | Same math but preserve color-by-tile convention. | |
| Keep ratio bar, add a separate capacity micro-bar | Two bars per tile — more info, more clutter. | |

**User's choice:** used / total (recommended — matches design spec)

### Q: Tile icons & header in capacity mode — any change?

| Option | Description | Selected |
|--------|-------------|----------|
| Unchanged | Keep fa-cloud / fa-database icons + amber accent + existing labels. | ✓ |
| Subtle icon adornment in capacity mode | Add a small disk overlay or watermark change. | |

**User's choice:** Unchanged (recommended)

---

## Number formatting

### Q: Percentage precision in the main value slot?

| Option | Description | Selected |
|--------|-------------|----------|
| Integer only — '65%' | Round to nearest integer. Matches design spec example. | ✓ |
| One decimal — '65.3%' | Always one decimal. More precise but visually busier. | |
| Adaptive — integer normally, one decimal when 90–99% | Extra precision in high-fill range; more template logic. | |

**User's choice:** Integer only — '65%' (recommended)

### Q: Unit handling for the 'of X GB' total?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse fileSize pipe — 'of 1.86 TB' / 'of 466 GB' etc | Existing FileSizePipe with 2 decimals. Auto-scales unit. | ✓ |
| Force GB scale — 'of 1860 GB' | Always GB. Easier mental comparison but big disks read awkwardly. | |
| fileSize pipe with 1 decimal — 'of 1.9 TB' | Tighter, less precise. | |

**User's choice:** Reuse fileSize pipe with 2 decimals (recommended)

### Q: How does the 'X used' sub-line format?

| Option | Description | Selected |
|--------|-------------|----------|
| fileSize:2 + literal 'used' — '120.50 GB used' | Same precision as 'of X GB'; visually aligned. | ✓ |
| fileSize:1 + 'used' — '120.5 GB used' | One decimal for compactness. | |
| Match existing 'Tracked' style — split spans | Maximum visual continuity with non-capacity mode. | |

**User's choice:** fileSize:2 + literal 'used' (recommended)

### Q: Bytes vs bibytes — the 'X GB' figures use which base?

| Option | Description | Selected |
|--------|-------------|----------|
| Whatever fileSize pipe currently does | Don't introduce a new convention; backend ships raw bytes. | ✓ |
| Switch capacity tiles to GiB (binary base) | df / disk_usage are byte-accurate; binary base lines up with disk vendors. | |

**User's choice:** Whatever fileSize pipe currently does (recommended)

---

## Threshold warnings

### Q: Should the tile visually warn when capacity gets dangerously full?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — progress bar color shifts at thresholds | Bar turns warning at >80%, danger at >95%. Standard disk-dashboard UX. | ✓ |
| Yes — only color the percentage number, leave bar fixed | Subtler warning. | |
| No — stay neutral, let the user read the number | Simplest, no opinionated thresholds. | |

**User's choice:** Yes — progress bar color shifts at thresholds (recommended)

### Q: If thresholds are used — which exact values?

| Option | Description | Selected |
|--------|-------------|----------|
| Warn 80%, danger 95% | Industry-standard split. | ✓ |
| Warn 85%, danger 95% | Slightly later warning. | |
| Warn 90%, danger 98% | 'Don't cry wolf' aligned. | |
| Skip — we chose neutral above | (n/a — thresholds were chosen) | |

**User's choice:** Warn 80%, danger 95% (recommended)

### Q: What CSS tokens drive the warning colors?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing semantic tokens (success/warning/danger) | Bootstrap variant classes already used elsewhere. Zero new tokens. | ✓ |
| Add dedicated capacity-warning tokens | New SCSS vars for color flexibility; more surface area. | |
| Skip — we chose neutral above | (n/a) | |

**User's choice:** Reuse existing semantic tokens (recommended)

---

## Refresh & failure UX

### Q: How should remote df be triggered?

| Option | Description | Selected |
|--------|-------------|----------|
| Once per remote scan cycle | Piggyback on existing remote scan SSH session. | ✓ |
| Once per remote scan, but throttled to ≥N seconds | Defends against rapid back-to-back scans. | |
| Independent timer (e.g., every 60s) | Decoupled cadence; spawns extra SSH sessions. | |

**User's choice:** Once per remote scan cycle (recommended)

### Q: What does the tile show before the first capacity value arrives?

| Option | Description | Selected |
|--------|-------------|----------|
| Show fallback (tracked-bytes) until non-null capacity arrives | Cold load = current behavior; flip to capacity on first non-null SSE. | ✓ |
| Show '—' / loading skeleton in the value slot | Explicit loading affordance. | |
| Default to '0%' with empty bar | Simplest template; visually misleading. | |

**User's choice:** Show fallback (tracked-bytes) until non-null capacity arrives (recommended)

### Q: If only one side reports capacity, how do tiles behave?

| Option | Description | Selected |
|--------|-------------|----------|
| Independent fallback per tile | Each tile evaluates its own (total, used) pair. | ✓ |
| Both-or-nothing | If either is null, both fall back. Symmetric but hides good local data. | |

**User's choice:** Independent fallback per tile (recommended)

### Q: How are SSH df parse failures surfaced?

| Option | Description | Selected |
|--------|-------------|----------|
| Silent fallback + log warning | Parse failure → None values + WARN log. Mirrors Phase 73's URL silent fallback. | ✓ |
| Fallback + surface error_msg on Status.ServerStatus | Single place to show 'why is capacity missing?'. More plumbing. | |
| Retry once per scan, then fall back | Slightly more resilient; modest extra complexity. | |

**User's choice:** Silent fallback + log warning (recommended)

---

## Claude's Discretion

- df -B1 output parser strategy
- Exact `@if` selector / class layout switching capacity vs fallback templates
- Threshold computation location (template vs derived DashboardStats field)
- Where the `>1%` change check lives (controller vs property setter)
- Whether warning/danger fill classes scope to a new modifier or extend the existing rule

## Deferred Ideas

- Capacity history / trend sparkline
- User-configurable thresholds
- Toast/notification on threshold crossing
- Multi-mount enumeration
- E2E coverage of capacity rendering (deferred per design spec)
- df retry-on-parse-failure
- Surfacing df failures via Status.ServerStatus.error_msg
