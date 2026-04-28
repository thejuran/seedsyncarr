---
phase: 92-e2e-infrastructure
plan: 02
status: complete
started: 2026-04-27
completed: 2026-04-27
---

## Summary

Rewrote `src/docker/test/e2e/parse_status.py` to replace the bare `except:` clause with a specific exception tuple `(json.JSONDecodeError, KeyError, TypeError)`, preventing unintentional masking of `SystemExit`, `KeyboardInterrupt`, and other non-recoverable errors. All executable logic was moved inside an `if __name__ == '__main__':` guard so the module can be safely imported without side effects.

## Tasks Completed

| # | Task | Status |
|---|------|--------|
| 1 | Replace bare except and add __main__ guard | ✓ |

## Key Files

### Modified
- src/docker/test/e2e/parse_status.py

## Self-Check

Verification run immediately after rewrite:

```
grep -q "if __name__ == '__main__':"           -> PASS
grep -q "except (json.JSONDecodeError, ...)"   -> PASS
! grep -q "^except:"                           -> PASS
echo '{"server":{"up":true}}' | python3 ...   -> True (PASS)
echo "not-json" | python3 ...                  -> False (PASS)
importlib import without side effects          -> IMPORT OK (PASS)
Overall: PASS: all parse_status.py checks
```

Commit: 53f3bb9

## Deviations

None
