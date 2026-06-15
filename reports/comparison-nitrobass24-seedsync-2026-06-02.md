# SeedSyncarr vs. nitrobass24/seedsync — Comparison Report

**Date:** 2026-06-02
**Author:** research session (Claude)
**Scope:** Read-only comparison of this repo (SeedSyncarr, `thejuran`) against the external fork
`nitrobass24/seedsync`, with a deep-dive on the Sonarr/Radarr (*arr) integration.

---

## TL;DR

- Both repos are **sibling forks of `ipsingh06/seedsync`** (the original, unmaintained since Dec 2020).
  Neither is upstream of the other.
- They have **independently converged** on nearly the same architecture (Bottle backend, Angular 21 SPA,
  LFTP+pexpect core, REST+SSE, multi-arch Alpine Docker, path pairs).
- The external fork is **actively developed** (last push 2026-06-02, the same day as this analysis;
  v0.18.1, 49★, Unraid Community App listing).
- The most strategically important difference is the **\*arr integration**, and the key insight is:
  **the two integrations solve *different problems*, not the same problem in opposite directions.**

---

## 1. Lineage

Both descend from **`ipsingh06/seedsync`** (Apache-2.0). They are cousins, not parent/child.
Both retain the original copyright headers, the LFTP+pexpect sync core, the Bottle backend,
the Angular SPA shell, the SSE model-push pattern, and the `scan_fs.py` remote-scanner trick.

## 2. Identity & activity

| | **SeedSyncarr (this repo)** | **nitrobass24/seedsync** |
|---|---|---|
| Owner | thejuran | nitrobass24 |
| Version scheme | v1.x (currently 1.3.0, → v1.4.0 "launch hardening") | v0.x (currently 0.18.1) |
| Default branch | `main` (single-branch) | `develop` → `master` (gitflow) |
| Created | — | Nov 30 2024 |
| Last push | active working branch | **2026-06-02** (same day as report) |
| Stars / forks / issues | pre-public | 49★ / 5 forks / 15 open issues |
| Docs site | MkDocs Material (`src/python/site/`) | Docusaurus (`website/`, Cloudflare `wrangler.toml`) |
| Branding | Custom "SeedSyncarr" wordmark + dashboard screenshot | Original seedsync logo |

## 3. Tech stack — nearly identical

Both: **Python + Bottle** backend, **Angular 21 + Bootstrap 5.3** SPA, REST + SSE transport,
`lftp`/`ssh` CLIs via `pexpect`, multi-arch Alpine Docker on port 8800, GitHub Actions CI, Playwright E2E.

Minor divergences:
- **Python target:** this repo pins `>=3.11,<3.13`; external targets 3.13.
- **Packaging:** this repo carries both Poetry *and* PEP-621/hatchling, plus `cryptography`, `paste`,
  `patool`. External dropped Poetry (pip), removed `paste` (Bottle built-in WSGI), replaced `patool`
  with direct `7z` subprocess calls.
- **Angular unit tests:** external migrated to **Vitest**; this repo still on **Karma + Jasmine**.
- **Icons:** this repo uses Phosphor; external uses Font Awesome 7.

## 4. Feature set — convergent, different emphases

Both independently built: multiple path pairs, per-pair LFTP/scanner, Auto-Queue, exclude patterns,
multi-select bulk actions, auto-extract, Sonarr/Radarr, optional API-key auth + CSP/CSRF/rate-limiting,
dark mode.

Genuine divergences:

| Capability | **SeedSyncarr** | **nitrobass24** |
|---|---|---|
| Secrets at rest (Fernet encryption, `secrets.key` 0600) | **Yes** (`common/encryption.py`) | **No** (plaintext config) |
| SSRF protection on outbound *arr test calls | **Yes** (`_validate_url` rejects private/loopback IPs) | scheme check only |
| Multi-instance *arr + per-pair routing | No (single `[Sonarr]`/`[Radarr]` INI) | **Yes** (`integrations.json`, `arr_target_ids`) |
| Discord / Telegram notification presets | No | **Yes** (`notifier.py`, `notification_formatters.py`) |
| Staging + post-download validation pipeline | No | **Yes** (`controller/move/`, `controller/validate/`) |
| Image size / dep leanness (no paste/patool/poetry) | heavier | **leaner** |

## 5. Internal architecture — same shape, different decomposition

Both decomposed the original monolithic `Controller` for complexity (C901) compliance, but named/split
the pieces differently:

