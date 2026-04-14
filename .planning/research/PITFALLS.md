# Pitfalls Research

**Domain:** Open source project rebrand (fork→standalone), curated list submissions, *arr/self-hosted community launch
**Researched:** 2026-04-08
**Confidence:** MEDIUM-HIGH — curated list criteria verified via official CONTRIBUTING.md; AI-code scrutiny dynamics from multiple sources including academic research; community launch patterns from practitioner experience

---

## Critical Pitfalls

### Pitfall 1: Fork Attribution That Looks Like Theft

**What goes wrong:**
The new repo (thejuran/seedsyncarr) is created from a fork of a fork. If the README only mentions the upstream origin once, buried at the bottom, without a live link — the community perception is that the author is taking credit for upstream work. This was called out explicitly in a prominent Hacker News thread on forking ethics. At minimum the project looks deceptive; at worst it triggers accusations of plagiarism on r/selfhosted.

SeedSync is itself a maintained fork of an upstream project with its own history. SeedSyncarr is a rename + standalone spin-out of that fork. The fork chain is: [upstream seedsync] → thejuran/seedsync → thejuran/seedsyncarr. Each link in that chain needs to be documented in the README, not as fine print but as part of the identity story ("SeedSyncarr started as a maintained fork of SeedSync by..." at the top of the README).

**Why it happens:**
Authors focus on the new thing they built and downplay the starting point to avoid looking derivative. But omitting the origin doesn't make the fork history invisible — GitHub shows it in the repository metadata, and anyone who spots the discrepancy will surface it publicly.

**How to avoid:**
- Put attribution in the first section of the README, not the last
- Frame the origin story positively: "grew out of maintaining a fork" signals commitment and continuity, not copying
- Link to the upstream repo with a sentence explaining what changed and why a standalone project was needed
- Do not use language like "built from scratch" or "completely new project" — the git history contradicts this

**Warning signs:**
- README intro says nothing about fork origin
- CHANGELOG starts at v1.0.0 with no mention of prior version history from SeedSync
- "About" section in GitHub repo lists no related projects or origins

**Phase to address:**
Phase: Rebrand & Rename — write README origin story in Phase 1, not as an afterthought in the launch phase.

---

### Pitfall 2: AI-Generated Code Signals Triggering Community Rejection

**What goes wrong:**
The 2026 open source community is acutely sensitive to AI-generated code. Maintainers of major projects (Ghostty, tldraw, cURL) have explicitly banned or rejected AI contributions. The *arr ecosystem (Sonarr, Radarr) has technically sophisticated communities who will review the code before trusting the project.

This project is AI-assisted by design. Triggarr was rejected from Awesomarr despite 60 stars. If reviewers read the code and see the specific patterns that AI generates — excessive comments explaining obvious operations, over-engineered abstractions without clear purpose, inconsistent code style in different files (because different AI sessions produce different patterns), hallucinated imports that were later corrected but left a residue of unnecessary shim layers — they will flag the project as "AI slop" and the rejection will be public and permanent for that listing round.

Academic research (CodeRabbit, 2025) found AI-assisted code has approximately 1.7x more "major issues" than human-written code. Reviewers have internalized this: when they see AI signals, they scrutinize harder and are primed to find problems.

**Why it happens:**
AI tools generate verbose, defensively structured code by default. Without deliberate cleanup, the output contains:
- Comments that restate what the code does instead of why
- Exception handlers that catch too broadly then do nothing
- Duplicate logic that wasn't recognized as duplication because it appeared in different AI sessions
- Variable names and docstring styles that are inconsistent across files written at different times
- Unnecessary type annotations in dynamic contexts, or missing ones in places that matter
- Code that handles edge cases that don't exist in this application's domain (generic AI over-generalization)

**How to avoid:**
Before submission to any list or community post:
1. Do a code audit specifically hunting for AI tells: remove comments that explain what (keep only why), audit exception handling for bare `except` or silent catches, find and deduplicate similar logic across files
2. Ensure style is consistent across all files — same naming conventions, same docstring format, same import ordering throughout
3. Remove any dead code paths, unused imports, or functions that exist "just in case"
4. Have the codebase reviewed as if it is being submitted for a code challenge — ask: "would a senior developer be embarrassed by any of this?"
5. The Phase: Harden for Scrutiny work (dead code removal, test audit) must explicitly target AI artifact patterns, not just functional bugs

