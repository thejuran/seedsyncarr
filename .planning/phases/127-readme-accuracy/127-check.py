#!/usr/bin/env python3
"""Phase 127 (README Accuracy) mechanical checks. Standard library only.

Usage:
    python3 .planning/phases/127-readme-accuracy/127-check.py <group>

Groups:
    structure  DOC-01, DOC-04  (D-09 .. D-15)
    claims     DOC-02, DOC-03  (D-01 .. D-07)
    security   D-08            (SECURITY.md: exactly two lines changed)
    scope      only README.md and SECURITY.md changed outside .planning/
    all        every group above

Exit code 0 when the selected groups pass, 1 otherwise. Each failure prints one
line starting with FAIL and the decision or requirement it belongs to.

These checks cover what can be decided mechanically. They do not replace the
read-through of the prose required by D-04 and the revised D-03.

Environment overrides (for trying a draft outside the repository):
    README_PATH, SECURITY_PATH  alternative files to check
    BASE_REF                    alternative base commit for the scope group
"""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# Commit whose README.md and SECURITY.md are the pre-phase baseline
# (HEAD of main when the phase was planned).
PIN = "091f51f23b88905d3067ffdbd9427754138d94db"

GUIDES = [
    "docs/GETTING-STARTED.md",
    "docs/CONFIGURATION.md",
    "SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/DEVELOPMENT.md",
    "docs/TESTING.md",
]

# First-run defaults the README states (D-07). If one of these lines is no
# longer in the code, the default changed and the README wording must be
# rechecked before this check is updated.
CODE_DEFAULTS = [
    r'config\.general\.webhook_secret = ""',
    r'config\.general\.api_token = ""',
    r"config\.general\.webhook_require_secret = False\b",
    r"config\.autodelete\.enabled = False\b",
    r"config\.autodelete\.dry_run = False\b",
    r"config\.autodelete\.delay_seconds = 60\b",
    r"config\.encryption\.enabled = False\b",
]

FORBIDDEN_README = [
    (r"never delet", "D-01 absolute never-delete wording"),
    (r"security by default", "D-05 old Features bullet"),
    (r"maximum transfer speed", "D-04 unconditional superlative"),
    (r"safely reclaim", "D-04 unconditional claim"),
    (r"safe auto-delete", "D-01/D-02 unconditional claim"),
    (r"hmac-verified", "D-03 Sonarr/Radarr webhooks are not verified by default and cannot be signed"),
    (r"thejuran\.github\.io", "D-11 website referenced as a docs source"),
    (r"\[!(warning|note|caution|important|tip)\]", "D-10 admonition syntax"),
]

failures = []


def fail(tag, message):
    failures.append("FAIL [{}] {}".format(tag, message))


def need(cond, tag, message):
    if not cond:
        fail(tag, message)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def git(*args):
    return subprocess.run(
        ["git", "-C", ROOT] + list(args), capture_output=True, text=True, check=False
    )


def split_lines(text):
    """Return [(line, in_fence)] so headings and links inside code fences are ignored."""
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            out.append((line, True))
            in_fence = not in_fence
            continue
        out.append((line, in_fence))
    return out


def prose(text):
    """Text with fenced code blocks removed."""
    return "\n".join(line for line, fenced in split_lines(text) if not fenced)


def h2_sections(text):
    """Return (ordered H2 titles, {title: body including fenced code}, preamble)."""
    order, bodies, preamble = [], {}, []
    current = None
    for line, fenced in split_lines(text):
        match = None if fenced else re.match(r"^## +(.+?)\s*$", line)
        if match:
            current = match.group(1)
            order.append(current)
            bodies[current] = []
            continue
        (bodies[current] if current else preamble).append(line)
    return order, {k: "\n".join(v) for k, v in bodies.items()}, "\n".join(preamble)


def slug(heading):
    """GitHub heading slug: lowercase, punctuation dropped, spaces to hyphens."""
    heading = heading.strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading)
    return heading.replace(" ", "-")


