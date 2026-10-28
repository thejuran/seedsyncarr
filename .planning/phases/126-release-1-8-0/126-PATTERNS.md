# Phase 126: Release 1.8.0 - Pattern Map

**Mapped:** 2026-10-28
**Files analyzed:** 18 (version-bump sites, content files, evidence/scripts)
**Analogs found:** 18 / 18 (every file has a direct same-role prior-release analog — this phase repeats the 1.7.4/1.7.5/1.7.6 release pattern with no new code)

This phase is pure release engineering: no new product code, no new component/service/controller
roles exist. Every "file to create or modify" is either (a) a repo-metadata file bumped identically
in every prior release, (b) a content file (CHANGELOG/release-notes/SECURITY.md) rewritten in the
exact structure the last three releases used, or (c) a release-evidence/script artifact that is a
direct copy-and-extend of the most recent same-purpose script. Treat the entire 119→119.1→122→125
evidence chain as the pattern source; there is no other part of the codebase to search.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `CHANGELOG.md` | config (release content) | transform (draft → finalized section) | `CHANGELOG.md` `## [1.7.6]` entry (same file, prior release) | exact |
| `release-notes.md` | config (release content) | transform (full rewrite per release) | `release-notes.md` 1.7.6 body (same file, prior release) | exact |
| `SECURITY.md` | config (security doc) | transform (one-bullet correction) | `SECURITY.md` "Encrypted secrets at rest" bullet fix, 119.1-04 | exact |
| `package.json` (root) | config (version metadata) | CRUD (single field write) | same file, 1.7.6 bump | exact |
| `package-lock.json` (root) | config (version + dependency metadata) | CRUD / batch (version field + puppeteer bump) | same file, 1.7.6 bump; 119-REL03 `npm update puppeteer` precedent | exact |
| `src/angular/package.json` | config (version + dependency ranges) | CRUD / batch | same file, 1.7.6 bump; 1.7.5's `@types/jasmine` range edit pattern | exact |
| `src/angular/package-lock.json` | config (dependency lockfile) | batch (regenerated, not hand-edited) | 119-REL03 `npm update source-map-js` regeneration, scaled to 23 packages | role-match (scale differs) |
| `src/python/pyproject.toml` | config (version metadata, 2 fields) | CRUD | same file, 1.7.6 bump (`[project]` + `[tool.poetry]`) | exact |
| `src/python/poetry.lock` | config (dependency lockfile) | batch (regenerated) | 119-REL03 `poetry update cryptography pytz` | exact |
| `126-teardown.sh` | utility (idempotent sandbox restore script) | event-driven (idempotent restore triggered by smoke session) | `125-teardown.sh` | exact |
| `126-webhook-post.sh` (if a fresh signed-webhook poster is needed) | utility (HMAC webhook POST script) | request-response | `122-webhook-post.sh` | exact |
| `126-extract_secrets.py` | utility (count-only secret-in-log extractor) | file-I/O (read-only, value-free) | `119.1-extract_secrets.py` | exact (copy verbatim per 119.1-REL04's own reuse note) |
| `118-05-parse_check.py` (reused, not modified) | utility (read-only persist-file loader check) | file-I/O | same script, unchanged since 1.7.6 | exact (verbatim reuse, no copy needed) |
| `126-REL-EVIDENCE.md` (dependency roll-in + release gate) | test (evidence/record file) | batch (command log + verification record) | `119.1-REL04-EVIDENCE.md` + `119-REL03-EVIDENCE.md` §"Dependabot roll-ins" | exact |
| `126-SMOKE-EVIDENCE.md` (sandbox smoke) | test (evidence/record file) | event-driven (live smoke session log) | `122-SAFE01-EVIDENCE.md` + 119.1-REL04 §"Smoke test on NAS" | exact |
| `126-DEPLOY-EVIDENCE.md` (prod deploy) | test (evidence/record file) | event-driven (deploy command log) | 119.1-REL04-EVIDENCE.md §"Merge and tag" / §"Tag and CI" / prod deploy recipe | exact |
| `.planning/STATE.md` | config (project state) | CRUD | same file, PR #140 status field correction | exact |
| `.planning/ROADMAP.md` §"Phase 126" / §"999.4" | config (roadmap record) | CRUD | same file, prior phase-completion entries | exact |

## Pattern Assignments

### `CHANGELOG.md` (config, transform)

**Analog:** `CHANGELOG.md` itself — the `## [1.7.6] - 2026-10-15` entry is the structural template; the current `## [Unreleased]` section is the Phase 125 draft to fold under `## [1.8.0]`.

**Current `[Unreleased]` draft (lines 7-40)** — keep verbatim per D-10, just re-head it:
```markdown
## [Unreleased]

These are the draft notes for 1.8.0. ...

### Changed
- Test Connection for Sonarr and Radarr now accepts local network and
  Docker container addresses ...
### Security
- Upgrading fixes an issue present in SeedSyncarr 1.7.6 and earlier: ...
```

**1.7.6 entry structure to copy (lines 42-80)** — section order `### Security` → `### Changed` →
`### Fixed` (D-07 locks this order: Security, Changed, Fixed for 1.8.0):
```markdown
## [1.7.6] - 2026-10-15

A security release. Every container start printed the whole settings file, ...

### Security
- Versions 1.0.0 through 1.7.5 printed the full `settings.cfg` to the
  container log ... (SEC-01)

### Changed
- Changed container startup to print `Config ready at /config/settings.cfg
  (existing config kept)` ... (SEC-01)
- Changed debug-level config logging to redact every setting marked secret, ...
```

**Required content assembly for `[1.8.0]`** (facts verified in RESEARCH.md, exact wording at
planner's discretion per CONTEXT.md "Claude's Discretion"):
1. Heading `## [1.8.0] - <tag date>`, one-paragraph summary (1.7.6's style: what changed and why minor).
2. `### Security` — existing Phase 125 bullets (keep as drafted) + new Phase 121 bullet. Exact fact
   to render (RESEARCH.md §"Release Notes Content", D-08): "Versions 1.0.0 through 1.7.6 sent the
   configured API token to GitHub's update-check endpoint on every page load (GitHub rejected it;
   no other destination ever received it). 1.8.0 only ever attaches the token to SeedSyncarr's own
   `/server/*` requests. If you have an API token configured, rotating it after upgrading is a cheap
   precaution — not required." — same plain-tone, no-exploit-detail register as the 1.7.6 SEC-01 bullet.
3. `### Changed` — Phase 125 draft bullets, verbatim (D-10).
4. `### Fixed` — one line each for 122, 123, 124, using the exact facts in RESEARCH.md §"Fixed
   section — exact facts (D-09)" (no internals, per D-09).
5. The `## [1.7.6] - 2026-10-15` entry and everything below it stays untouched.

**Metadata contract this file must satisfy** (checked by CI's `verify-release-metadata` job,
source: `scripts/verify-release-metadata.mjs` lines 25-29):
```javascript
export function hasChangelogReleaseSection(changelogText, expectedVersion) {
  const releaseHeading = new RegExp(`^##\\s+\\[?${escapedVersion}\\]?(?:\\s+-\\s+.+)?\\s*$`, "m");
  return releaseHeading.test(changelogText);
}
```
A heading matching `## [1.8.0] - <anything>` is sufficient; content below it is not machine-checked.

---

### `release-notes.md` (config, full rewrite)

**Analog:** `release-notes.md`'s own 1.7.6 body (currently in the repo — this entire file gets
replaced for 1.8.0, confirmed as the established pattern by RESEARCH.md Open Question 2: "each
release's `release-notes.md` commit is a full rewrite, not an append").

**Section skeleton to reproduce (verbatim structure, new content):**
```markdown
<opening paragraph: what this release is, one line on "should you update">

### What changed in 1.8.0
- <bullet per notable Security/Changed/Fixed item, plain English>

**Do this after updating:**
1. <numbered list — for 1.8.0: rotate API token only if one is configured (D-08); no
   recreate-the-container requirement since this isn't a log-printing fix>

### Should you update?
<yes/no framing>

### Before you upgrade
1. Stop SeedSyncarr ...
2. Copy three files ... with a `.pre-1.8.0` suffix ...
3. Change the image tag to 1.8.0 and start SeedSyncarr ...

### If you need to roll back
<rollback runbook — see Shared Patterns "Rollback Runbook" below for the exact 7-step structure
 and the three callouts to keep/drop per RESEARCH.md §"Rollback Safety">

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
```

**CI link-pattern contract** (checked, `{{VERSION}}` is substituted at publish time — `.github/workflows/ci.yml` line ~327):
```bash
sed "s|{{VERSION}}|${RELEASE_VERSION}|g" release-notes.md > release-body.md
gh release create "v${RELEASE_VERSION}" --title "v${RELEASE_VERSION} — SeedSyncarr" --notes-file release-body.md
```
Keep the literal `{{VERSION}}` token in the final changelog link line — do not hand-substitute it.

---

### `SECURITY.md` (config, one-bullet correction)

**Analog:** the 119.1-04 SECURITY.md amendment (`34267d0`, "Encrypted secrets at rest" bullet) — same
file, same kind of drift-correction, same checkpoint timing (pre-tag, owner-caught precedent).

**Current (wrong) bullet, line 45:**
```markdown
- **IP-resolution guard on *arr connection URLs** — When you test or connect a Sonarr/Radarr server, the user-supplied URL is resolved via `socket.getaddrinfo` and rejected if it points to a private, loopback, reserved, or link-local IP. This is an IP-resolution SSRF guard on the *arr connection URL (not a full SSRF library; DNS-rebinding/TOCTOU is a documented out-of-scope limitation for a homelab tool). SeedSyncarr *receives* import webhooks; it does not send outbound webhooks.
```

**119.1-04 precedent for how to apply this kind of fix** (one line changed, nothing else in the file,
verified post-change with `node scripts/verify-release-metadata.mjs` + `git diff --stat`):
```
before: **Encrypted secrets at rest** — API tokens, webhook secrets, and *arr API keys are Fernet-encrypted in the config file ...
after:  **Encrypted secrets at rest (opt-in)** — Off by default: unless you set `[Encryption] enabled = True` in `settings.cfg`, secrets are stored in plaintext. When enabled, the seedbox password, API tokens, webhook secrets, and *arr API keys are Fernet-encrypted ...
$ git diff --stat
SECURITY.md | 2 +-
```
Apply the same one-bullet, minimal-diff discipline: replace only the IP-resolution guard bullet
with RESEARCH.md's suggested corrected wording (§"SECURITY.md correction required"), leave every
other bullet and the section intro untouched, verify with `git diff --stat -- SECURITY.md`.

---

### Version bump sites — `package.json` / `src/angular/package.json` / `src/python/pyproject.toml` / lockfiles (config, CRUD)

**Analog:** 119.1-REL04-EVIDENCE.md §"Release metadata" (exact command + exact output shape to reproduce) and §"Pitfall 2" in RESEARCH.md (the two sites the script does NOT check).

**Automated check (run after every bump, source: 119.1-REL04-EVIDENCE.md lines 169-183):**
```bash
$ node scripts/verify-release-metadata.mjs 1.8.0
Release metadata matches 1.8.0:
- CHANGELOG.md has release section [1.8.0]
- release-notes.md links to CHANGELOG.md through the {{VERSION}} tag placeholder
- package.json version is 1.8.0
- src/angular/package.json version is 1.8.0
- src/angular/package-lock.json version is 1.8.0
- src/angular/package-lock.json packages[""].version is 1.8.0
```

**Manual sites not covered by the script (verify by eye, same precedent):**
```bash
grep -n "version" package-lock.json | head -3          # root lockfile: .version + packages[""].version
grep -n "^version" src/python/pyproject.toml            # both [project] and [tool.poetry] lines
```

---

### Dependency lockfile regeneration — `src/angular/package.json` + `package-lock.json`, `src/python/poetry.lock`, root `package-lock.json` (config, batch)

**Analog:** `119-REL03-EVIDENCE.md` §"Dependabot roll-ins (D-21)" — this is the exact command shape to repeat at larger scale (8 PRs vs 2).

**Core regeneration pattern (lines 341-349):**
```bash
# Python (src/python), on the release branch:
poetry update cryptography pytz   # -> lockfile diff limited to those two packages, identical
                                   # versions to the PRs
poetry run pytest tests/unittests/test_common -q   # sanity: 187 passed

# Angular (src/angular):
npm update source-map-js   # -> 1.2.2 on both paths, no override needed
npm audit --audit-level=high   # confirm the targeted finding is gone
```

**1.8.0-scale application (from RESEARCH.md §"Dependabot Roll-In Mechanics" and §"Standard Stack"):**
```bash
cd src/python && poetry update certifi mkdocs-material testfixtures \
  && poetry run pytest tests/unittests -q

npm update puppeteer   # root package.json/package-lock.json

cd src/angular
# bump the one major range first: "@types/jasmine": "^6.0.0" -> "^7.0.0" in package.json
npx tsc --noEmit -p .                 # isolated compile check, per D-02/Pitfall 3
npm run test:ci 2>&1 | tail -30       # isolated Karma check before folding into the group bump
npm install                            # resolves the rest (@angular/cli, vite, follow-redirects,
                                        # @modelcontextprotocol/server, and the other 22 npm_and_yarn
                                        # packages) into one consistent lockfile diff
npm run lint && make -C ../.. run-tests-angular
npm audit --audit-level=low            # must show 0 remaining findings
```

**Verification gate, same shape as 119-REL03's "lockfile diff limited to those two packages":**
```bash
git diff --stat -- src/python/poetry.lock src/angular/package.json src/angular/package-lock.json \
  package.json package-lock.json
gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'   # expect 0
```

**Anti-pattern (explicitly do not do this):** cherry-picking PR #130's and #131's commits — both
touch `src/angular/package-lock.json`'s `@angular/cli` entry at different target versions
(22.2.3 vs 22.2.4) and will conflict or silently under-apply. Regenerate via `npm install`, never
`git cherry-pick`.

---

### `126-teardown.sh` (utility, event-driven idempotent restore)

**Analog:** `.planning/phases/125-lan-connection-tests/125-teardown.sh` (committed in repo, 160 lines) — copy as the starting point, per RESEARCH.md §"Reusable harness".

**Full structural pattern to copy (state-file read/write, idempotent restore, read-back verification):**
```bash
#!/usr/bin/env bash
# ... header comment documents: usage, what state.env keys mean, scope limits, idempotency ...
set -u

state_get() {
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
state_set() {
  [ -n "$D" ] || return 0
  printf '%s=%s\n' "$1" "$2" >> "$D/state.env"
}

SONARR_URL_L0="$(state_get SONARR_URL_L0)"
SONARR_URL_SET="$(state_get SONARR_URL_SET)"

get_sonarr_url() {
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty'
}
set_sonarr_url() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"sonarr",key:"sonarr_url",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}

# restore step: check current value, only act if it differs, verify by reading back
if [ "$SONARR_URL_SET" = "1" ] && [ -n "$SONARR_URL_L0" ]; then
  have="$(get_sonarr_url)"
  if [ "$have" != "$SONARR_URL_L0" ]; then
    set_sonarr_url "$SONARR_URL_L0"
    have="$(get_sonarr_url)"
  fi
  if [ "$have" = "$SONARR_URL_L0" ]; then
    echo "RESTORED sonarr_url ok"; state_set SONARR_URL_SET 0
  else
    echo "RESTORED sonarr_url FAIL"; fail sonarr_url
  fi
else
  echo "RESTORED sonarr_url ok (not set this session)"
fi
```

**Required extension for 126** (per RESEARCH.md Pattern 2 and the `code_context` instructions):
add a `RADARR_URL_L0` / `RADARR_URL_SET` key pair and `get_radarr_url()` / `set_radarr_url()`
functions mirroring the `sonarr_url` pair exactly, with `section:"radarr",key:"radarr_url"` in the
JSON body — same `config/get`/`config/set` shape, same idempotent-restore-with-read-back structure.

---

### `126-extract_secrets.py` (utility, file-I/O, count-only)

**Analog:** `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-extract_secrets.py` — copy verbatim (119.1-REL04-EVIDENCE.md §"Step 9" explicitly reuses this same script by sha256, no modification).

**Pattern to copy (value-free design, exact doc-string contract):**
```python
"""Read-only, value-free secret extractor for count-only log checks.
...
STDERR carries only field NAMES and counts:
    FIELDS <names> N=<set fields> LINES=<value lines written>
On any exception it prints only `ERROR <ExceptionClassName>` to stderr and
exits 3; exception messages are never printed (ConfigError messages can
embed values). Never writes a file and never creates a key file.
"""
import sys
sys.path.insert(0, "/app/python")
CONFIG_DIR = "/c"

def main() -> int:
    from common import Config
    from seedsyncarr import Seedsyncarr
    settings_name = getattr(Seedsyncarr, "_Seedsyncarr__FILE_CONFIG")
    key_name = getattr(Seedsyncarr, "_Seedsyncarr__FILE_SECRETS_KEY")
    with open(os.path.join(CONFIG_DIR, settings_name), "rb") as f:
        text = f.read().decode("utf-8")
    Config.set_keyfile_path(os.path.join(CONFIG_DIR, key_name))
    config = Config.from_str(text)
    # ... writes decoded + serialized-on-disk value lines to stdout, field names to stderr only
```

**Invocation pattern (119.1-REL04-EVIDENCE.md §"Step 9", Pattern 3 in RESEARCH.md):**
```bash
sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL \
  --user 1026:100 -v /volume1/docker/seedsync:/c:ro --entrypoint python3 -w /app/python \
  ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<digest> - < 126-extract_secrets.py > "$T/values" 2> "$T/fields"
sudo /usr/local/bin/docker logs seedsyncarr > "$T/log" 2>&1
grep -cFf "$T/values" "$T/log"   # must print 0; rc=1 confirms no match
```
Do not print any matched value — only match counts, field names, HTTP codes (the established
hygiene bar, no exceptions).

---

### Release evidence files — `126-REL-EVIDENCE.md` / `126-SMOKE-EVIDENCE.md` / `126-DEPLOY-EVIDENCE.md` (test/record, batch + event-driven)

**Analog:** `119.1-REL04-EVIDENCE.md` (1344 lines — the single most complete analog: covers
dependency recheck, merge/tag, GHCR/GitHub/PyPI publish verification, NAS smoke, and prod deploy
all in one file) plus `122-SAFE01-EVIDENCE.md` (sandbox-only deploy/teardown pattern) and
`119-REL03-EVIDENCE.md` (Dependabot roll-in evidence format). The planner may split 126's evidence
across 2-3 files matching the wave structure (dependency/release-content, smoke, deploy) or follow
119.1's single-file precedent — discretion per CONTEXT.md.

**Hygiene preamble to reuse verbatim in spirit (119.1-REL04-EVIDENCE.md lines 8-11):**
```markdown
Hygiene: only test names, exception class names and counts are recorded. No secret value, no test
sentinel value and no captured test stdout appears in this file.
```

**Dependabot re-check block (reuse exact shape, 119.1-REL04-EVIDENCE.md lines 185-199 and 334-348,
run twice: once before the PR push, once immediately before `git tag` per D-04):**
```bash
$ gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'
0
$ gh pr list --author app/dependabot --json number,title,createdAt
```

**Merge + tag block (119.1-REL04-EVIDENCE.md lines 350-374):**
```bash
$ gh pr merge <N> --merge --subject "Merge 1.8.0 release (#<N>)"
$ git tag -a v1.8.0 -m "SeedSyncarr 1.8.0 — <summary>" <merge-sha>
$ git cat-file -t v1.8.0        # expect: tag
$ git rev-parse v1.8.0 v1.8.0^{commit}
$ git push origin v1.8.0
```

**Publish verification block — GHCR digest, GitHub Release, PyPI (119.1-REL04-EVIDENCE.md lines
376-462), two independent digest-resolution methods, cross-checked:**
```bash
docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.8.0
# or:
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -I -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.oci.image.index.v1+json" \
  "https://ghcr.io/v2/thejuran/seedsyncarr/manifests/1.8.0" | grep -i docker-content-digest

$ gh release view v1.8.0 --json name,tagName,url,isDraft,isPrerelease
$ pip install --no-cache-dir seedsyncarr==1.8.0   # clean scratch venv, INSTALL_EXIT=0
```

**Sandbox smoke block (122-SAFE01-EVIDENCE.md's "Build under test" + 119.1-REL04's "Smoke test on
NAS" Steps 0-9, adapted: `seedsyncarr-test` instead of a throwaway container, per D-11):**
```markdown
## Build under test
- **Tag/digest:** ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<digest>
- **Digest resolution (two independent methods, cross-checked)**
## Sandbox deploy
<repin seedsyncarr-test, record IMAGE_PIN_L0 and SONARR_URL_L0/RADARR_URL_L0 to state.env
 before any change — mirrors 125-teardown.sh's own state contract>
```
D-12a's per-check verdicts (restart / real transfer / Sonarr-v4 + Radarr integration / cleanup /
Test Connection container-name + metadata-IP refusal / no-secrets / no-app-token / webhook test
event) should each get a `Verdict: **PASS**` line in the same style as 119.1-REL04-EVIDENCE.md
Steps 1-9 (e.g. "Verdict, real transfer: **PASS** (in-flight name only `smoke-a.bin.lftp`, renamed
on completion, sha256 match, final `downloaded`, `hold_reason: null`)").

**Prod deploy block (119.1-REL04-EVIDENCE.md's unread remainder + RESEARCH.md §"Prod Deploy +
wud + Backups", exact command recipe already adapted for 1.8.0 in RESEARCH.md lines 440-474):**
```bash
ssh nas 'sudo /usr/local/bin/docker inspect wud --format "{{.State.Status}}"'
ssh nas 'cd /volume1/docker && cp -p docker-compose.yml docker-compose.yml.pre-1.8.0-<TS>'
ssh nas 'sudo /usr/local/bin/docker pull -q ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<digest>'
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop seedsyncarr'
ssh nas 'cd /volume1/docker/seedsync && cp -p settings.cfg settings.cfg.pre-1.8.0-<TS> && \
  cp -p controller.persist controller.persist.pre-1.8.0-<TS> && \
  cp -p autoqueue.persist autoqueue.persist.pre-1.8.0-<TS> && sha256sum *.pre-1.8.0-<TS>'
# sed to a temp file, cat back — never redirect directly (inode-preserving compose edit)
ssh nas 'cd /volume1/docker && sed "s|seedsyncarr:1.7.6@sha256:da6196e0…|seedsyncarr:1.8.0@sha256:<digest>|" \
  docker-compose.yml > /tmp/dc.new && cat /tmp/dc.new > docker-compose.yml && rm /tmp/dc.new'
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose up -d seedsyncarr'
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose start wud'   # restored LAST
```
Reuse `118-05-parse_check.py` (sha256 `920363ac3693d1528ece37114e870cf00cb8b75b718663bc2ef5d446b3f5dd53`,
unchanged, verbatim) for the before/after persist-file loader check — guaranteed PASS per
RESEARCH.md's rollback-safety finding (zero diff to `persist.py`/`config.py` since 1.7.6).

---

### `.planning/STATE.md` (config, CRUD)

**Analog:** same file's own prior phase-transition updates (e.g. the 123/125-completion entries) —
no external analog needed; this is a direct field-correction edit (PR #140 draft→merged, per
CONTEXT.md "Specifics": "STATE.md says PR #140 is 'draft, not merged'. That's stale... Correct it
during the state update.").

---

## Shared Patterns

### Dependabot/alert triage query shape
**Source:** `119.1-REL04-EVIDENCE.md` lines 189-199, 338-348; `119-REL03-EVIDENCE.md` lines 341-349
**Apply to:** all dependency roll-in work and both owner-checkpoint dependency-list presentations (D-05)
```bash
gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'
gh pr list --author app/dependabot --json number,title,createdAt
```

### NAS command safety (absolute docker path, inode-preserving compose edits)
**Source:** `119.1-REL04-EVIDENCE.md` §"Prod Deploy", global CLAUDE.md "NAS docker access" rule
**Apply to:** every NAS-touching step in the dependency/smoke/deploy evidence files
```bash
sudo /usr/local/bin/docker ...      # never bare `sudo docker` over non-interactive ssh
# compose edits always: sed to a temp file, cat back — never redirect directly into the compose file
```

### Count-only secret verification
**Source:** `119.1-extract_secrets.py`, Pattern 3 in RESEARCH.md
**Apply to:** `126-extract_secrets.py` reuse, any evidence file touching a secret field
Never print a matched value; print only field names, match counts, and HTTP status codes.

### Idempotent sandbox restore with read-back verification
**Source:** `125-teardown.sh`
**Apply to:** `126-teardown.sh` (extended with `radarr_url`)
Every restore step reads the current live value first, only writes if it differs, then re-reads to
confirm — never trust a write's own success response.

### Rollback runbook structure (7 steps)
**Source:** `release-notes.md` 1.7.6 "If you need to roll back" section; RESEARCH.md §"Rollback
Safety" recommended structure
**Apply to:** `release-notes.md`'s 1.8.0 rollback section
```
1. Stop wud
2. Stop seedsyncarr
3. Restore the three persist files (with checksum verification)
4. Force AutoDelete.enabled = False in the restored settings.cfg
5. Verify
6. Re-pin compose to :1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
7. docker compose up -d, verify, restore wud last
```
Per RESEARCH.md: drop the 1.7.6-era "rotate again, credentials get reprinted" caution (does not
apply to a 1.8.0→1.7.6 rollback, since 1.7.6 already has SEC-01); keep the `%`-in-secrets caution
and the AutoDelete caution verbatim.

### Two-checkpoint owner approval gate
**Source:** `119.1-REL04-EVIDENCE.md` §"Owner decision (Plan 119.1-03 Task 3)" / §"Owner approval"
**Apply to:** D-13's two checkpoints (pre-tag, pre-prod-deploy)
Record the owner's verbatim decision text, what was shown (notes, dependency list, CI status / smoke
results), and what it authorized — do not infer approval from silence or proceed past "ask" language.

---

## Conventions

Derived via the shared `gsd-tools.cjs verify conventions --derive` module (repo-wide; the scope
covers the mixed Python/Angular/Node tree this phase's version-bump and script files sit in):

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| File-name casing | (mixed — no single dominant form) | 52.1% | 0.832 | contested hotspot |
| Identifier casing | camelCase (vs Pascal/CONSTANT/snake) | 50.6% | 0.611 | contested hotspot |
| Export style | ESM (`export`) | 64% | 0.943 | contested hotspot |
| Import style | ESM (`import`) | 92.9% | 0.371 | named contract |

**Contested hotspots (author's choice).** Below the 70% dominance bar, a convention is the
author's choice per-directory, not a repo-wide rule to enforce. The prototype case for this
pattern is a CJS↔ESM dual resolver split — one subtree using CJS `module.exports`/`require`,
a sibling subtree using ESM `export`/`import` — where each half is internally consistent and the
split is contested only when measured repo-wide. In this repo, the analogous split is
Python (`src/python`, snake_case identifiers, absolute/relative imports mixed per module) versus
Angular/TypeScript (`src/angular`, camelCase/PascalCase, ESM imports) versus the root Node tooling
(`package.json`, `scripts/*.mjs`, mixed CJS test files) — three internally-consistent ecosystems
that only look "contested" when the axis is computed across all of them at once. For this phase's
files, match the local ecosystem: JSON/TOML/Markdown metadata files have no identifier-casing axis
to violate; any new shell/Python evidence scripts should match `119.1-extract_secrets.py`'s
snake_case/explicit-import style (already the dominant Python convention), and any new `.mjs`
tooling should match `scripts/verify-release-metadata.mjs`'s ESM import/export style (the named,
92.9%-dominant contract for this axis).

## No Analog Found

None. Every file this phase touches has a direct, same-role precedent from the 119/119.1/122/125
release chain.

## Metadata

**Analog search scope:** `.planning/phases/119-safety-follow-ups-and-1-7-5-release/`,
`.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/`,
`.planning/phases/122-safety-acceptance-and-logging-fixes/`,
`.planning/phases/125-lan-connection-tests/`, `.planning/phases/118-durable-state/`,
repo root (`CHANGELOG.md`, `release-notes.md`, `SECURITY.md`, `package.json`,
`src/angular/package.json`, `src/python/pyproject.toml`, `.github/workflows/ci.yml`,
`.github/dependabot.yml`, `scripts/verify-release-metadata.mjs`)
**Files scanned:** 18 target files + 9 analog/source files read in full or by targeted range
**Pattern extraction date:** 2026-10-28
