---
phase: 125
slug: lan-connection-tests
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-10-27
---

# Phase 125 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (`unittest.TestCase`-style tests) |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py -p no:cacheprovider -q` |
| **Full suite command** | `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q` plus `ruff check src/python/` from repo root |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command (pytest + whole-tree ruff)
- **Before `/bm:verify-work`:** Full suite must be green, plus the D-09 live sandbox check
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

To be filled from the plans' tasks. Requirement → test mapping (from 125-RESEARCH.md):

| Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|-----------------|-----------|-------------------|-------------|--------|
| LAN-01 | Private IPv4 ranges, IPv6 ULA, CGNAT, container name resolving private, loopback on 8989/7878 accepted | unit | `pytest tests/unittests/test_web/test_handler/test_config_handler.py -q` | ✅ | ⬜ pending |
| LAN-02 | Link-local/metadata, unspecified, multicast, reserved, loopback wrong/no port, mixed resolution, IPv4-mapped/compatible/NAT64 bypass forms, site-local refused with specific message; redirects unchanged | unit | same | ✅ | ⬜ pending |
| LAN-02 | No other outbound path uses the relaxed check (D-06) | unit | same | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (`TestValidateUrl` already stubs `socket.getaddrinfo`).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `http://sonarr-v5:8989` Test Connection succeeds and reports Sonarr version | LAN-01 | Needs real Docker DNS on the NAS sandbox | D-09: deploy PR CI staging image by digest to `seedsyncarr-test`, run Test Connection, restore pin, fresh-session check |
| `http://169.254.169.254` returns the new refusal message | LAN-02 | Live confirmation on the deployed image | D-09: temporarily set sandbox Sonarr URL, test, restore URL immediately |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