**Warning signs:**
- Comment density is high relative to code complexity (comments on obvious operations)
- Exception handling is broader than necessary in multiple files
- Similar utility functions appear in different modules with slightly different signatures
- Import sections contain items not used in that file
- Method docstrings use generic descriptions that don't match the actual parameters

**Phase to address:**
Phase: Harden for Scrutiny — this is the primary purpose of that phase. Must include explicit AI-artifact audit checklist, not just a generic code review.

---

### Pitfall 3: Submitting to Curated Lists Too Early

**What goes wrong:**
Submitting to awesome-selfhosted or Awesomarr before the project has earned social proof results in rejection that is visible in the PR history. Rejected PRs become part of the project's public record. If someone googles "seedsyncarr awesome-selfhosted" in the future, they find the rejected PR and the reason for rejection. A premature submission sets a negative first impression that is hard to recover from.

**Why it happens:**
The author is excited to launch and treats list submission as a launch activity. But curated lists have specific, hard gates:

- **Awesome-selfhosted**: Requires project was first released more than 4 months ago. Projects are removed if no development activity for 6-12 months. Rejects projects where installation docs are missing or broken. Does not explicitly require a star count, but maintainers do look at "community interest" signals.
- **Awesomarr (awesome-arr)**: Requires minimum 50 GitHub stars. No stars = instant rejection regardless of code quality.

SeedSyncarr v1.0.0 will have zero stars on launch day. The Awesomarr submission cannot happen until the project has organically accumulated 50+ stars. Submitting on day one wastes the opportunity and burns the PR slot.

**How to avoid:**
- Do NOT submit to Awesomarr until the repo has 50+ stars — this is a hard, documented requirement
- Do NOT submit to awesome-selfhosted until at least 4 months after the v1.0.0 tag is pushed
- Sequence community outreach to build stars naturally BEFORE attempting list submissions
- Treat list submissions as milestone goals (e.g., "submit to Awesomarr when 50 stars reached") not as launch-day activities

**Warning signs:**
- Submission PR is opened within weeks of first release
- Repo has fewer than 50 stars at time of Awesomarr submission
- Installation docs are not tested end-to-end before submitting

**Phase to address:**
Phase: Community Launch — make list submission a conditional follow-up activity, not part of the launch phase itself. Include explicit star-count gate in the phase's "done" criteria.

---

### Pitfall 4: The "New Name, Same Problems" Reception

**What goes wrong:**
If the v1.0.0 release has visible quality issues — outdated dependencies, failing CI on certain platforms, sparse documentation, or a README that reads like marketing copy — the community will flag it as a low-effort rebranding exercise. The self-hosted community is deeply skeptical of projects that launch with fanfare but lack depth. Reddit posts for projects like this often get top-level comments like "this is just X with a new name" or "what does this actually add?"

This is distinct from the attribution pitfall (Pitfall 1) — it's about whether the project demonstrates genuine craft and maintenance investment, not just whether attribution is given.

**Why it happens:**
Rebranding milestones focus on presentation (new name, new README, launch posts) and skip the quality work. The tendency is to ship the rebrand quickly and handle quality later. But community first impressions are sticky — a poor reception on r/selfhosted or the Servarr Discord will define how people talk about the project for months.

**How to avoid:**
- Harden first, rebrand second — do the code quality work (Harden phase) before writing the community-facing content (Present phase) so the README's claims are supported by the code
- Run CI green with zero lint errors before any launch post
- Have working Docker Compose install instructions that work on first try — test from a clean environment, not from the dev machine
- Ensure the GitHub releases page has meaningful changelogs, not just "initial release"
- Fix any open issues or Dependabot alerts before launch — a project with 10 open security alerts on day one signals poor maintenance

**Warning signs:**
- CI is not green at time of launch post
- Dependabot shows open security alerts on the new repo
- Docker Compose instructions have not been tested end-to-end on a clean machine
- Release notes say "see commit log" instead of describing what the tool does and why it matters