| Concern | **SeedSyncarr** | **nitrobass24** |
|---|---|---|
| Model build/diff pipeline | `model_pipeline.py` | `model_updater.py` + `model_registry.py` |
| Command execution | `command_processor.py` | `command_pipeline.py` |
| Per-pair state | (in controller managers) | `pair_context.py` (`PairContext`) |
| Manager split | `scan_manager`, `lftp_manager`, `file_operation_manager`, `webhook_manager`, `auto_delete_manager`, `memory_monitor` | folded into `pair_context` + pipelines |

This repo is **more granular on the manager axis** (six managers + `MemoryMonitor` leak detection,
which external lacks). External is **more granular on the per-pair axis** (`PairContext` as the unit
of isolation).

## 6. Code size & test investment

| Metric (LOC) | **SeedSyncarr** | **nitrobass24** |
|---|---|---|
| Python (non-test) | 11,336 | 13,081 |
| Python tests | **26,819** | 23,626 |
| Angular app (no specs) | 7,124 | 5,289 |
| Angular specs | **11,744** | 6,643 |
| Test:code ratio (Python) | **2.37:1** | 1.81:1 |

This repo carries substantially more test code per line shipped. External ships more *product* code
(staging, multi-instance, notifications). External advertises 828 Python / 412 Angular / 95 E2E tests.

## 7. Process / tooling

- External also uses Claude Code (`CLAUDE.md` with strict gitflow) plus `.coderabbit.yaml` (CodeRabbit AI review).
- This repo uses GSD / `.planning/` + deep-review setup.
- External wrote a `MODERNIZATION_PLAN.md` documenting the fork journey (439 MB → 45 MB image,
  Angular 4→21, Poetry removed, Debian dropped, unrar→7z).

---

## 8. The \*arr integration — deep dive (the important part)

**Key insight: these are NOT the same feature pointed in opposite directions. They solve different problems.**

### SeedSyncarr — inbound webhook (this repo)
- Files: `web/handler/webhook.py` (222 LOC), `controller/webhook_manager.py` (92 LOC).
- Flow: Sonarr/Radarr POST a `Download` event **to** SeedSyncarr → extract filename
  (3-level fallback: `sourcePath` basename → `releaseTitle` → series/movie title) →
  match case-insensitively against the model → feed **auto-delete**.
- **Purpose: cleanup coordination.** "*arr imported this, so it's safe for me to delete it."
  Closes the *back half* of the lifecycle.
- Security: HMAC-SHA256 verified, constant-time compare, fail-closed option (503 when
  `webhook_require_secret` set but no secret), 1 MB body cap, rate-limited 60/60s,
  log-injection (CWE-117) sanitized. **Substantially more hardened than external's outbound path.**

### nitrobass24 — outbound push (external)
- File: `controller/arr_notifier.py` (`ArrNotifier(IModelListener)`).
- Flow: when a file hits `DOWNLOADED`, POST `{"name": "DownloadedEpisodesScan"|"DownloadedMoviesScan",
  "path": ...}` to *arr `/api/v3/command`, routed to every enabled instance in the pair's `arr_target_ids`.
- **Purpose: import triggering.** "I downloaded this — *arr, go scan/import it now."
  Drives the *front half* of the lifecycle.
- Multi-instance + per-pair routing (e.g. 4K pair fires only 4K Radarr).
- Weaknesses: fire-and-forget (swallows all exceptions, no UI feedback, no retry);
  **path-mapping fragility** (sends `local_path + full_path`; breaks under Docker remote-path-mapping
  mismatch — the #1 *arr support issue); thread-per-event, unbounded; no SSRF filtering
  (arguably correct since *arr targets are legitimately private IPs).

### Why the outbound push matters less than it first appears

Sonarr discovers new files two ways:
1. **It's tracking the download** (Sonarr initiated the search → it polls the client → imports promptly).
2. **Periodic library rescan** (default every 6–12h) for files that just *appear* in a monitored folder.

The outbound push only helps case (2) — the **decoupled / manually-sourced workflow** where the seedbox
acquires files Sonarr never asked for, so Sonarr only finds them on its slow scheduled rescan.

**If Sonarr drives the searches** (Sonarr is tracking the download in its queue), there is **no
meaningful lag** and the push buys nothing — it's redundant.

### The two forks encode different homelab philosophies

- **SeedSyncarr ("Sonarr drives"):** Sonarr is the brain. SeedSyncarr is fast transport for what Sonarr
  requested. The only thing worth coordinating is "tell me when you've imported, so I can safely reclaim
  disk." → **inbound HMAC webhook → safe auto-delete.**
- **nitrobass24 ("seedbox-first"):** the seedbox/SeedSync is the brain. Files arrive Sonarr didn't request,
  so SeedSync must poke Sonarr to look. → **outbound push.**

Neither is wrong. They reflect different assumptions about who's in charge.

---

## 8b. Staging directory — what it buys (and whether it's worth copying)

External has a **staging directory** feature (`controller/move/move_process.py`, `/staging` volume).
What it's for: homelabs with **two storage tiers** — fast scratch (NVMe/SSD) + slow bulk (spinning
array / NAS). Downloads land on the fast tier, then *move* to the final location on completion.

