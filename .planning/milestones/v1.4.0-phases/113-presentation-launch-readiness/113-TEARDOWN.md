# Cynical-Reader Teardown — SeedSyncarr README (current, pre-rewrite)

**Framing:** r/selfhosted commenter, first impression in 30 seconds. I'm looking at the repo cold — no prior context, just clicked a link on a thread. I give every project a fair read before I dismiss it, but I'm not going to chase down things that should be obvious.

---

## First Impressions

The wordmark renders fine in dark mode (I'm on GitHub dark by default), and having both light/dark sources in a `<picture>` element is a nice touch — shows the maintainer thought about presentation. But that's immediately undercut by the first thing GitHub shows me in the sidebar: **"No license."** I can already see there's a `LICENSE.txt` in the file tree, so I know it's Apache 2.0, but GitHub didn't detect it because the filename ends in `.txt`. That's a credibility hit before I read a single line of text. It signals either inattention to detail or someone who set up the repo once and never checked how it looked to a stranger. If you don't know GitHub only recognizes files named exactly `LICENSE`, that's fine — everyone misses it once — but it should be fixed before you put this in front of people.

The dashboard screenshot is dark and functional-looking, but it's small and I can't make out much detail. There's also a duplicate screenshot — the same `screenshot-dashboard.png` appears both in the header block at line 9 AND again in a "Screenshots" section at line 101. That reads as a copy-paste artifact that nobody cleaned up, and it reinforces the "solo project, rough edges" read.

The one-liner is generic: "Sync files from your seedbox to your local media server — fast, automated, and integrated with Sonarr and Radarr." Every seedbox sync tool says something in this family. I learn nothing about why this one exists or what makes it worth installing over the alternatives.

The badge row has CI (green, presumably), Release, Docker, and License. The License badge either shows "No license" or throws an error because the Shields.io GitHub license API relies on the file being named `LICENSE`. This is consistent with the sidebar, and doubly visible.

---

## Credibility Gaps

**"Integrated with Sonarr and Radarr"** — this is listed as a bullet in Features and in the one-liner. Fine as a claim, but the feature section doesn't tell me *what that integration actually does*. There are two completely different ways an *arr integration can work: you can push file-ready notifications to *arr, or you can receive import webhooks *from* *arr and act on them. These are fundamentally different workflows with different implications for who is "in charge." I have to read all the way to the Usage Examples section (line 132, buried well below the fold) to understand that SeedSyncarr *receives* import webhooks from Sonarr/Radarr and uses them to trigger safe auto-delete. That's actually the interesting part. The feature list buries the lede entirely.

**Sole-fork bravado risk** — there's no fork relationship note anywhere. I immediately search GitHub for "seedsync" forks and find there's at least one other active maintained fork (nitrobass24). If the README were to claim to be the only active fork or the "canonical" continuation, I'd flag it. Currently the README is silent on this, which isn't wrong, but it reads as if the project appeared from nothing. A "this is a fork of X" note is standard for forks that diverge from the original, and the absence of one is a small credibility drag for anyone doing due diligence.

**"See the documentation"** links to `https://thejuran.github.io/seedsyncarr` (line 85). Does that URL actually resolve? Documentation links that 404 are worse than no documentation link at all. I'd click this in my review — if it 404s, that's a red flag. (This is a verifiable item, not a teardown assumption, but the README puts it forward as a resource without confirmation it's live.)

**Security claiming without a surface-level summary** — SECURITY.md is linked at the bottom (line 114), but there's no mention of what security features the tool actually implements. The existing SECURITY.md is a reporting policy, not a posture description. A self-hosted tool that runs as a service on your local network, connects to remote servers, and auto-deletes files on your local disk *should* lead with what it does to protect you. Right now the README says nothing about auth, webhook verification, or anything else. For a tool this potentially destructive (auto-delete path), I want to see evidence that the author thought about security before I run it.

**The pip install path** — `pip install seedsyncarr`. Is this package actually on PyPI under that name? A quick check would tell me, but the README presents this as a first-class install method with no caveat. If the package doesn't exist on PyPI or is stale, a user following this path hits a dead end and the project looks abandoned. This is the second call-to-action in the readme and it needs to be reliable.

---

## Install Path Issues

**Docker Quick Start** — the docker-compose snippet is clean and minimal. Volume mounts are clear. I can run this. The only question is: what happens first time? The README tells me to open `http://localhost:8800` and configure in Settings. Fair enough, but there's no note about what state the app is in until I configure it — is it running but idle? Is there a health check endpoint? For the Docker path, the install-to-first-use flow is actually the strongest part of this README.

**pip path** — "Install system dependencies first, then install via pip." The listed system deps are: `lftp openssh-client p7zip-full unrar bzip2`. This list looks Debian/Ubuntu-centric and the comment says as much — but there's no note for macOS users (who need `brew install lftp`) or rpm-based distros. More importantly: `openssh-client` is almost certainly already installed on any Linux system that has `ssh`. Listing it suggests the author is copying a dependencies list without thinking about who actually runs this. `Poetry` is listed as a prerequisite in CONTRIBUTING.md but isn't mentioned in the README pip install section — is Poetry required for end users? If not, why is it listed as a contributor prerequisite but not clarified here?

**"Requires Python 3.11 or 3.12"** — the CI comment says 3.12, CONTRIBUTING says "Python 3.11+ (CI runs 3.12)." The README says 3.11 or 3.12. These are slightly inconsistent signals. A user on Python 3.13 doesn't know if they should try or not.

**No version pinning or release tag in Docker snippet** — the Quick Start uses `:latest`. That's fine for a demo, but it means users following this path won't know when they break on a major-version update. This is a minor point but it's the kind of thing homelab users on r/selfhosted mention every single time.

**The `POST /server/config/set` endpoint** — this is Phase 111 work, already in scope, but for the teardown record: if the current code uses a GET endpoint for config/set (with credentials in the URL), that is a real operational concern. Logs, browser history, and reverse-proxy logs all capture GET URLs verbatim. A hostile reader who scans the API surface will find this. After Phase 111 ships this is moot for the rewrite, but the teardown should flag it.

---

## Security Claims

**No security posture up front** — the current README has zero security claims in the main body. The only security reference is a one-liner: "See [SECURITY.md](SECURITY.md) for reporting vulnerabilities." The existing SECURITY.md is a responsible-disclosure policy with best-practice bullets — nothing about what the tool actually does to protect users.

This is the biggest presentation gap given the tool's actual posture. The code ships with: Fernet encryption at rest for secrets, HMAC-SHA256 verified webhooks, Bearer token auth (opt-in), an IP-resolution guard on *arr connection URLs, hash-based CSP, and rate limiting on specific endpoints. None of this is visible anywhere in the README. For a self-hosted tool that auto-deletes files, a reader who doesn't see any security claims in the first screen is going to assume there are none.

**The SECURITY.md contact method** — the email listed is `thejuran@users.noreply.github.com`. GitHub noreply addresses are not guaranteed to work for inbound email in a security-disclosure context. GitHub's private security advisory feature (`https://github.com/thejuran/seedsyncarr/security/advisories/new`) is the maintained path for this. Using a noreply address looks like a template that was never updated.

**HMAC webhook default behavior** — the SECURITY.md best-practices bullets say "Use strong passwords for SSH connections" and "Restrict network access" but say nothing about enabling `webhook_require_secret`. A user reading this file has no indication that fail-closed webhook behavior requires an opt-in setting. This is actually a meaningful security configuration that deserves a sentence.

**What the security section does NOT oversell:** to the current README's credit, it doesn't claim things that aren't true. There are no "enterprise-grade security" assertions, no claim of being a security-first tool, no mention of CVE counts or audit results. The problem is the opposite — undersell, not oversell. A reader who cares about security is more likely to dismiss the project than to be alarmed by inflated claims.

---

## What Actually Lands

**The code quality signals are genuinely good for this class of project.** Running `ruff check src/python/` comes back clean. Semgrep auto-rules (320 rules, 92 files) hits zero findings. gitleaks finds nothing across 1,172 commits. These are not trivial results — injection patterns, secret detection, command-execution risks, all clean. A skeptical engineer who runs the obvious tools in the first five minutes gets a green result on every one of them.

**~89% Python test coverage with a CI-enforced floor** is legitimately impressive for a solo-maintained self-hosted tool. Most projects in this space have ad-hoc or absent test suites. The CI setup (amd64 + arm64, coverage gates, Playwright E2E) signals engineering discipline, not vibes.

**The Docker setup is clean.** The quick-start snippet is minimal, the image is on GHCR, and the configuration story (everything via the web UI after first run) is reasonable. The integration story for Sonarr/Radarr — once you read deep enough to understand it — is actually well-thought-out.

**The HMAC-verified auto-delete safety guarantee** is the correct differentiator for this tool. "You never delete a file that didn't make it into your library" is a real, specific, user-valuable property. The current README buries it in Usage Examples. Moving it above the fold would transform how the project reads to an informed r/selfhosted reader.

**The Features list is honest.** It doesn't overclaim. "Sonarr and Radarr integration — webhook-driven import notifications" is accurate if underspecified. AutoQueue, LFTP-based transfers, dark mode — all present and correct.

---

## Priority Fixes Before Rewrite Finalization

1. **Rename `LICENSE.txt` to `LICENSE` and update all badge links.** This is the single most visible credibility signal on the repo page. It costs 30 seconds. The shields.io license badge, README line 118, and ACKNOWLEDGMENTS.md all reference `LICENSE.txt` and will break or render incorrectly until this is fixed.

2. **Rewrite the one-liner to lead with the owned differentiator.** The current one-liner is interchangeable with any seedbox sync tool. The specific claim — "an HMAC-verified import webhook drives safe auto-delete so you never delete a file that didn't reach your library" — needs to be in the first sentence, not page two.

3. **Add a security selling point near the top of the README.** The tool ships with Fernet encryption at rest, HMAC-verified webhooks, Bearer auth, an IP-resolution guard on *arr connection URLs, CSP headers, and rate limiting. None of this is visible to a first-time reader. Even a single sentence ("security by default — Fernet-encrypted secrets, HMAC-verified webhooks, and an IP-resolution guard on *arr connection URLs; see SECURITY.md") changes the narrative from "unknown self-hosted tool" to "someone actually thought about this."

4. **Add a Security Posture section to SECURITY.md.** The current file is a responsible-disclosure policy, which is necessary but not sufficient. A reader who follows the SECURITY.md link should find what protections are active by default and what requires opt-in configuration (particularly `api_token` for non-loopback binds and `webhook_require_secret = true` for fail-closed webhooks). This doubles as a selling point and as an honest "here's what this tool does and doesn't protect."

5. **Add a fork relationship note.** "SeedSyncarr is a fork of SeedSync (ipsingh06). Like other active forks, it modernizes the original; SeedSyncarr's focus is a Sonarr-driven workflow where an HMAC-verified import webhook drives safe auto-delete — so you never delete a file that didn't reach your library." This pre-empts the most obvious hostile follow-up question. Do not name the sibling fork directly, do not claim to be the only active fork, frame the absent outbound-push as scope choice not advantage.

6. **Fix the duplicate screenshot** (appears at line 9 and again at line 101). Keep the hero position at line 9; the Screenshots section at line 101 is where the 3-shot set from the milestone-end walkthrough will live. Until those are captured, the duplication is noise.

7. **Update the SECURITY.md contact** from `thejuran@users.noreply.github.com` to the GitHub private security advisory link (`https://github.com/thejuran/seedsyncarr/security/advisories/new`). A noreply address in a security policy is not a maintained reporting channel.

8. **Verify the pip install path is live** (PyPI package exists, name is correct, Python version constraints are consistent). If `pip install seedsyncarr` doesn't work, remove it from the README rather than leaving it as a dead-end install path.
