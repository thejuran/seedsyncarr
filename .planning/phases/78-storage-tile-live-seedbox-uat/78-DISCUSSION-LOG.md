# Phase 78: Storage Tile Live-Seedbox UAT - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 78-storage-tile-live-seedbox-uat
**Areas discussed:** Test environment, Threshold forcing, Failure injection, Evidence + who drives

---

## Test environment

### Q1: What is the live seedbox target for this UAT?

| Option | Description | Selected |
|--------|-------------|----------|
| Real personal seedbox | Production seedbox over real SSH. Most authentic; fills must be reversible. | |
| Dedicated test host | Separate VPS / Linux box purpose-built for UAT. | |
| Disposable container | Docker/compose SSH target with a mounted tmpfs of known size. | ✓ |

**User's choice:** Disposable container

### Q2: What build do we validate against?

| Option | Description | Selected |
|--------|-------------|----------|
| Already-running instance | Use whatever is currently deployed. | |
| Fresh :dev image | Pull/build latest :dev before UAT. | |
| Run from source locally | Launch from this repo pointing at the seedbox. | ✓ |

**User's choice:** Run from source locally

### Q3: How should the disposable SSH container be provisioned?

| Option | Description | Selected |
|--------|-------------|----------|
| linuxserver/openssh-server | Pre-built image with SSH; add tmpfs/loop volume for watched path. | |
| Bespoke docker-compose | Purpose-built compose with openssh-server + loop-mounted ext4 image. | |
| Claude's discretion | Pick at plan time; both satisfy the SSH + bounded FS constraint. | ✓ |

**User's choice:** Claude's discretion

### Q4: Where does the bounded filesystem live so we can fill it safely?

| Option | Description | Selected |
|--------|-------------|----------|
| Loop-mounted image file | `dd` + `mkfs.ext4` + mount — small, restart-survivable. | |
| tmpfs of fixed size | tmpfs with `size=100m` — resets on restart. | |
| Claude's discretion | Both work; loop-image is more authentic, tmpfs simpler. | ✓ |

**User's choice:** Claude's discretion

---

## Threshold forcing

### Q1: How do we drive the remote FS to 80% and 95%?

| Option | Description | Selected |
|--------|-------------|----------|
| fallocate to target size | Sparse/reservation, fast, exact control, reversible with `rm`. | ✓ |
| dd with real writes | Slower; actually writes zeros. | |
| Pre-seed the image | Three baked FS image variants, swap loop-mount. | |

**User's choice:** fallocate to target size

### Q2: How do we validate the local tile's thresholds?

| Option | Description | Selected |
|--------|-------------|----------|
| Bounded local watched path | Loop-mounted image on the dev host, symmetric with remote. | |
| Accept current host state | Read whatever `shutil.disk_usage(watched_path)` reports; skip thresholds. | |
| Claude's discretion | Pick at plan time based on host-disruption cost. | ✓ |

**User's choice:** Claude's discretion

### Q3: How many threshold boundaries per tile?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 levels: <80, 80–94, ≥95 | One data point per color zone. | |
| Boundary ping: 79, 80, 94, 95 | Strict-inequality visual validation. | |
| Claude's discretion | Minimum set that proves D-05/D-11 without duplicating unit-test coverage. | ✓ |

**User's choice:** Claude's discretion

### Q4: Also exercise the `>1% change gate` against live SSH?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, explicit test | Small then large fallocate delta, confirm SSE gating. | |
| No, unit-tested already | Skip; 9 unit-test cases cover it. | |
| Claude's discretion | Include only if it folds naturally into the fallocate workflow. | ✓ |

**User's choice:** Claude's discretion

---

## Failure injection

### Q1: Which df-failure modes do we exercise?

| Option | Description | Selected |
|--------|-------------|----------|
| Path missing (non-zero exit) | Point `remote_path` at a nonexistent directory. | |
| Network drop mid-scan | Stop SSH container or iptables-drop port 22. | |
| Parse failure | Stub `df` to emit malformed output. | |
| All three | Run the full matrix. | ✓ |

**User's choice:** All three

### Q2: How do we confirm the UI handled the failure gracefully?

| Option | Description | Selected |
|--------|-------------|----------|
| Visual inspection + DOM | Browser shows tracked-bytes fallback; snapshot + screenshot. | |
| Check SSE payload + UI | Tap `/server/status` + DOM; both layers. | |
| Claude's discretion | Minimum evidence needed to prove "didn't crash + other tile unaffected." | ✓ |

**User's choice:** Claude's discretion

### Q3: Per-tile independence — both directions?

| Option | Description | Selected |
|--------|-------------|----------|
| Both directions | Remote-fail/local-ok AND local-fail/remote-ok (matches 74-UAT Test 5). | |
| One direction only | Remote-fail/local-ok (realistic case; SSH is the fragile side). | |
| Claude's discretion | Both if cheap; one if local-fail requires host OS disruption. | ✓ |

**User's choice:** Claude's discretion

---

## Evidence + who drives

### Q1: Where do we record UAT results?

| Option | Description | Selected |
|--------|-------------|----------|
| 78-UAT.md mirroring 74-UAT | Structured frontmatter; 6 items promoted from blocked to pass/fail. | |
| 78-HUMAN-UAT.md (Phase 77 shape) | Human-driven narrative format. | |
| Both | Structured + narrative. | ✓ |

**User's choice:** Both

### Q2: What evidence alongside each pass/fail?

| Option | Description | Selected |
|--------|-------------|----------|
| Text findings + log excerpts | Written observation + backend log lines. | |
| Screenshots + text | Browser screenshots under `.planning/phases/78-.../evidence/`. | |
| Claude's discretion | Convince a future reviewer each success criterion was met. | ✓ |

**User's choice:** Claude's discretion

### Q3: Who operates what during the UAT session?

| Option | Description | Selected |
|--------|-------------|----------|
| Claude drives, user watches | Claude runs docker/SSH/fallocate/browser; user confirms visual. | ✓ |
| User drives, Claude records | User runs manually; Claude writes UAT markdown. | |
| Hybrid | Claude scripts; user runs; Claude records. | |

**User's choice:** Claude drives, user watches

---

## Claude's Discretion

- Container image choice (openssh-server vs. custom compose)
- Bounded FS mechanism (loop image vs. tmpfs)
- Local tile bounding mechanism
- Boundary-ping granularity
- Fold or skip live `>1%` gate test
- UI-evidence minimum for failure tests
- Per-tile-independence both-directions vs. one-direction
- Screenshot-vs-text per test item

## Deferred Ideas

- Automating the UAT in Playwright — impossible (74-CONTEXT §Deferred Ideas)
- CI integration of live UAT — out of scope for v1.1.1
- Below-80% "healthy" color coverage — unit-tested, not a UAT concern