What it buys:
1. **Fast disk absorbs LFTP write churn.** Parallel/segmented LFTP writes are random/out-of-order —
   terrible for spinning disks and parity arrays (unRAID, RAIDZ). Staging on SSD keeps the messy random
   I/O on flash; the bulk array only ever sees one clean sequential copy at the end. **Biggest real win,
   especially on unRAID** (their target — they have an Unraid Community App listing).
2. **Extraction on fast storage.** Unpacking RAR/7z on NVMe is far faster and spares the array a second
   round of random I/O. Composes with their extract pipeline.
3. **No partial/corrupt files in the library.** Final location only receives complete files via an
   atomic-ish move; *arr never sees a half-written `.mkv`. Pairs with their `validate/` checksum step
   (validate on staging → move only what passed). A correctness guarantee, not just speed.
4. **unRAID cache→array synergy.** Maps onto the idiomatic "download to cache, move to array" model.

**The catch:** the move is cheap (metadata rename) only if `/staging` and `/downloads` are on the **same
filesystem**. Across filesystems it's a full copy+delete — doubling I/O. The tiered setup that most wants
staging (NVMe staging + separate array) is exactly the one where the move is most expensive. Inherent
tension.

**Verdict for this repo:** the author runs a **single NAS, no storage tiers** — so staging buys *nothing*
for the author's own use; it'd add a config knob + move step with no benefit. It is **only** an adoption
play for the tiered-storage / unRAID crowd. That said, it's a *more defensible* feature to copy than the
outbound *arr push: staging solves a common, platform-agnostic **hardware-topology** problem, whereas the
push solves a workflow-specific (seedbox-first) one. If courting unRAID users ever becomes a goal, staging
is the higher-value port. If not, skip it.

---

## 9. Where we landed (positioning)

**Decision context:** the goal is real adoption (the author works harder on, and wants people using,
public repos). The question was whether to advertise given how similar the two forks are, and how to
frame the *arr integration.

**Conclusion:**

1. **Worth maintaining as a public, polished project** — the public bar is the author's forcing function
   for quality, independent of adoption. Keep the discipline; the *marketing* grind (Reddit/Unraid
   promotion) is optional and need not be paid head-to-head against an established sibling.

2. **\*arr framing — directional, not superior.** Do NOT claim a blanket "unique *arr integration"
   (external has one too, and a richer multi-instance UI). Claim uniqueness on the **axis actually owned**:
   a Sonarr-driven workflow where a **secure (HMAC-verified) import webhook drives safe auto-delete** —
   so you never delete a file that didn't make it into the library. External does not have this.

3. **Suggested README line:**
   > "SeedSyncarr is built for a Sonarr-driven workflow: Sonarr drives the searches, SeedSyncarr handles
   > fast transport, and a secure (HMAC-verified) import webhook lets SeedSyncarr safely reclaim disk
   > space only *after* your import succeeds — so you never delete a file that didn't make it into your
   > library."

4. **Honesty guardrails for the write-up:**
   - Frame the absence of outbound push as **focus / chosen scope**, not as a deliberate advantage.
   - Do not imply "we don't clutter Sonarr with API calls" — it isn't a feature, it's a scope choice.
   - "Pick your user" (Sonarr-driven crowd) beats "claim everyone."

5. **Differentiators to lead with:** encryption at rest, SSRF hardening, deeper test suite (the last is a
   *contributor* signal, not a user-facing one — keep it out of the user pitch).

6. **External's user-facing gaps this repo could consider later** (only if they fit the author's own
   workflow / adoption goals — don't build to match a checklist): multi-instance *arr with per-pair
   routing, Discord/Telegram notification presets, staging + post-download validation. The outbound push
   itself is **not** worth building for a "Sonarr drives" user — it solves a problem that workflow doesn't
   have.

---

## Appendix — method

- `/gsd:map-codebase` agents read the local filesystem only; they cannot target a URL. External repo was
  shallow-cloned to `/tmp`, inspected file-by-file, and removed after analysis.
- Local side anchored on the existing (current) `.planning/codebase/` map.
- GitHub metadata via the public API. Read-only throughout; nothing in this repo was modified during
  research (this report is the only artifact written).
