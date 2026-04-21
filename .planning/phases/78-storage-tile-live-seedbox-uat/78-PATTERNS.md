# Phase 78: Storage Tile Live-Seedbox UAT - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 6 (4 new artifacts, 2 discretionary, 0 modified source)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/phases/78-.../78-UAT.md` (NEW) | doc (structured pass/fail log) | request-response (test-item frontmatter → result blocks) | `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/74-UAT.md` | **exact** (same 6 items being promoted from `blocked` to executed) |
| `.planning/phases/78-.../78-HUMAN-UAT.md` (NEW) | doc (narrative findings companion) | event-driven (human observations) | `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-HUMAN-UAT.md` | exact (same phase-scoped narrative template) |
| `.planning/phases/78-.../compose.yml` OR `src/e2e/compose-ssh-target.yml` (NEW) | infra (disposable SSH container spec) | request-response (docker compose up → SSH target ready) | `src/docker/test/e2e/compose.yml` + `src/docker/test/e2e/remote/Dockerfile` | role-match (same openssh-server shape, different watched-path bounding) |
| `.planning/phases/78-.../evidence/*.png` (OPTIONAL, NEW) | evidence (visual snapshots, load-bearing only) | file-I/O (artifact storage) | — (no prior phase has evidence dirs) | **no analog** (new convention) |
| `.planning/phases/78-.../scripts/*.sh` (OPTIONAL, NEW — loop-image bounding, D-05) | infra (host-side helper script) | file-I/O (loop-mount lifecycle) | — (no prior host-side bash helpers in `.planning/`) | **no analog** (discretionary, keep it tiny) |
| `src/python/controller/scan/{local,remote}_scanner.py` + `controller.py` + `stats-strip.component.*` | READ-ONLY reference | — | self | exact (exercised, not modified) |

## Pattern Assignments

### `78-UAT.md` (NEW, doc, structured pass/fail log)

**Analog:** `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/74-UAT.md`

**Why this analog:** Phase 78 is literally executing the 6 items Phase 74 marked `blocked`. Mirroring the exact shape lets an audit read `74-UAT.md` → `78-UAT.md` as a continuous trail (blocked → executed). D-12 mandates this.

**Frontmatter pattern** (copy from `74-UAT.md` lines 1-8, adapt fields):
```yaml
---
status: partial              # → 'partial' while running, 'complete' when done
phase: 78-storage-tile-live-seedbox-uat
source: [78-HUMAN-UAT.md]    # narrative companion is the source-of-evidence
started: 2026-04-21T<HH:MM:SS>Z
updated: 2026-04-21T<HH:MM:SS>Z
resolution: runtime-execution-on-disposable-seedbox   # contrast with 74's "structural-verification + 6 runtime items deferred"
---
```

**Current Test marker** (copy from `74-UAT.md` line 10-12):
```markdown
## Current Test

[test 3/6 in progress — threshold color 80% boundary]
```

**Per-test block — unblocked shape** (copy from the PASSING items in `74-UAT.md` lines 52-56, NOT the blocked shape at 16-21):
```markdown
### 1. Remote Storage tile — capacity mode
expected: Remote Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line when SSH df succeeds.
result: pass
evidence: "docker compose up -d; app booted against ssh-target:1234; df -B1 /data returned total=104857600 used=52428800; dashboard rendered '50%' + 'of 100.00 MB' + amber progress + '50.00 MB used'. Backend log: INFO RemoteScanner df ok. Screenshot: evidence/01-remote-capacity.png."
```

For failing tests:
```markdown
### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: [verbatim from 74-UAT.md lines 29-30]
result: fail
issue: "<short bug headline>"
evidence: "[log lines + reproducer + link to HUMAN-UAT.md section]"
```

**Verbatim expectation lines** — copy the six `expected:` strings from `74-UAT.md` lines 17, 23, 29-30, 35-36, 41, 47 UNCHANGED. D-12 says "mirror `74-UAT.md` structure exactly" — the expectation is the contract under test; paraphrasing breaks the trail.

**Summary block** (copy from `74-UAT.md` lines 107-114):
```markdown
## Summary

total: 6
passed: <N>
issues: <N>
pending: <N>
skipped: 0
blocked: 0    # ← critical: must be 0 when this phase closes; 74-UAT.md had 6 blocked, 78 clears them
```

