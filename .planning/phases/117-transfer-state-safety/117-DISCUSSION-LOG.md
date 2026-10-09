# Phase 117: Transfer-State Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-08
**Phase:** 117-Transfer-State Safety
**Areas discussed:** UI during 'unavailable', Stability after an outage, Scope of the parser audit

---

## UI during 'unavailable'

| Option | Description | Selected |
|--------|-------------|----------|
| Freeze last-known | Active downloads keep last progress/speed until status returns; zero UI change | ✓ |
| Add an 'unavailable' badge | Visible marker while status is unavailable; new UI + frontend/e2e work | |

**User's choice:** Freeze last-known
**Notes:** The question stated the gap is short because the 3rd failure restarts the controller. Corrected afterwards: `LftpManager.status()` catches the escalation raise and returns `None`, so the freeze lasts as long as status stays unparseable (already today's behavior for failures ≥3). Freeze retained; indicator deferred.

---

## Stability after an outage

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, count it | Stability measured between real observations; failed scans neither add time nor reset | ✓ (with refinement) |
| Restart the timer | Any failed scan resets the window | |

**User's choice:** Yes, count it — two successful observations with matching sizes separated by the window satisfy the gate; failed scans cannot advance or reset it.
**Notes:** If the first successful scan after recovery shows a different size, restart the window. Test both cases for remote and local clocks.

---

## Scope of the parser audit

| Option | Description | Selected |
|--------|-------------|----------|
| Header-swallowing only | Fix every next-line-consuming site that can swallow a header, test each; record others | ✓ (with refinement) |
| Also tighten other loose patterns | Broader fixes; bigger diff and regression risk | |

**User's choice:** Header-swallowing only.
**Notes:** Regression test per confirmed site, plus checks that valid existing output still parses unchanged. Record unrelated parser weaknesses for later. "Keep this patch focused on preventing lost or misreported jobs."

---

## Claude's Discretion

- Name/location of successful-scan clock(s); internal parser peek-before-pop structure; test organization.

## Deferred Ideas

- UI "transfer status unavailable" indicator.
- Unrelated LFTP parser weaknesses found during the audit.