**Phase to address:**
Phase: Harden for Scrutiny must precede Phase: Present. The launch post should be the last activity, not the second.

---

### Pitfall 5: Docker Hub vs GHCR Confusion After Rebrand

**What goes wrong:**
The project currently publishes to `ghcr.io/thejuran/seedsync`. After rebrand, it should publish to `ghcr.io/thejuran/seedsyncarr`. If CI is not updated atomically, there is a window where the old image name is published (or not published) and the new name doesn't exist yet. Users following the old image tag get stale software. New users following the README get 404s.

Additionally, if the new repo's CI references the old registry path in docker-compose examples, users who copy-paste the compose file will pull the wrong (or non-existent) image. This class of error generates immediate negative feedback because it prevents the most basic "does this work" test.

**Why it happens:**
Registry paths are hardcoded in multiple places: CI workflow YAML, docker-compose.yml examples, README install section, CLAUDE.md, and sometimes in the Angular `environment.ts` files or Python version strings. It's easy to miss one.

**How to avoid:**
- Audit all occurrences of `ghcr.io/thejuran/seedsync` before first push to the new repo
- Update CI to publish to the new image name in the same commit that changes the README
- Test the new image path actually exists and pulls successfully before sending any community posts
- Use `grep -r "seedsync"` on the entire codebase during rebrand to find missed references

**Warning signs:**
- README shows `ghcr.io/thejuran/seedsyncarr` but CI still pushes to `ghcr.io/thejuran/seedsync`
- Docker Compose example in docs uses a different image path than what CI publishes
- First GitHub release is created before CI successfully publishes the image

**Phase to address:**
Phase: Rebrand & Rename — image name update must be part of the atomic rename sweep, with a CI smoke test confirming the new image path is reachable before the phase closes.

---

### Pitfall 6: Announcing in the Wrong Channel at the Wrong Time

**What goes wrong:**
Cross-posting an announcement to r/selfhosted, r/sonarr, r/radarr, r/homelab, and the Servarr Discord simultaneously on day one triggers Reddit's spam detection and gets removed, or the posts read as spam to community moderators. Subreddits have rules about self-promotion frequency; posting the same project to 5 communities within hours is a known spam pattern.

Separately: announcing in the Servarr Discord without reading the community norms first often backfires. The *arr community values technical depth — a generic "check out my new project!" message without specifics about how it integrates with Sonarr/Radarr will be ignored or downvoted.

**Why it happens:**
Launch day excitement drives "post everywhere at once" behavior. The author wants maximum exposure immediately.

**How to avoid:**
- Start with r/selfhosted only, with a substantive "I built this to solve X" post, not a promotional announcement
- Wait until the r/selfhosted post has organic traction (20+ upvotes, comments) before crossposting
- Customize the post title and framing for each community (r/selfhosted: general utility; Servarr Discord: specific *arr integration details)
- Space posts over 24-48 hours minimum to avoid spam detection
- Engage with every comment on the first post within the first hour — the algorithm and community reception are both much better when the author is present

**Warning signs:**
- Planning to post to more than 2 communities on launch day
- Post title is the same across all communities
- No community-specific framing prepared (Servarr Discord requires *arr-specific angle)

**Phase to address:**
Phase: Community Launch — write community post drafts during the Present phase so they are customized and ready, not improvised on launch day.

---

### Pitfall 7: Servarr Wiki Listing Requirements Not Met

**What goes wrong:**
The Servarr Wiki "Useful Tools" page is a key discovery channel for the *arr ecosystem. Getting listed there provides organic traffic from users already running Sonarr/Radarr. However, the wiki lists tools that are "companions to the *Arr Suite of Applications" and have clear, working documentation. If the mkdocs site is not deployed, or the Sonarr/Radarr integration story is not clearly explained on the landing page, the wiki PR will be held until docs are complete.

**Why it happens:**
The mkdocs site is planned but often deprioritized because it feels like polish. In practice, documentation quality is what curators check when evaluating whether a tool is production-ready.

**How to avoid:**
- Deploy the mkdocs docs site before attempting a Servarr wiki PR
- Include a dedicated "Integration with Sonarr/Radarr" page in the docs, not just a mention in the README
- The install page must have a Docker Compose example that is tested and current