**Gaps block** (copy line 116-118 shape):
```markdown
## Gaps

[none | <bug # routed to fix phase>]
```

---

### `78-HUMAN-UAT.md` (NEW, doc, narrative companion)

**Analog:** `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-HUMAN-UAT.md`

**Why this analog:** Phase 77 is the only prior phase whose HUMAN-UAT file sits in the new `.planning/phases/` tree (post-milestone structure). Phase 76's `76-HUMAN-UAT.md` is a close second and shares the "CLI-driven pass/fail, awaiting human confirmation" framing — D-14 ("Claude drives, user watches") makes 76/77 the right shape.

**Frontmatter pattern** (copy from `77-HUMAN-UAT.md` lines 1-7, adapt):
```yaml
---
status: partial
phase: 78-storage-tile-live-seedbox-uat
source: [78-UAT.md]           # inverse of 78-UAT.md.source — structured file references narrative, narrative references structured
started: 2026-04-21T<HH:MM:SS>Z
updated: 2026-04-21T<HH:MM:SS>Z
---
```

**Current Test marker** (copy from `77-HUMAN-UAT.md` line 9-11):
```markdown
## Current Test

[awaiting human visual confirmation of threshold color at 95% boundary]
```

**Per-test narrative pattern** (copy from `77-HUMAN-UAT.md` test-block shape, lines 15-25):
- Bullet-shaped, 1-3 sentences per item
- Include fallocate command + expected vs observed
- Link to `evidence/NN-*.png` only when visual is load-bearing (threshold color shifts, layout parity per D-13)

```markdown
### 1. Remote Storage tile — capacity mode
expected: Tile renders '50%' + 'of 100.00 MB' + amber bar + '50.00 MB used' after `fallocate -l 50M /data/fill.img` inside container.
result: [pending | pass | fail]
notes: "<prose observations, not just pass/fail — e.g., 'integer rounding rounded 49.8% → 50% as expected per D-05; capacity flipped from fallback to capacity mode on first SSE push after scan cycle, ~3s latency'>"
followups: "[none | link to bug or deferred item]"
```

**Summary block** (copy from `77-HUMAN-UAT.md` lines 27-33):
```markdown
## Summary

total: 6
passed: <N>
issues: <N>
pending: <N>
skipped: 0
blocked: 0
```

**Gaps block** — identical to 78-UAT.md; if a bug is found, both files link to the same fix-phase entry. Do not duplicate narrative between the two files — 78-UAT.md is terse/audit-grade, 78-HUMAN-UAT.md is prose/reviewer-grade.

---

### `compose.yml` (NEW, infra, disposable SSH target)

**Location:** `.planning/phases/78-storage-tile-live-seedbox-uat/compose.yml` per CONTEXT §Specifics ("Prefer a compose file under `.planning/phases/78-.../` (or `src/e2e/` if there's a clean home)"). Recommend the phase dir so teardown is `rm -rf .planning/phases/78-.../` and nothing leaks into `src/`.

**Analog:** `src/docker/test/e2e/compose.yml` + `src/docker/test/e2e/remote/Dockerfile`

**Why this analog:** The existing E2E harness already runs a disposable openssh-server container (`seedsyncarr_test_e2e_remote`) on LAN, user `remoteuser`, password `remotepass`, port 1234. Phase 78 needs the exact same shape plus a bounded filesystem at the watched path. D-03 explicitly allows linuxserver/openssh-server OR bespoke — the bespoke one we already have is the lower-friction choice.

**Compose service pattern** (copy from `src/docker/test/e2e/compose.yml` lines 16-23):
```yaml
services:
  ssh-target:
    image: seedsyncarr/phase78/ssh-target
    container_name: seedsyncarr_phase78_ssh_target
    platform: ${SEEDSYNCARR_PLATFORM:-linux/amd64}
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "2222:1234"   # expose SSH on host:2222 to avoid colliding with host's 22
    # D-04: bounded FS at watched path — pick ONE of:
    # (a) tmpfs (simple, size cap enforced)
    tmpfs:
      - /data:size=100M,mode=0755,uid=1000,gid=1000
    # (b) OR loop-mounted image (requires privileged container + host-side script per D-05)
    # volumes:
    #   - ./fixtures/fs-100m.img:/data.img
    # privileged: true
    # command: sh -c "losetup /dev/loop0 /data.img && mount /dev/loop0 /data && /usr/sbin/sshd -D"
```

