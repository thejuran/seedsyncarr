# Phase 78: Storage Tile Live-Seedbox UAT - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute the 6 runtime UAT items deferred from Phase 74 against live seedbox infrastructure, record pass/fail + findings, and close UAT-03. Phase 74's implementation decisions (D-01..D-16) are locked — this phase only validates them against a real `df -B1` over SSH and a real `shutil.disk_usage` on the host. No code changes are expected; any bug found in UAT is logged and routed to a separate fix phase, not folded here.

</domain>

<decisions>
## Implementation Decisions

### Test environment
- **D-01:** Remote seedbox = a **disposable SSH container** (localhost/LAN), not a real personal seedbox and not a dedicated VPS. Safer for destructive fill tests.
- **D-02:** App runs **from source locally** (python + `ng serve`) pointing at the containerized SSH target — faster iteration on any findings, no rebuild loop.
- **D-03:** Container provisioning approach (linuxserver/openssh-server vs. bespoke docker-compose) is **Claude's discretion** during planning. The UAT needs only: SSH access + a size-bounded filesystem at the watched path.
- **D-04:** Bounded-FS shape (loop-mounted image vs. fixed-size tmpfs) is **Claude's discretion**. Both are acceptable; constraint is that `df -B1 <watched_path>` reports a small total (~100 MB range) so fills are fast and cheap.
- **D-05:** The local tile also needs a bounded watched path on the dev host so thresholds can be driven symmetrically. How to bound it is Claude's discretion (loop image recommended; don't mess with the host root FS).

### Threshold forcing
- **D-06:** Fill method = **`fallocate -l <N>M`** (sparse/reservation), not `dd`. Exact control, near-instant, reversible with `rm`.
- **D-07:** Boundary coverage is **Claude's discretion** — minimum viable is one data point per color zone (<80, 80–94, ≥95). Exact-boundary ping (79/80/94/95) is fine if cheap to script but unit tests already cover strict-inequality; the runtime UAT only needs to prove colors render against a real FS.
- **D-08:** `>1% change gate` live validation is **Claude's discretion** — include if it folds naturally into the fallocate sequence (small delta → no SSE update, large delta → SSE update); drop otherwise. Unit tests already cover the 9 strict-inequality cases.

### Failure injection
- **D-09:** Exercise **all three** df-failure modes: (a) path missing / non-zero exit (point `remote_path` at a nonexistent directory), (b) network drop mid-scan (stop SSH container or iptables-drop port 22), (c) parse failure (stub `df` binary to emit malformed output).
- **D-10:** UI-pass evidence format for graceful-failure tests is **Claude's discretion** — pick the minimum that proves "didn't crash dashboard + fell back to tracked-bytes + other tile unaffected." Expect visual snapshot + one backend log line.
- **D-11:** Per-tile independence coverage is **Claude's discretion** — run both directions (remote-fail/local-ok AND local-fail/remote-ok) if both sides are bounded FS we control; drop local-fail if it would require disruptive action on the dev host OS.

### Evidence and execution
- **D-12:** Record UAT in **both** `78-UAT.md` (structured 6-item pass/fail, mirroring `74-UAT.md` shape) **and** `78-HUMAN-UAT.md` (narrative findings, follow-ups). Structured file for audit trail; narrative file for anything that wants prose.
- **D-13:** Evidence alongside each pass/fail = **Claude's discretion**. Default to text findings + backend log excerpts; add screenshots under `.planning/phases/78-.../evidence/` only where the visual is load-bearing (threshold color shifts, fallback layout).
- **D-14:** Execution split = **Claude drives, user watches**. Claude operates docker/SSH/fallocate/gsd-browser; user confirms subjective visual results (color correctness, layout parity) where judgment is needed.

