---
created: 2026-04-23T00:04:58.911Z
title: Tighten Shield Semgrep rules to reduce false positives
area: tooling
files:
  - shield-claude-skill/configs/semgrep-rules/javascript.yaml
---

## Problem

The Shield security scanner's custom Semgrep rules produce hundreds of false positives on Angular/TypeScript codebases:

1. **`js-nosql-injection-where`** (617 false positives) — Pattern `$COLLECTION.$WHERE($INPUT)` matches any method call on any object (e.g., `this.cdr.markForCheck()`, `service.subscribe(...)`). It's intended to catch MongoDB's `$where` operator but has no context constraint.

2. **`js-xss-eval-user-input`** (11 false positives) — Pattern matches `setTimeout($INPUT, ...)` and `setInterval($INPUT, ...)` including arrow-function callbacks like `setTimeout(() => this.scrollToBottom(), 0)`. Only string arguments to setTimeout/setInterval are actual eval sinks.

These 628 false positives drown out real findings and make the raw score meaningless (reported 0/100 before triage).

## Solution

In `shield-claude-skill/configs/semgrep-rules/javascript.yaml`:

1. **`js-nosql-injection-where`** — Add a `pattern-inside` constraint to limit matches to files/scopes that import a MongoDB driver, or replace the overly broad `$COLLECTION.$WHERE($INPUT)` with patterns specific to MongoDB collection method chains.

2. **`js-xss-eval-user-input`** — Add `pattern-not` exclusions for arrow-function and named-function callbacks:
   - `pattern-not: setTimeout((...) => {...}, ...)`
   - `pattern-not: setInterval((...) => {...}, ...)`
   - `pattern-not: setTimeout(function(...){...}, ...)`
   - `pattern-not: setInterval(function(...){...}, ...)`