**Warning signs:**
- Servarr wiki PR submitted before mkdocs site is live
- mkdocs site has only index.md and install.md, nothing on *arr integration

**Phase to address:**
Phase: Present — mkdocs deployment must be completed and verified before any wiki submission attempt.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Submit to curated lists before earning stars | Early visibility | Burned PR slot, negative public record | Never — wait for 50+ stars |
| Launch post before CI is green | Faster launch date | First responders find build failures; sets tone of "broken project" | Never — CI must be green at launch |
| Generic README copied from template with minimal customization | Saves time | Reads as low-effort; doesn't differentiate from the upstream fork | Never for a community launch |
| Archive old repo silently with no redirect | Avoids confusion about which repo to use | Existing users have no migration path; old stars don't transfer | Never — post a pinned notice and link |
| Keep AI-verbose comments to explain the codebase | "Helpful" documentation | Signals AI generation to technical reviewers | Never in community-facing code |
| Cross-post announcement to all communities same day | Maximum reach immediately | Reddit spam detection, looks like promotion not contribution | Never — stagger by 24-48 hours |

---

## Integration Gotchas

Common mistakes when connecting to community platforms and registries.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GHCR image rename | CI updated but README not, or vice versa | Atomic: update CI, README, docker-compose.yml, and docs in same PR |
| awesome-selfhosted submission | Submitting before 4-month age requirement | Track release date; submit no earlier than 4 months post-v1.0.0 tag |
| Awesomarr submission | Submitting before 50-star requirement | Hard gate: do not open PR until repo has 50+ stars |
| Servarr wiki | Submitting with no *arr-specific docs page | Deploy mkdocs with dedicated integration page first |
| Reddit r/selfhosted | Generic announcement post with no story | Frame as "I built X to solve Y" with specific problem statement |
| Servarr Discord | Copy-paste announcement from Reddit | Customize for *arr audience: emphasize Sonarr/Radarr webhook flow |
| GitHub repo archive | Archive without forward notice | Pin a notice on old repo for 30+ days before archiving |

---

## Security Mistakes

Mistakes that would surface during curator or community code review and undermine trust.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Shipping Dependabot alerts open on new repo | First thing curators check; signals abandoned maintenance | Resolve all alerts before v1.0.0 tag; configure Dependabot on new repo immediately |
| CI badge pointing to old repo | Confusing, looks unmaintained | Update README CI badge URL to new repo in rebrand phase |
| Inconsistent version strings across files (package.json, debian/changelog, about page) | Launch QA failure; users report wrong version | Use release checklist to verify all 3 version files before tagging |
| README install section references old image name | Users can't install; first impression is broken | Test Docker Compose from a clean environment before launch post |
| Leaving "generated with Claude" commit messages in git history | Community sees AI-generation signals in commit log | Review recent commit messages; if AI session artifacts are in history, document the AI-assisted process proactively rather than leaving it ambiguous |

---

## UX Pitfalls

User experience mistakes specific to a community launch.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| README shows features but no "why use this over X" section | Users don't understand differentiation from other seedbox tools | Add explicit comparison/differentiation section addressing competing tools |
| Install instructions require more than 3 commands | Friction causes abandonment in first 60 seconds | Test "zero to running" path and count commands; reduce if possible |
| No demo screenshots in README | Community posts with screenshots get 3x more engagement on r/selfhosted | Add at least 2 screenshots (dashboard, settings) to README |
| GitHub Discussions not enabled | No place for users to ask questions without opening issues | Enable Discussions in repo settings before launch |
| No "getting help" section in README | Users file issues for config questions | Add Discussions link and a brief troubleshooting section to README |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces before community launch.