**Dockerfile pattern** (copy from `src/docker/test/e2e/remote/Dockerfile` lines 1-36, strip the scan-fixture copy):
```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    openssh-server \
    coreutils    # provides fallocate, df
# user setup
RUN useradd --create-home -s /bin/bash seeduser && \
    echo "seeduser:seedpass" | chpasswd && \
    mkdir -p /data && chown seeduser:seeduser /data

# sshd config
RUN sed -i '/Port 22/c\Port 1234' /etc/ssh/sshd_config && \
    mkdir /var/run/sshd
EXPOSE 1234
CMD ["/usr/sbin/sshd", "-D"]
```

**Key deltas from the E2E remote Dockerfile:**
- Drop the `scanfs` fixture copy (lines 25) — Phase 78 boots the real app against this target; scanfs deploys itself via `_install_scanfs`.
- Drop the public-key auth install (lines 17-22) — Phase 78 uses password auth via the app's config; matches D-01's "disposable" framing.
- Add `coreutils` explicitly so `fallocate` + `df -B1` are guaranteed present (Ubuntu 22.04 has them by default but being explicit documents the dependency).

**D-09 failure-mode hooks** — none need compose-level plumbing:
- (a) path-missing: change app config `remote_path=/nonexistent`; no compose change.
- (b) network drop: `docker stop seedsyncarr_phase78_ssh_target` OR `iptables -I INPUT -p tcp --dport 2222 -j DROP` on host; no compose change.
- (c) parse failure: `docker exec … bash -c 'mv /usr/bin/df /usr/bin/df.real && echo -e "#!/bin/sh\necho garbage" > /usr/bin/df && chmod +x /usr/bin/df'`; runtime mutation, no compose change.

---

### `evidence/*.png` (OPTIONAL, NEW, screenshot artifacts)

**Analog:** none — no prior phase has committed evidence directories.

**Convention (new, proposed per D-13):**
- Path: `.planning/phases/78-storage-tile-live-seedbox-uat/evidence/`
- Naming: `NN-<slug>.png` where `NN` matches the UAT test number (01-06) and `<slug>` is a short label (e.g., `04-threshold-95-danger.png`)
- Capture tool: `gsd-browser screenshot` (per user global instructions)
- Commit policy: commit only load-bearing visuals per D-13 (threshold color shifts for Test 4; fallback-layout parity for Test 3; Test 6 before/after for Download Speed / Active Tasks tiles). Text + backend log excerpts are default for Tests 1, 2, 5.

**Referencing from 78-UAT.md / 78-HUMAN-UAT.md:**
```markdown
evidence: "...; screenshot: evidence/04-threshold-95-danger.png"
```
Use a relative path inside the phase dir so the whole phase folder is self-contained.

---

### `scripts/bound-local-fs.sh` (OPTIONAL, NEW, host-side loop-image bounding per D-05)

**Analog:** none — no prior phase has host-side bash helpers in `.planning/`.

**Convention:**
- Only create if D-05's "loop image recommended" path is taken for the local tile.
- Keep it to ~20 lines: `dd if=/dev/zero of=loop.img bs=1M count=100 && mkfs.ext4 loop.img && sudo mount -o loop loop.img /tmp/seedsync-local-mount`.
- Document teardown in the same script (`umount /tmp/seedsync-local-mount; rm loop.img`).
- Pair it with a README note in 78-HUMAN-UAT.md under "Test environment setup" so re-running the UAT doesn't require re-deriving the incantation.

---

### Source files under test (READ-ONLY, reference analogs)

The UAT drives these but does not modify them. Planner should cite these lines in UAT test items so evidence is anchored to concrete code:

| File | Lines | What the UAT verifies |
|------|-------|----------------------|
| `src/python/controller/scan/remote_scanner.py` | 30-51 (`_parse_df_output`) | Test 3 (parse-failure branch) — malformed `df` output returns `(None, None)` silently |
| `src/python/controller/scan/remote_scanner.py` | 126-137 (capacity block) | Test 1 (happy path) + Test 3 (SshcpError WARN log) |
| `src/python/controller/scan/local_scanner.py` | 32-39 (capacity block) | Test 2 (happy path) + Test 3 (OSError WARN log for local) |
| `src/python/controller/controller.py` | 639, 657-683 (`_should_update_capacity` + writes) | Test 4 (>1% gate under real fallocate deltas, if folded in per D-08) |
| `src/angular/src/app/pages/files/stats-strip.component.html` | 10-41 (Remote `@if`/`@else`) | Test 1 (capacity render) + Test 3 (fallback branch) |
| `src/angular/src/app/pages/files/stats-strip.component.html` | 51-82 (Local `@if`/`@else`) | Test 2 (capacity render) + Test 5 (per-tile independence) |
| `src/angular/src/app/pages/files/stats-strip.component.html` | 85-97, 99-114 (Download Speed, Active Tasks) | Test 6 (unchanged tiles) |

## Shared Patterns

### Pass/fail result shape
**Source:** `74-UAT.md` lines 52-105 (11 passing items)
**Apply to:** every test block in `78-UAT.md`
```markdown
result: pass
evidence: "<command or ui observation>; <log line>; <optional screenshot ref>"
```
**Key insight:** The `evidence:` string is a single line (markdown yaml-ish, not a real yaml block). Keep it grep-able; if it grows past ~300 chars, overflow goes to `78-HUMAN-UAT.md`'s `notes:` field.

### Frontmatter twin-reference (structured ↔ narrative)
**Source:** `74-UAT.md` line 4 (`source: [74-01-SUMMARY.md, ...]`) + `77-HUMAN-UAT.md` line 4 (`source: [77-VERIFICATION.md]`)
**Apply to:** both `78-UAT.md` and `78-HUMAN-UAT.md`
```yaml
# in 78-UAT.md
source: [78-HUMAN-UAT.md]

# in 78-HUMAN-UAT.md
source: [78-UAT.md]
```
**Key insight:** The two files reference each other, not phase plan summaries — there are no plans in this phase (no code changes). D-12 framed it as "structured file for audit trail; narrative file for anything that wants prose"; the cross-reference makes that explicit.

### Disposable openssh-server container
**Source:** `src/docker/test/e2e/remote/Dockerfile` + `src/docker/test/e2e/compose.yml`
**Apply to:** `.planning/phases/78-.../Dockerfile` + `compose.yml`
```yaml
# compose.yml skeleton
services:
  ssh-target:
    build: { context: ., dockerfile: Dockerfile }
    ports: ["2222:1234"]
    tmpfs: ["/data:size=100M,mode=0755,uid=1000,gid=1000"]
```
**Key insight:** The existing E2E harness already proves ubuntu:22.04 + openssh-server is a stable recipe. Reuse it verbatim so the UAT and the E2E suite have zero skew. Port 1234 is internal; map to host 2222 to stay clear of OS SSH.

### WARN-log silent-fallback assertion
**Source:** `remote_scanner.py:136` (`self.logger.warning("df SSH call failed for '%s': %s", ...)`); `local_scanner.py:39` (`self.logger.warning("Local disk_usage failed for path '%s': %s", ...)`)
**Apply to:** Test 3 evidence in `78-UAT.md`
**What to capture:**
```
WARN RemoteScanner df SSH call failed for '/nonexistent': <err>
WARN LocalScanner Local disk_usage failed for path '/unmounted': <err>
```
**Key insight:** D-16 is the contract under test — "silent fallback + WARN log". Test 3 evidence MUST cite the WARN line (copy-paste from app stdout/stderr) alongside the UI observation. Both ends of the contract in one line of evidence.

