---
phase: 92-e2e-infrastructure
fixed_at: 2026-04-27T00:00:00Z
review_path: .planning/phases/92-e2e-infrastructure/92-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 92: Code Review Fix Report

**Fixed at:** 2026-04-27
**Source review:** .planning/phases/92-e2e-infrastructure/92-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: `curl -s` silently discards HTTP errors in run_tests.sh

**Files modified:** `src/docker/test/e2e/run_tests.sh`
**Commit:** 71f49f9
**Applied fix:** Changed both polling curl calls from `-s` to `-sf` with `2>/dev/null` appended. The `-f` flag causes curl to exit non-zero on HTTP errors and emit nothing to stdout; `parse_status.py` then receives empty stdin, triggers `json.JSONDecodeError`, and returns `False` — keeping the polling loop running without silently ingesting a misleading error body. The `2>/dev/null` suppresses curl's stderr during the startup window (preserving the original intent of `-s`). The diagnostic curl on line 49 (used only in the failure path to display status for debugging) was left with `-s` only since it intentionally prints the raw response body.

### WR-02: Missing `set -euo pipefail` in run_tests.sh

**Files modified:** `src/docker/test/e2e/run_tests.sh`
**Commit:** 0787708
**Applied fix:** Added `set -euo pipefail` as the first executable line after the shebang, matching the convention in `setup_seedsyncarr.sh`. Also converted the three backtick command substitutions for `tput` on lines 3-5 to `$(...)` syntax as directed by the reviewer's fix note, making them consistent with all other command substitutions in the file.

---

_Fixed: 2026-04-27_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