- [ ] **Attribution story:** README has origin story with live link to upstream — verify it's in the first section, not a footnote
- [ ] **Rebrand sweep:** `grep -r "seedsync"` on entire codebase returns only intentional legacy references — verify no missed rename in CI, docker-compose, or docs
- [ ] **GHCR image:** `docker pull ghcr.io/thejuran/seedsyncarr:latest` succeeds from a clean machine — verify before any announcement
- [ ] **CI badge:** README CI badge links to new repo, shows passing — verify badge URL is updated
- [ ] **Dependabot:** New repo has zero open security alerts — verify before v1.0.0 tag
- [ ] **Version consistency:** package.json, debian/changelog, and E2E about-page spec all show same version — verify with release checklist
- [ ] **Install test:** Docker Compose instructions tested end-to-end from a fresh environment — verify with `docker compose up` on a machine with no cached images
- [ ] **mkdocs live:** `mkdocs gh-deploy` has been run and the docs site is reachable — verify URL before submitting to any wiki
- [ ] **Star gate:** Awesomarr submission not opened until repo has 50+ stars — track and gate this explicitly
- [ ] **Age gate:** awesome-selfhosted submission not opened until 4 months post-v1.0.0 — calendar this

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Fork attribution backlash | MEDIUM | Add prominent attribution to README within hours; respond to community post directly and transparently; do not get defensive |
| Rejected from Awesomarr (too few stars) | LOW | Close PR gracefully, thank maintainer, re-submit once 50-star gate is met; don't argue |
| Rejected from awesome-selfhosted (too new) | LOW | Close PR, calendar 4-month resubmission date |
| Negative r/selfhosted reception | HIGH | Respond to each criticism specifically; push a fix within 24 hours if technical; update README; follow up with "here's what changed" comment |
| CI failures discovered post-launch | MEDIUM | Push fix immediately, post a "v1.0.1 patch" comment in the announcement thread; speed of response mitigates the damage |
| Wrong GHCR image name in README | LOW | Push correction immediately; post errata comment in announcement thread |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Fork attribution looks like theft | Phase 1: Rebrand & Rename | README reviewed for prominent origin story before merge |
| AI code signals | Phase 2: Harden for Scrutiny | AI-artifact audit checklist completed; no comments explaining obvious code |
| Premature list submission (too few stars) | Phase 4: Community Launch | Star-count gate documented in launch plan; submission deferred |
| Premature list submission (too new) | Phase 4: Community Launch | Calendar reminder for 4-month mark set at launch |
| New name, same problems | Phase 2: Harden for Scrutiny | CI green, zero lint errors, zero Dependabot alerts at phase close |
| GHCR image rename confusion | Phase 1: Rebrand & Rename | `docker pull ghcr.io/thejuran/seedsyncarr:latest` tested from clean env |
| Wrong announcement channel/timing | Phase 4: Community Launch | Launch post drafts written per-community with stagger plan |
| Servarr wiki listing rejected | Phase 3: Present | mkdocs site live and *arr integration page complete before wiki PR |

---

## Sources

- Awesomarr CONTRIBUTING.md (50-star gate, alphabetical ordering): https://github.com/Ravencentric/awesome-arr
- awesome-selfhosted CONTRIBUTING.md (4-month age requirement, maintenance standards): https://github.com/awesome-selfhosted/awesome-selfhosted-data/blob/master/CONTRIBUTING.md
- Servarr Wiki "Useful Tools" (companion app listing, no official criteria): https://wiki.servarr.com/useful-tools
- Hacker News: "How not to fork an open source project" (attribution ethics, community reactions): https://news.ycombinator.com/item?id=47378448
- InfoQ: "AI Vibe Coding Threatens Open Source as Maintainers Face Crisis" (maintainer rejection patterns, AI slop backlash): https://www.infoq.com/news/2026/02/ai-floods-close-projects/
- CodeRabbit: "AI vs human code gen report" (1.7x more major issues in AI code): https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report
- Reddit self-promotion rules and anti-spam guidelines: https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam
- Open Source Guides (community launch timing and engagement): https://opensource.guide/
- Pangram Labs: AI code detector patterns (comment density, over-engineering signals): https://www.pangram.com/blog/ai-code-detector

---
*Pitfalls research for: SeedSyncarr rebrand, fork-to-standalone transition, curated list submissions, *arr community launch*
*Researched: 2026-04-08*
*Confidence: MEDIUM-HIGH — list criteria from official sources; community dynamics from multiple corroborating sources; AI-code scrutiny from peer-reviewed research and practitioner reports*