### D-09 failure-injection commands (reference, for planner)
**Source:** CONTEXT.md §<decisions> D-09 (a/b/c)
**Apply to:** Test 3 + any follow-up failure tests
```bash
# (a) path missing / non-zero exit
# Edit app config: remote_path=/nonexistent/path; restart scan cycle; observe Remote tile → fallback.

# (b) network drop mid-scan
docker stop seedsyncarr_phase78_ssh_target
# OR on host:
sudo iptables -I OUTPUT -p tcp --dport 2222 -j DROP
# Then revert: docker start … / iptables -D OUTPUT -p tcp --dport 2222 -j DROP

# (c) parse failure — stub df inside the container
docker exec seedsyncarr_phase78_ssh_target bash -c '
  mv /usr/bin/df /usr/bin/df.real &&
  printf "#!/bin/sh\necho garbage\n" > /usr/bin/df &&
  chmod +x /usr/bin/df
'
# Revert: mv /usr/bin/df.real /usr/bin/df
```
**Key insight:** Each failure mode hits a different code path in `remote_scanner.py` lines 129-137: (a) app config validation (never reaches df), (b) `SshcpError` except block (line 135), (c) `_parse_df_output` returning `(None, None)` + WARN on line 132-134. Test 3 evidence should annotate which branch was exercised.

### Boundary fallocate sequence (D-07)
**Source:** CONTEXT.md §<decisions> D-06/D-07 + `remote_scanner.py:130` (`df -B1` is the data source)
**Apply to:** Test 4 evidence
```bash
# Inside the ssh-target container:
fallocate -l 79M  /data/fill.img && sync   # expect amber    (< 80%)
fallocate -l 80M  /data/fill.img && sync   # expect warning  (>= 80% && < 95%)
fallocate -l 94M  /data/fill.img && sync   # expect warning  (>= 80% && < 95%)
fallocate -l 95M  /data/fill.img && sync   # expect danger   (>= 95%)
rm /data/fill.img                           # revert
```
**Key insight:** 100M tmpfs means 79M = 79%, 80M = 80%, etc. — the math is 1:1 so fallocate percentages = displayed percentages. `fallocate` is preferred over `dd` per D-06 (reservation without actual write, near-instant, reversible via `rm`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/78-.../evidence/` | evidence dir | file-I/O | No prior phase has committed screenshots in `.planning/`. Phase 78 introduces the convention per D-13. Keep it minimal — only commit files that prove a claim text can't (threshold colors, layout parity). |
| `.planning/phases/78-.../scripts/bound-local-fs.sh` | host-side helper | file-I/O | No precedent for bash scripts inside `.planning/`. Only add if D-05's loop-mount path is taken; prefer inlining the ~5 commands into 78-HUMAN-UAT.md setup section. |

## Metadata

**Analog search scope:**
- `.planning/milestones/v1.1.0-phases/74-storage-capacity-tiles/` (full dir — the phase being UAT'd)
- `.planning/milestones/v1.1.0-phases/{69,70,73}-*/` (*-HUMAN-UAT.md siblings)
- `.planning/phases/{76,77}-*/` (recent HUMAN-UAT.md siblings)
- `src/docker/test/e2e/` (disposable-SSH-container precedent)
- `src/python/controller/scan/{local,remote}_scanner.py`, `src/python/controller/controller.py` (exercised code)

**Files scanned:** 14

**Pattern extraction date:** 2026-04-21

**Key observations:**
1. **Twin-file convention is new** — Phase 78 is the first to split UAT into structured + narrative. Prior phases had either a `*-UAT.md` (milestones 62-74) OR a `*-HUMAN-UAT.md` (phases 69, 70, 73, 76, 77), never both. D-12 explicitly mandates both here because the blocked → executed trail needs audit-grade rigor AND the live findings are prose-heavy.
2. **Phase 78 has no plan files** — no code changes expected. Planner should NOT produce `78-NN-PLAN.md` files per the standard phase template; instead produce an execution-runbook-style single plan or skip planning entirely and hand directly to an executor. PATTERNS.md informs whichever path the planner takes.
3. **The `evidence/` dir is a new convention** — document it in 78-HUMAN-UAT.md so future UAT phases have a reference. Keep screenshots small (< 500KB each); use `gsd-browser screenshot` which defaults to PNG at the current viewport size.
4. **Disposable SSH container already exists in-tree** — `src/docker/test/e2e/remote/` is a green-field template; Phase 78's compose.yml should cite "derived from `src/docker/test/e2e/remote/Dockerfile`" in a header comment to make the lineage obvious.
5. **No source code will be touched** — if a UAT item fails and the failure is a bug in the code exercised (e.g., threshold boundary off-by-one), log it as `issue:` in 78-UAT.md + prose in 78-HUMAN-UAT.md + route to a separate fix phase per CONTEXT.md §Phase Boundary. Do NOT fold the fix into Phase 78.