def blockquotes(text):
    """Contiguous '>' blocks outside code fences, each as one string."""
    blocks, current = [], []
    for line, fenced in split_lines(text):
        if not fenced and line.startswith(">"):
            current.append(line)
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def flat(text):
    """Collapse wrapped prose (and blockquote markers) to single spaces."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^> ?", "", text))


def check_links(readme):
    text = prose(readme)
    anchors = {slug(m) for m in re.findall(r"(?m)^#{1,6}\s+(.+)$", text)}
    links = re.findall(r"\]\(([^)\s]+)\)", text)
    links += re.findall(r'(?:src|srcset)="([^"]+)"', text)
    for link in links:
        if re.match(r"(https?:|mailto:)", link):
            continue
        if link.startswith("#"):
            need(link[1:] in anchors, "D-15", "same-file anchor does not resolve: " + link)
            continue
        target = link.split("#")[0]
        need(os.path.exists(os.path.join(ROOT, target)), "D-15", "relative link does not resolve: " + link)


def group_structure(readme):
    order, sec, _ = h2_sections(readme)
    required = [
        "About This Fork", "Quick Start", "Documentation", "Features", "How It Works",
        "Installation", "Configuration", "Usage Examples", "Contributing", "Security", "License",
    ]
    missing = [name for name in required if name not in order]
    for name in missing:
        fail("DOC-01", "README is missing the '## {}' section".format(name))
    for name in set(order):
        need(order.count(name) == 1, "DOC-01", "'## {}' appears more than once".format(name))
    if missing:
        return

    pos = {name: order.index(name) for name in order}
    need(pos["Documentation"] == pos["Quick Start"] + 1, "D-12",
         "'## Documentation' must be the section immediately after '## Quick Start'")
    need(pos["Documentation"] < pos["Features"], "D-12", "'## Documentation' must come before '## Features'")
    for later in ("Contributing", "Security", "License"):
        need(pos["Usage Examples"] < pos[later], "D-14",
             "'## Usage Examples' must come before '## {}'".format(later))

    doc = sec["Documentation"]
    offsets = []
    for guide in GUIDES:
        at = doc.find("](" + guide)
        need(at >= 0, "DOC-01", "Documentation section does not link " + guide)
        offsets.append(at)
    using = doc.lower().find("using seedsyncarr")
    internals = doc.lower().find("internals")
    need(using >= 0, "D-13", "Documentation section lacks the 'Using SeedSyncarr' group label")
    need(internals >= 0, "D-13", "Documentation section lacks the 'Contributing / internals' group label")
    if using >= 0 and internals >= 0 and min(offsets) >= 0:
        need(using < min(offsets[:3]) and max(offsets[:3]) < internals < min(offsets[3:]), "D-13",
             "guides are not grouped: Getting Started, Configuration, Security under 'Using SeedSyncarr'; "
             "Architecture, Development, Testing under 'Contributing / internals'")
    for guide, at in zip(GUIDES, offsets):
        if at < 0:
            continue
        line = doc[doc.rfind("\n", 0, at) + 1: (doc.find("\n", at) if doc.find("\n", at) >= 0 else len(doc))]
        after = line[line.find(")", line.find("](" + guide)) + 1:]
        need(len(re.sub(r"[\W_]+", "", after)) >= 12, "D-13",
             "no one-line blurb after the {} link".format(guide))

    inst = sec["Installation"]
    for guide in GUIDES[:2]:
        need("](" + guide in inst, "D-11", "Installation section does not link " + guide)

    quick = sec["Quick Start"]
    need('- "8800:8800"' in quick, "D-09", "compose example must keep the \"8800:8800\" port mapping")
    need("-p 8800:8800" in inst, "D-09", "docker run example must keep -p 8800:8800")
    need(not re.search(r"\d+\.\d+\.\d+\.\d+:8800", readme), "D-09", "examples must not bind 8800 to a host IP")

    notes = [flat(b) for b in blockquotes(quick)]
    need(any(n.startswith("**Set `PUID`/`PGID`") for n in notes), "D-10",
         "the existing PUID/PGID note must stay in Quick Start")
    exposure = [n for n in notes if re.match(r"\*\*[^*]*network exposure[^*]*\*\*", n, re.I)]
    need(len(exposure) == 1, "D-10",
         "Quick Start needs exactly one blockquote whose bold lead contains 'Network exposure'")
    if len(exposure) == 1:
        note = exposure[0]
        need(quick.find("```yaml") < quick.lower().find("network exposure"), "D-10",
             "the Network exposure note must sit under the compose example")
        need(re.search(r"all (host )?interfaces", note, re.I), "DOC-04", "note must say port 8800 is published on all host interfaces")
        need("8800" in note, "DOC-04", "note must name port 8800")
        need(re.search(r"reverse proxy", note, re.I), "DOC-04", "note must name an authenticating reverse proxy")
        need(re.search(r"authenticat", note, re.I), "DOC-04", "note must say the reverse proxy authenticates")
        need(re.search(r"restrict", note, re.I), "DOC-04", "note must say to restrict network access")
        need("`api_token`" in note, "DOC-04", "note must name `api_token`")
        need(re.search(r"\bUI\b", note), "DOC-04", "note must say the API token does not protect the UI")
        need(re.search(r"\b(contains|carries|includes)\b", note, re.I), "DOC-04", "note must say the UI contains the token")
        need("(#security)" in note, "D-10", "note must link to the Security section (#security)")

    usage = sec["Usage Examples"]
    for title in (
        "**Sync only TV shows and movies using AutoQueue patterns**",
        "**Confirm a Sonarr import before cleaning up**",
        "**Automatically clean up after import**",
    ):
        need(title in usage, "D-14", "Usage Examples lost its example: " + title)
    need("/server/webhook/sonarr" in usage and "/server/webhook/radarr" in usage, "D-14",
         "Usage Examples must keep both webhook endpoint paths")

    check_links(readme)


def group_claims(readme):
    order, sec, preamble = h2_sections(readme)
    lowered = readme.lower()
    for pattern, why in FORBIDDEN_README:
        for match in re.finditer(pattern, lowered):
            line_no = lowered.count("\n", 0, match.start()) + 1
            fail("DOC-03", "README.md:{} still contains '{}' ({})".format(line_no, match.group(0), why))

    taglines = [flat(b) for b in blockquotes(preamble)]
    need(len(taglines) == 1, "D-01", "expected exactly one tagline blockquote above the first section")
    if len(taglines) == 1:
        tag = taglines[0]
        need("Sonarr" in tag, "D-01", "tagline must name Sonarr")
        need(re.search(r"confirm", tag, re.I) and re.search(r"import", tag, re.I), "D-01",
             "tagline must condition auto-delete on the confirmed import")
        need(not re.search(r"hmac|never|always|guarantee", tag, re.I), "D-01", "tagline must not make an absolute or HMAC claim")

    for name in ("About This Fork", "Features", "How It Works", "Security", "Usage Examples"):
        if name not in sec:
            fail("DOC-03", "README is missing the '## {}' section".format(name))
            return

    how = flat(sec["How It Works"])
    for pattern, what in (
        (r"webhook", "the inbound import webhook"),
        (r"post-import pruning", "Post-Import Pruning by name"),
        (r"off by default", "that pruning is off by default"),
        (r"delay", "the safety delay"),
        (r"\b60\b", "the 60 second default"),
        (r"dry[- ]run", "the dry-run option"),
        (r"remote", "that the remote copy is not deleted by pruning"),
    ):
        need(re.search(pattern, how, re.I), "D-02", "How It Works must state " + what)
    need("(#security)" in how, "D-03", "How It Works must link to the Security section (#security)")

    about = flat(sec["About This Fork"])
    need("(#how-it-works)" in about, "D-02", "About This Fork must point to How It Works (#how-it-works)")
    need("ipsingh06/seedsync" in about, "D-02", "About This Fork must keep the upstream SeedSync link")

    bullets = [flat(b) for b in re.split(r"(?m)^(?=- )", sec["Features"]) if b.startswith("- ")]
    arr = [b for b in bullets if b.startswith("- **Sonarr and Radarr integration**")]
    need(len(arr) == 1, "D-02", "Features must keep one '- **Sonarr and Radarr integration**' bullet")
    if len(arr) == 1:
        need("(#how-it-works)" in arr[0], "D-02", "the Sonarr and Radarr integration bullet must point to How It Works")
        need(not re.search(r"removes the local copy", arr[0], re.I), "D-02",
             "the Sonarr and Radarr integration bullet must not repeat the cleanup promise")
        need(len(arr[0]) <= 220, "D-02", "the Sonarr and Radarr integration bullet must be short (220 characters or fewer)")

    controls = [b for b in bullets if b.startswith("- **Security controls**")]
    need(len(controls) == 1, "D-05", "Features must have one '- **Security controls**' bullet")
    if len(controls) == 1:
        bullet = controls[0]
        for pattern, what in (
            (r"\bCSP\b", "CSP headers"),
            (r"rate[- ]limit", "rate limiting"),
            (r"webhook", "the rate-limited webhook endpoints by name"),
            (r"status", "the rate-limited status endpoint by name"),
            (r"log", "log-injection sanitizing"),
            (r"test(ing)? (a|an|the) .{0,24}connection|test-connection|connection test", "that the IP guard applies when testing a connection"),
        ):
            need(re.search(pattern, bullet, re.I), "D-05", "Security controls bullet must name " + what)
        need("(#security)" in bullet, "D-05", "Security controls bullet must link to the Security section (#security)")
        for pattern in (r"fernet", r"encrypt", r"hmac", r"bearer", r"api_token", r"by default"):
            need(not re.search(pattern, bullet, re.I), "D-05",
                 "Security controls bullet lists only always-on controls; remove '{}'".format(pattern))

    security_raw = sec["Security"]
    security = flat(security_raw)
    need(not any(line.lstrip().startswith("|") for line in security_raw.split("\n")), "D-06",
         "Security section must be a list, not a table")
    need(len(re.findall(r"(?m)^- ", security_raw)) >= 4, "D-06", "Security section needs a list of at least four off-until-configured items")
    need(re.search(r"`api_token`.{0,160}(empty|unset|not set|off)|(empty|unset|not set|off).{0,160}`api_token`", security, re.I),
         "DOC-02", "Security must say API authentication is off when `api_token` is empty")
    need(re.search(r"`webhook_secret`.{0,160}(empty|unset|not set|off)|(empty|unset|not set|off).{0,160}`webhook_secret`", security, re.I),
         "DOC-02", "Security must say webhook verification is off when `webhook_secret` is empty")
    need(re.search(r"`webhook_require_secret`.{0,120}`False`", security), "DOC-02",
         "Security must say `webhook_require_secret` defaults to `False`")
    need("`[Encryption] enabled = True`" in security, "DOC-02", "Security must give `[Encryption] enabled = True` as the way to enable encryption")
    need(re.search(r"plaintext|plain text", security, re.I), "DOC-02", "Security must say stored secrets are plaintext by default")
    need("settings.cfg" in security, "D-06", "Security must say these are set in settings.cfg")
    need("](SECURITY.md)" in security, "D-06", "Security must link SECURITY.md")
    need(re.search(r"report", security, re.I), "D-06", "Security must keep the vulnerability-reporting pointer")
    need(re.search(r"can reach", security, re.I), "D-03", "Security must say anything that can reach the endpoint can report an import")
    need(re.search(r"\bsigns?\b|\bsigned\b|\bsigning\b", security, re.I), "D-03", "Security must say verification needs a sender that signs each request")
    need(re.search(r"Sonarr", security) and re.search(r"Radarr", security), "D-03", "Security must say Sonarr and Radarr do not sign")
    need(re.search(r"reject", security, re.I), "D-03", "Security must say a secret makes SeedSyncarr reject Sonarr/Radarr webhooks")
    need("8800" in security, "D-03", "Security must name restricting who can reach port 8800 as the practical protection")

    usage = flat(sec["Usage Examples"])
    need("(#security)" in usage, "D-03", "Usage Examples webhook example must point to the Security section (#security)")
    need(re.search(r"dry[- ]run", usage, re.I) and re.search(r"\b60\b", usage), "D-14",
         "Usage Examples must keep the 60 second default and the dry-run advice")

    for sentence in re.split(r"(?<=[.!?])\s+", flat(prose(readme))):
        if not re.search(r"webhook_(require_)?secret", sentence):
            continue
        if re.search(r"\b(recommend(ed|s)?|should (set|enable|configure)|be sure to|make sure to|we advise)\b", sentence, re.I) \
                and not re.search(r"\b(not|don't|never)\b", sentence, re.I):
            fail("D-03", "README recommends a webhook secret setting: " + sentence[:120])

    code = read(os.path.join(ROOT, "src", "python", "seedsyncarr.py"))
    for pattern in CODE_DEFAULTS:
        need(re.search(pattern, code), "D-07",
             "default no longer found in src/python/seedsyncarr.py: {} (recheck README wording)".format(pattern))


def group_security(security_text):
    need("several protections are active by default" not in security_text, "D-08",
         "SECURITY.md still says 'several protections are active by default'")
    base = git("show", PIN + ":SECURITY.md")
    if base.returncode != 0:
        fail("D-08", "cannot read baseline SECURITY.md from commit " + PIN[:8])
        return
    old = base.stdout.split("\n")
    new = security_text.split("\n")
    if len(old) != len(new):
        fail("D-08", "SECURITY.md line count changed ({} -> {}); each of the two edits must stay on its own single line".format(len(old), len(new)))
        return
    changed = [i + 1 for i, (a, b) in enumerate(zip(old, new)) if a != b]
    need(changed == [40, 43], "D-08",
         "SECURITY.md must differ from the baseline on lines 40 and 43 only; differs on {}".format(changed))
    if changed != [40, 43]:
        return

    intro, bullet = new[39], new[42]
    need(intro.startswith("SeedSyncarr is designed to be self-hosted on a private network"), "D-08",
         "line 40 must keep the 'self-hosted on a private network' opening")
    need(intro.rstrip().endswith(":"), "D-08", "line 40 must still end with a colon introducing the list")
    need(re.search(r"always[- ]on", intro, re.I), "D-08", "line 40 must say which protections are always on")
    need(re.search(r"off (until|unless)|opt-in", intro, re.I), "D-08", "line 40 must say which protections are off until configured")
    need(not re.search(r"by default", intro, re.I), "D-08", "line 40 must not claim protections are active by default")

    need(bullet.startswith("- **"), "D-08", "line 43 must stay a bold-titled list bullet")
    need(not bullet.startswith("- **HMAC-verified import webhooks**"), "D-08", "line 43 must not keep the 'HMAC-verified import webhooks' title")
    need("Sonarr" in bullet and "Radarr" in bullet, "D-08", "line 43 must name Sonarr and Radarr")
    need(re.search(r"(do not|don't|cannot|can't|never) (sign|compute)", bullet, re.I), "D-08",
         "line 43 must say Sonarr/Radarr do not sign requests")
    need("`webhook_secret`" in bullet and "`webhook_require_secret" in bullet, "D-08",
         "line 43 must name `webhook_secret` and `webhook_require_secret`")
    need("401" in bullet and "503" in bullet, "D-08", "line 43 must keep the 401 and 503 rejection facts")
    need(re.search(r"reject", bullet, re.I), "D-08", "line 43 must say their webhooks would be rejected")
    need("X-Webhook-Signature" in bullet, "D-08", "line 43 must name the X-Webhook-Signature header")
    need(not re.search(r"\benable `webhook_require_secret", bullet, re.I), "D-08",
         "line 43 must not tell the reader to enable webhook_require_secret")
    need(re.search(r"\b8800\b|network", bullet, re.I), "D-08", "line 43 must name network restriction as the practical protection")


def group_scope():
    base = os.environ.get("BASE_REF")
    if not base:
        head = git("rev-parse", "HEAD").stdout.strip()
        merge_base = git("merge-base", "HEAD", "main").stdout.strip()
        base = merge_base if merge_base and merge_base != head else PIN
    diff = git("diff", "--name-only", base, "--", ".", ":(exclude).planning")
    untracked = git("ls-files", "--others", "--exclude-standard", "--", ".", ":(exclude).planning")
    if diff.returncode != 0 or untracked.returncode != 0:
        fail("SCOPE", "git could not compute the changed-file list against " + base[:8])
        return
    changed = sorted(set(filter(None, (diff.stdout + "\n" + untracked.stdout).split("\n"))))
    extra = [name for name in changed if name not in ("README.md", "SECURITY.md")]
    need(not extra, "SCOPE", "files outside README.md, SECURITY.md and .planning/ changed: {}".format(extra))
    for name in ("README.md", "SECURITY.md"):
        need(name in changed, "SCOPE", "{} is unchanged against {}".format(name, base[:8]))


def main():
    group = sys.argv[1] if len(sys.argv) == 2 else ""
    if group not in ("structure", "claims", "security", "scope", "all"):
        print(__doc__)
        return 2
    readme = read(os.environ.get("README_PATH") or os.path.join(ROOT, "README.md"))
    security = read(os.environ.get("SECURITY_PATH") or os.path.join(ROOT, "SECURITY.md"))
    if group in ("structure", "all"):
        group_structure(readme)
    if group in ("claims", "all"):
        group_claims(readme)
    if group in ("security", "all"):
        group_security(security)
    if group in ("scope", "all"):
        group_scope()
    for line in failures:
        print(line)
    print("{}: {}".format(group, "{} failure(s)".format(len(failures)) if failures else "OK"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
