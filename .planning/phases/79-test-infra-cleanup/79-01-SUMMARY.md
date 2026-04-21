---
phase: 79
plan: 01
status: complete
requirements: [TEST-01]
completed: 2026-04-21
key-files:
  modified:
    - src/docker/test/python/Dockerfile
    - src/python/pyproject.toml
  created:
    - .planning/todos/pending/2026-04-21-webob-cgi-upstream-unblock.md
---

# Plan 79-01 — Python pytest stderr cleanup

## What shipped

Eliminated the four recurring stderr noise sources in `make run-tests-python`:

- 3× pytest-cache write warnings (caused by the read-only `/src` mount) — suppressed by disabling the `cacheprovider` plugin entirely.
- 1× webob/cgi `DeprecationWarning` (webob 1.8.9 still imports stdlib `cgi` under Python 3.11) — suppressed by an interpreter-level `PYTHONWARNINGS` filter applied before webob imports `cgi`.

### Edits

**`src/docker/test/python/Dockerfile` (commit `131c074`):**

```diff
 ENV PYTHONPATH=/src
+ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"

 ENTRYPOINT ["/app/entrypoint.sh"]
-CMD ["pytest", "-v"]
+CMD ["pytest", "-v", "-p", "no:cacheprovider"]
```

**`src/python/pyproject.toml` (commit `eddd52e`):**

Dropped dead `cache_dir` (never honored once `cacheprovider` is disabled) and the non-matching `filterwarnings` entry (the cgi `DeprecationWarning` fires at import time, before pytest installs its filter chain — see RESEARCH §3/§4). Final `[tool.pytest.ini_options]` contains only `pythonpath` and `timeout`.

## Decisions realized

Implements `D-01`, `D-02`, `D-04`, `D-05` per RESEARCH §2–§3. `D-03` (webob upgrade) is unviable as of 2026-04-21 — verified against live PyPI that webob 1.8.9 is the latest release and still imports `cgi` at `src/webob/compat.py:4`; PR #466 (cgi-removal for webob 2.0) remains unmerged. Committed to `D-05` (interpreter-level filter) directly, no "try upgrade first" branch.

Scoped `:cgi` qualifier retained — not broadened to `ignore::DeprecationWarning` — because RESEARCH §2 verified the `DeprecationWarning` is emitted by the stdlib `cgi` module itself, making `:cgi` the correct `PYTHONWARNINGS` qualifier. The R-5 broad-filter fallback was not triggered (no empirical grep evidence required broadening).

Local dev unchanged — `PYTHONWARNINGS` lives only in the test container's `ENV`, not in `pyproject.toml`, so `poetry run pytest` outside Docker still shows the cgi warning (intentional; surfaces upstream state).

## Verification

### Static acceptance (all passed in worktree)

```
grep -c 'CMD \["pytest", "-v", "-p", "no:cacheprovider"\]' src/docker/test/python/Dockerfile  → 1
grep -c 'ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"' src/docker/test/python/Dockerfile → 1
grep -c '^CMD \["pytest", "-v"\]$' src/docker/test/python/Dockerfile                          → 0
grep -c 'cache_dir\|filterwarnings' src/python/pyproject.toml                                 → 0
grep -c '\[tool.pytest.ini_options\]' src/python/pyproject.toml                               → 1
grep -c 'pythonpath = \["\."\]' src/python/pyproject.toml                                     → 1
grep -c 'timeout = 60' src/python/pyproject.toml                                              → 1
grep -c '\[tool.coverage.run\]' src/python/pyproject.toml                                     → 1
```

### Runtime acceptance (deferred per plan exemption)

`make tests-python` failed locally at the **base image build step** — specifically the `apt-get install openssh-server rar unrar` layer — which is the documented arm64 tech-debt failure (see ROADMAP Phase 80 scope; Plan 01 Task 3 acceptance explicitly marks this "exempt"). The failure happens in the base `seedsyncarr_run_python_env` image, upstream of every edit this plan made. Runtime stderr grep verification therefore falls back to SC #1c ("orchestrator post-merge CI log inspection at `.github/workflows/ci.yml:144`") tracked in `79-VALIDATION.md` "Manual-Only Verifications".

No R-5 broad-filter fallback applied. If post-merge CI stderr shows `cgi.*deprecated` matches, follow the fallback sequence in 79-01-PLAN.md Task 3: broaden to `ENV PYTHONWARNINGS="ignore::DeprecationWarning"` (container-only, does not leak to local dev).

## Follow-ups

- Created `.planning/todos/pending/2026-04-21-webob-cgi-upstream-unblock.md` tracking webob PR #466 / webob 2.0 release for eventual `PYTHONWARNINGS` removal. When webob ships without the `cgi` import, the `ENV PYTHONWARNINGS` line can be dropped as dead filter.
- Supersedes `.planning/todos/pending/2026-02-08-clean-up-test-warnings.md` — that original todo is now addressed by this plan; consider moving to `done/` as part of phase completion.

## Self-Check: PASSED (static acceptance; runtime deferred per plan exemption)