### Claude's Discretion
- Container image choice (openssh-server vs. custom compose)
- Bounded FS mechanism (loop image vs. tmpfs)
- Local tile bounding mechanism
- Boundary-ping granularity
- Whether to fold the live `>1%` gate test into the fallocate sequence
- UI-evidence minimum for failure tests
- Per-tile-independence both-directions vs. one-direction
- Screenshot-vs-text-only per test item

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 78 scope anchors
- `.planning/ROADMAP.md` → `### Phase 78: Storage Tile Live-Seedbox UAT` — goal, 5 success criteria, UAT-03 mapping
- `.planning/REQUIREMENTS.md` → UAT-03 — the six runtime checks being promoted from blocked to executed

### Locked Phase 74 decisions (feed everything UAT observes)
- `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/74-CONTEXT.md` §Implementation Decisions — D-01..D-16 covering tile layout, threshold colors, >1% gate, per-tile independence, silent fallback semantics
- `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/74-UAT.md` §Tests 1–6 — verbatim descriptions of the six deferred runtime items this phase executes
- `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/74-VALIDATION.md` — manual-only justification for items deferred here

### Implementation surface this UAT exercises
- `src/python/common/status.py` — `Status.StorageStatus` shape
- `src/python/controller/controller.py::_should_update_capacity` — `>1%` change gate
- `src/python/controller/scan/local_scanner.py` — `shutil.disk_usage` + OSError/ValueError fallback
- `src/python/controller/scan/remote_scanner.py` — `df -B1 <shlex.quote(path)>` + SshcpError / parse fallback
- `src/angular/src/app/pages/files/stats-strip.component.html` — capacity `@if`/`@else` + threshold class bindings
- `src/angular/src/app/pages/files/stats-strip.component.scss` — `--warning` / `--danger` modifiers
- `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts` — threshold boundary tests (reference, not re-run)

### Comparable prior phase shape
- `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-HUMAN-UAT.md` — template for the narrative `78-HUMAN-UAT.md` companion file

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- `Status.StorageStatus` + `SerializeStatusJson` — already emit the `storage` block on SSE; UAT just reads it.
- `shlex.quote` wrapping of the remote path — hostile-path unit test already passes; live UAT only needs to confirm a normal path still works.
- `stats-strip.component` capacity `@if` / fallback `@else` — the UAT drives the branches, it doesn't modify them.

### Established patterns
- Silent fallback on scanner exceptions (`WARN` log, no error banner) — Phase 74 D-16 establishes this; UAT asserts the UI matches.
- `>1% change gate` lives in `controller.py::_should_update_capacity` with strict-inequality semantics; live test validates the same math against real df output.

### Integration points
- SSE `/server/status` stream delivers the `storage` block — tap here to verify backend-side capacity before inspecting the tile.
- Dashboard `stats-strip` consumes `DashboardStats.*Capacity*` fields via `combineLatest([files, status])` — the observable path is the live verification target.

</code_context>

<specifics>
## Specific Ideas

- Mirror `74-UAT.md` structure exactly for `78-UAT.md` (same frontmatter keys, same per-test `expected`/`result`/`evidence` shape) so the trail from blocked → executed is mechanical.
- Follow `77-HUMAN-UAT.md` framing for the narrative companion file — short, bullet-shaped, CI/runtime framing.
- Prefer a compose file under `.planning/phases/78-.../` (or `src/e2e/` if there's a clean home) that can be spun up with one `docker compose up -d` so the UAT is re-runnable by anyone.

</specifics>

<deferred>
## Deferred Ideas

- Automating this UAT in Playwright: impossible — SSH df + host disk state can't be faked in the E2E harness (74-CONTEXT §Deferred Ideas established this). Stays manual by design; no follow-up phase needed.
- CI integration of the live UAT: out of scope for v1.1.1; revisit only if a future milestone adds a persistent test seedbox.
- Extending threshold coverage below 80% (e.g., a formal "healthy" state color test): D-09 thresholds already colored via Bootstrap tokens, covered by unit tests — not a UAT concern.

</deferred>

---

*Phase: 78-storage-tile-live-seedbox-uat*
*Context gathered: 2026-04-21*
