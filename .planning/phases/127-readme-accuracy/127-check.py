#!/usr/bin/env python3
"""Phase 127 (README Accuracy) mechanical checks. Standard library only.

Usage:
    python3 .planning/phases/127-readme-accuracy/127-check.py <group>

Groups:
    structure  DOC-01, DOC-04  (D-09 .. D-15)
    claims     DOC-02, DOC-03  (D-01 .. D-07)
    security   D-08            (SECURITY.md: only the two approved spots changed)
    scope      only README.md and SECURITY.md changed outside .planning/
    selftest   fixtures proving the detectors below reject known-bad text
    all        every group above

Exit code 0 when the selected groups pass, 1 otherwise. Each failure prints one
line starting with FAIL and the decision or requirement it belongs to.

WHAT THESE CHECKS ARE. Most checks here are PRESENCE checks: they confirm that
a required term or phrase appears in the right section. Presence of a keyword
does not prove the sentence around it is true. A small set of CONTRADICTION
detectors (see contradiction_problems) rejects specific false statements that
were shown to slip past presence checks, and the selftest group pins those
cases. Neither replaces the mandatory read-through of the prose: every DOC-02
and DOC-04 assertion, the signing conditions and the local-only cleanup
statement must be confirmed by reading (127-VALIDATION.md, Manual-Only
Verifications; claims ledger in the SUMMARY).

Baseline. PIN below is the one baseline for both the security and the scope
group: the commit whose README.md and SECURITY.md are the pre-phase versions.

Environment overrides:
    README_PATH, SECURITY_PATH  alternative files to check (for trying a draft
                                outside the repository; relative links are still
                                resolved against the repository root)
    BASE_REF                    alternative base commit for the scope group.
                                Needed only when commits unrelated to this phase
                                sit between PIN and the checked tree, for example
                                when re-running after the phase PR merged and
                                later work landed on main: set BASE_REF to the
                                parent of the phase's first commit.
"""
import difflib
import html.parser
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

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
    (r"then deletes", "D-02/D-04 deletion is attempted after the delay, subject to safeguards; it is not automatic"),
    (r"thejuran\.github\.io", "D-11 website referenced as a docs source"),
    (r"\[!(warning|note|caution|important|tip)\]", "D-10 admonition syntax"),
]

# The two SECURITY.md baseline lines the owner approved for replacement (D-08).
OLD_INTRO = ("SeedSyncarr is designed to be self-hosted on a private network, "
             "and several protections are active by default:")
OLD_BULLET_PREFIX = "- **HMAC-verified import webhooks**"
# Third approved spot (owner ruling 2026-11-18 on code review WR-01): the Bearer
# auth bullet overclaimed what `api_token` covers; it may be replaced in place.
OLD_BEARER_PREFIX = "- **Bearer auth**"

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


def anchors_of(text):
    """Anchors a Markdown file exposes: heading slugs (with GitHub's -1, -2
    suffixes for repeated headings) and explicit HTML name/id attributes."""
    found, seen = set(), {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", prose(text)):
        base = slug(heading)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else "{}-{}".format(base, count))
    found.update(re.findall(r'<a\s+(?:name|id)="([^"]+)"', text))
    return found


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
    return re.sub(r"\s+", " ", re.sub(r"(?m)^> ?", "", text)).strip()


def blocks_of(text):
    """List items and paragraphs outside code fences, each flattened to one line."""
    out = []
    for item in re.split(r"(?m)^\s*(?:[-*]|\d+\.)\s+", prose(text)):
        for para in re.split(r"\n\s*\n", item):
            if flat(para):
                out.append(flat(para))
    return out


def units(text):
    """Sentence-sized units (split on . ! ? ; inside each list item or paragraph)."""
    out = []
    for block in blocks_of(text):
        out.extend(s.strip() for s in re.split(r"(?<=[.!?;])\s+", block) if s.strip())
    return out


# --------------------------------------------------------------------------
# Detectors. Pure functions returning a list of problem strings, so the
# selftest group can exercise them against fixtures.
# --------------------------------------------------------------------------

INLINE_LINK = re.compile(r"""\]\(\s*<?([^)\s>]+)>?(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)""")
REF_DEF = re.compile(r"""(?m)^ {0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+["'(].*)?\s*$""")
REF_USE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")


class _AttributeLinks(html.parser.HTMLParser):
    """Collect src, srcset and href values from HTML tags, whatever the quoting
    (double, single or none)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if not value:
                continue
            if name in ("src", "href"):
                self.found.append(value.strip())
            elif name == "srcset":
                self.found += [part.strip().split()[0] for part in value.split(",") if part.strip()]


def link_problems(text, root):
    """Problems with relative links, images and anchors in a Markdown text.

    Checked: inline links and images (with or without a title), reference
    links ([text][label], [label][]) and their definitions, HTML src / srcset /
    href attributes in any quoting (parsed with html.parser), same-file
    anchors, and fragments on linked .md files. An inline link ('](') that
    cannot be parsed is reported as unsupported instead of being skipped.

    Not checked: any other way of writing a link (autolinks such as <path>,
    bare paths in prose, HTML attributes other than src / srcset / href).
    The README must keep to the checked forms.
    """
    problems = []
    body = prose(text)
    own_anchors = anchors_of(text)

    targets = [m.group(1) for m in INLINE_LINK.finditer(body)]
    unparsed = body.count("](") - len(targets)
    if unparsed:
        problems.append("{} inline link(s) use syntax this checker does not parse".format(unparsed))

    definitions = {label.strip().lower(): target for label, target in REF_DEF.findall(body)}
    targets += list(definitions.values())
    for shown, label in REF_USE.findall(body):
        key = (label or shown).strip().lower()
        if key not in definitions:
            problems.append("reference link has no definition: [{}]".format(label or shown))

    attributes = _AttributeLinks()
    attributes.feed(body)
    attributes.close()
    targets += attributes.found

    for link in targets:
        if re.match(r"(?i)(https?:|mailto:)", link):
            continue
        link = urllib.parse.unquote(link)
        path, _, fragment = link.partition("#")
        if not path:
            if fragment not in own_anchors:
                problems.append("same-file anchor does not resolve: #" + fragment)
            continue
        full = os.path.join(root, path)
        if not os.path.exists(full):
            problems.append("relative link does not resolve: " + link)
            continue
        if fragment:
            if not path.lower().endswith(".md") or os.path.isdir(full):
                problems.append("fragment on a non-Markdown target cannot be checked: " + link)
            elif fragment not in anchors_of(read(full)):
                problems.append("fragment does not resolve in {}: #{}".format(path, fragment))
    return problems


SECRET = r"webhook_(?:require_)?secret"
ADVICE = re.compile(
    r"recommend\w*|advis\w*|suggest\w*|\bconsider\b"
    r"|\bconsidering (?:setting|enabling|using|adding|configuring|turning)\b"
    r"|encourag\w*|best[- ]practices?"
    r"|\bshould\b(?!\s+not\b)(?!n't)|\bought to\b|\bbe sure to\b|\bmake sure to\b"
    r"|\bfor (?:better|extra|added|more|stronger|improved) (?:security|protection)\b",
    re.I,
)
NEGATED_JUST_BEFORE = re.compile(r"(?:\bnot|n't|\bnever|\bno)\s+(?:\w+\s+)?$", re.I)
IMPERATIVE = re.compile(
    r"(?:^|[;:,(—–]\s*|\b(?:then|and|or|please|also|always|just|simply)\s+)"
    r"(?:set|enable|configure|turn on|switch on|use|add|define)\s+(?:\w+\s+){0,3}`?" + SECRET,
    re.I,
)


def recommend_problems(text):
    """Sentences that advise or instruct the reader to turn on webhook_secret
    or webhook_require_secret (revised D-03 forbids this for Sonarr/Radarr).

    A negation excuses an advisory word only when it sits immediately before
    that word ("do not recommend"); a "not" elsewhere in the sentence does not.
    "consider" counts only as advice ("consider setting", "considering
    enabling"), not as description ("a call is considered unverified").
    """
    problems = []
    for sentence in units(text):
        if not re.search(SECRET, sentence):
            continue
        advised = any(
            not NEGATED_JUST_BEFORE.search(sentence[:m.start()]) for m in ADVICE.finditer(sentence)
        )
        if advised or IMPERATIVE.search(sentence):
            problems.append("recommends or instructs a webhook secret setting: " + sentence[:140])
    return problems


EMPTY = r"\b(?:empty|unset|not set|blank|no token|no secret|without a (?:token|secret))\b"
NEG = r"\b(?:off|not|no|never|disabled|skipped|without|unprotected|neither|nor|cannot|unsigned)\b|n't"
ON = r"\b(?:on|enabled|active|enforced|required|verified|protected|checked)\b"
ARR = r"(?:Sonarr|Radarr)(?:\s*(?:and|or|/|&)\s*(?:Sonarr|Radarr))?"
# Sonarr/Radarr as the grammatical subject of signing, or their webhooks
# described as signed. A sentence that merely names them next to "a sender
# that signs each request" or "the signed header" is not a claim that they sign.
ARR_SIGNS = re.compile(
    r"\b" + ARR + r"(?:\s+(?:both|each|also|always|now|can|will|natively))*\s+"
    r"(?:sign(?:s|ed)?\b|HMAC-sign|comput\w+\s+(?:an?|the)\s+(?:HMAC|signature)|adds?\s+(?:an?|the)\s+(?:HMAC|signature))"
    r"|\b" + ARR + r"\s+(?:import\s+)?(?:webhooks?|requests?|calls?|payloads?)\s+(?:are|is|come|arrive)\s+(?:\w+\s+)?signed\b"
    r"|\bsigned by (?:Sonarr|Radarr)\b",
    re.I,
)
# The token said to protect the UI (either word order). Naming the UI, the
# token and an authenticating reverse proxy in one sentence is not that claim.
TOKEN_PROTECTS_UI = re.compile(
    r"token\b[^.;]*?\b(?:protect|secur|authenticat|gate)\w*[^.;]*?\bUI\b"
    r"|\bUI\b[^.;]*?\b(?:is|are|stays?|remains?)\s+(?:\w+\s+)?(?:protected|secured|gated|authenticated)\b[^.;]*?token",
    re.I,
)
ENCRYPTION_OFF = r"\bopt-in\b|\bplaintext\b|\bplain text\b|\bunencrypted\b"
REMOTE_KEPT = r"\buntouched\b|\bleft\b|\bkept\b|\bstays?\b|\bleav(?:es?|ing)\b|\balone\b"


def contradiction_problems(text):
    """Specific false statements that presence checks let through.

    Each rule looks at one sentence-sized unit: the topic is named, a positive
    assertion is made, and no negation is present. This is a narrow net for
    known contradictions, not a proof that the remaining prose is true.
    """
    problems = []
    for unit in units(text):
        bare = re.sub(EMPTY, " ", unit, flags=re.I)
        negated = re.search(NEG, bare, re.I)
        positive = re.search(ON, bare, re.I)

        def flag(what):
            problems.append("{}: {}".format(what, unit[:140]))

        if "api_token" in unit and re.search(EMPTY, unit, re.I) and positive and not negated:
            flag("says API authentication is on while `api_token` is empty")
        if re.search(r"webhook_secret", unit) and re.search(EMPTY, unit, re.I) and positive and not negated:
            flag("says webhook verification is on while `webhook_secret` is empty")
        if re.search(r"encrypt", unit, re.I) and re.search(r"by default", unit, re.I) and positive and not negated \
                and not re.search(ENCRYPTION_OFF, unit, re.I):
            flag("says encryption at rest is on by default")
        if re.search(r"verif|signature", unit, re.I) and re.search(r"by default", unit, re.I) \
                and positive and not negated:
            flag("says webhook verification is on by default")
        if ARR_SIGNS.search(unit) and not negated:
            flag("says Sonarr/Radarr sign their webhook requests")
        if re.search(r"remote cop(?:y|ies)", unit, re.I) and re.search(r"delet|remov|prun|clean", unit, re.I) \
                and not re.search(NEG + "|" + REMOTE_KEPT, unit, re.I):
            flag("says pruning deletes the remote copy")
        if TOKEN_PROTECTS_UI.search(unit) and not negated:
            flag("says the API token protects the UI")
    return problems


def security_diff_problems(old, new):
    """Compare SECURITY.md line lists by content, not by line number.

    Passes only when the difference is exactly two replacements: the baseline
    intro sentence (OLD_INTRO) and the baseline webhook bullet
    (OLD_BULLET_PREFIX), plus optionally a one-line replacement of the Bearer
    auth bullet (OLD_BEARER_PREFIX, approved after code review WR-01). Every
    other baseline line must survive unchanged and
    nothing may be added elsewhere. The replacement bullet is one list item:
    a first line starting with "- ", optionally followed by continuation lines
    indented by two or more spaces (a wrapped bullet); an unindented line or a
    nested list item there is rejected. Returns (problems, intro_text,
    bullet_text, bearer_text) with wrapped lines joined by single spaces;
    bearer_text is "" when the Bearer bullet was not replaced.
    """
    bearer_text = ""
    old_b = [i for i, line in enumerate(old) if line.startswith(OLD_BEARER_PREFIX)]
    new_b = [i for i, line in enumerate(new) if line.startswith(OLD_BEARER_PREFIX)]
    if len(old_b) == 1 and len(new_b) == 1 and old[old_b[0]] != new[new_b[0]]:
        # The Bearer bullet stays one line, replaced in place; set it aside so
        # the remaining diff must be exactly the two original approved spots.
        bearer_text = new[new_b[0]]
        old = old[:old_b[0]] + old[old_b[0] + 1:]
        new = new[:new_b[0]] + new[new_b[0] + 1:]
    ops = [op for op in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
           if op[0] != "equal"]
    removed = [line for _, i1, i2, _, _ in ops for line in old[i1:i2]]
    intro_ops = [op for op in ops if old[op[1]:op[2]] == [OLD_INTRO]]
    bullet_ops = [op for op in ops
                  if op[2] - op[1] == 1 and old[op[1]].startswith(OLD_BULLET_PREFIX)]
    problems = []
    if len(ops) != 2 or len(intro_ops) != 1 or len(bullet_ops) != 1 or any(op[0] != "replace" for op in ops):
        other = [line[:60] for line in removed if line != OLD_INTRO and not line.startswith(OLD_BULLET_PREFIX)]
        problems.append(
            "SECURITY.md must differ from the baseline in exactly two places: the intro sentence of the "
            "Security posture list and the 'HMAC-verified import webhooks' bullet (plus, optionally, the "
            "'Bearer auth' bullet). Found {} changed region(s); other baseline lines removed or altered: {}".format(len(ops), other))
        return problems, "", "", ""
    intro_lines = new[intro_ops[0][3]:intro_ops[0][4]]
    bullet_lines = new[bullet_ops[0][3]:bullet_ops[0][4]]
    if any(not line.strip() for line in intro_lines + bullet_lines):
        problems.append("the two SECURITY.md replacements must not introduce blank lines")
    if not bullet_lines or not bullet_lines[0].startswith("- "):
        problems.append("the replaced webhook bullet must stay one list item starting with '- '")
    for line in bullet_lines[1:]:
        if not re.match(r"^ {2,}\S", line) or re.match(r"^\s+(?:[-*+]|\d+\.)\s", line):
            problems.append("the replaced webhook bullet must stay one list item: lines after the first must be "
                            "continuation lines indented by two or more spaces, not new text or list items")
            break
    return problems, " ".join(intro_lines), " ".join(line.strip() for line in bullet_lines), bearer_text


# --------------------------------------------------------------------------
# Groups
# --------------------------------------------------------------------------

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

    raw_notes = blockquotes(quick)
    notes = [flat(b) for b in raw_notes]
    need(any(n.startswith("**Set `PUID`/`PGID`") for n in notes), "D-10",
         "the existing PUID/PGID note must stay in Quick Start")
    need(len([b for b in blockquotes(readme) if re.match(r"> \*\*", b)]) == 2, "D-10",
         "README should have exactly two bold-lead blockquote notes (PUID/PGID and Network exposure)")
    exposure = [n for n in notes if re.match(r"\*\*[^*]*network exposure[^*]*\*\*", n, re.I)]
    need(len(exposure) == 1, "D-10",
         "Quick Start needs exactly one blockquote whose bold lead contains 'Network exposure'")
    if len(exposure) == 1:
        note = exposure[0]
        need(quick.find("```yaml") < quick.lower().find("network exposure"), "D-10",
             "the Network exposure note must sit under the compose example")
        # Presence checks: the terms must be there. Whether the sentences are
        # true is covered by contradiction_problems and the manual read-through.
        need(re.search(r"all (host )?interfaces", note, re.I), "DOC-04", "note must say port 8800 is published on all host interfaces")
        need("8800" in note, "DOC-04", "note must name port 8800")
        need(re.search(r"reverse proxy", note, re.I), "DOC-04", "note must name an authenticating reverse proxy")
        need(re.search(r"authenticat", note, re.I), "DOC-04", "note must say the reverse proxy authenticates")
        need(re.search(r"restrict", note, re.I), "DOC-04", "note must say to restrict network access")
        need("`api_token`" in note, "DOC-04", "note must name `api_token`")
        need(re.search(r"(?:\bnot|n't)\b[^.;]{0,40}\bUI\b", note), "DOC-04",
             "note must say the API token does NOT protect the UI")
        need(re.search(r"\bUI\b[^.;]{0,40}\b(contains|carries|includes)\b[^.;]{0,30}token", note, re.I), "DOC-04",
             "note must say the UI contains the token")
        need("(#security)" in note, "D-10", "note must link to the Security section (#security)")
        for problem in contradiction_problems("\n".join(raw_notes)):
            fail("DOC-04", "Quick Start note " + problem)

    usage = sec["Usage Examples"]
    for title in (
        "**Sync only TV shows and movies using AutoQueue patterns**",
        "**Confirm a Sonarr import before cleaning up**",
        "**Automatically clean up after import**",
    ):
        need(title in usage, "D-14", "Usage Examples lost its example: " + title)
    need("/server/webhook/sonarr" in usage and "/server/webhook/radarr" in usage, "D-14",
         "Usage Examples must keep both webhook endpoint paths")

    for problem in link_problems(readme, ROOT):
        fail("D-15", problem)


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

    # Presence checks from here on (see the module docstring).
    how = flat(sec["How It Works"])
    for pattern, what in (
        (r"webhook", "the inbound import webhook"),
        (r"post-import pruning", "Post-Import Pruning by name"),
        (r"off by default", "that pruning is off by default"),
        (r"delay", "the safety delay"),
        (r"\b60\b", "the 60 second default"),
        (r"dry[- ]run", "the dry-run option"),
        (r"local copy", "that pruning deletes the local copy"),
        (r"remote", "that the remote copy is not deleted by pruning"),
        (r"\bdownloaded\b", "that pruning applies only to releases SeedSyncarr downloaded"),
        (r"attempt|safeguard|subject to|deferred|defers?\b", "that deletion is attempted after the delay, subject to safeguards (not automatic)"),
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
            (r"config[- ]set|config/set", "the rate-limited POST config-set endpoint by name (not 'config endpoints')"),
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
    blocks = blocks_of(security_raw)
    empty = r"\b(empty|unset|not set|blank)\b"
    off = r"\b(off|disabled|skipped|not (required|verified|checked|enforced)|unauthenticated)\b"

    def block_with(*patterns):
        return any(all(re.search(p, b, re.I) for p in patterns) for b in blocks)

    need(not any(line.lstrip().startswith("|") for line in security_raw.split("\n")), "D-06",
         "Security section must be a list, not a table")
    need(len(re.findall(r"(?m)^- ", security_raw)) >= 4, "D-06", "Security section needs a list of at least four off-until-configured items")
    need(block_with(r"`api_token`", empty, off), "DOC-02",
         "Security must say, in one list item, that API authentication is off when `api_token` is empty")
    need(block_with(r"`api_token`", r"webhook", r"\bnot\b|n't|\bexempt"), "DOC-02",
         "Security must say `api_token` does not authenticate the webhook endpoints")
    need(block_with(r"`webhook_secret`", empty, off), "DOC-02",
         "Security must say, in one list item, that webhook verification is off when `webhook_secret` is empty")
    need(re.search(r"`webhook_require_secret`.{0,120}`False`", security), "DOC-02",
         "Security must say `webhook_require_secret` defaults to `False`")
    need("`[Encryption] enabled = True`" in security, "DOC-02", "Security must give `[Encryption] enabled = True` as the way to enable encryption")
    need(block_with(r"encrypt", r"\boff\b|\bopt-in\b|\bdisabled\b", r"plaintext|plain text"), "DOC-02",
         "Security must say, in one list item, that encryption at rest is off by default (or opt-in) and stored secrets are plaintext")
    need("settings.cfg" in security, "D-06", "Security must say these are set in settings.cfg")
    need("](SECURITY.md)" in security, "D-06", "Security must link SECURITY.md")
    need(re.search(r"report", security, re.I), "D-06", "Security must keep the vulnerability-reporting pointer")
    need(re.search(r"can reach", security, re.I), "D-03", "Security must say anything that can reach the endpoint can report an import")
    need(re.search(r"\bsigns?\b|\bsigned\b|\bsigning\b", security, re.I), "D-03", "Security must say verification needs a sender that signs each request")
    need("X-Webhook-Signature" in security, "D-03", "Security must name the `X-Webhook-Signature` header")
    need(re.search(r"Sonarr", security) and re.search(r"Radarr", security), "D-03", "Security must name Sonarr and Radarr")
    need(re.search(r"(do not|don't|does not|cannot|can't|never) sign", security, re.I), "D-03",
         "Security must say Sonarr and Radarr do not sign their webhooks")
    need(re.search(r"reject", security, re.I), "D-03", "Security must say unsigned Sonarr/Radarr webhooks are rejected once a secret is configured")
    need(re.search(r"\bdirect\b", security, re.I) and re.search(r"unsigned|not signed|(do not|don't) sign", security, re.I), "D-03",
         "Security must scope the incompatibility to direct, unsigned Sonarr/Radarr webhooks")
    need(re.search(r"`webhook_require_secret\s*=\s*true`", security, re.I)
         and re.search(r"no secret|without a secret|no `webhook_secret`|`webhook_secret` (is )?(empty|unset|not set)", security, re.I),
         "D-03", "Security must state the precise condition: `webhook_require_secret = true` with no secret rejects every call")
    need("8800" in security, "D-03", "Security must name restricting who can reach port 8800 as the practical protection")

    usage = flat(sec["Usage Examples"])
    need("(#security)" in usage, "D-03", "Usage Examples webhook example must point to the Security section (#security)")
    need(re.search(r"dry[- ]run", usage, re.I) and re.search(r"\b60\b", usage), "D-14",
         "Usage Examples must keep the 60 second default and the dry-run advice")
    need(re.search(r"attempt|safeguard|subject to|deferred|defers?\b", usage, re.I), "D-04",
         "Usage Examples cleanup example must say deletion is attempted after the delay, subject to safeguards")

    for problem in recommend_problems(readme):
        fail("D-03", "README " + problem)
    for problem in contradiction_problems(readme):
        fail("DOC-02/03", "README " + problem)

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
    problems, intro, bullet, bearer = security_diff_problems(base.stdout.split("\n"), security_text.split("\n"))
    for problem in problems:
        fail("D-08", problem)
    if not intro or not bullet:
        return

    need(intro.startswith("SeedSyncarr is designed to be self-hosted on a private network"), "D-08",
         "the intro sentence must keep the 'self-hosted on a private network' opening")
    need(intro.rstrip().endswith(":"), "D-08", "the intro sentence must still end with a colon introducing the list")
    need(re.search(r"always[- ]on", intro, re.I), "D-08", "the intro sentence must say which protections are always on")
    need(re.search(r"off (until|unless)|opt-in", intro, re.I), "D-08", "the intro sentence must say which protections are off until configured")
    need(not re.search(r"by default", intro, re.I), "D-08", "the intro sentence must not claim protections are active by default")

    need(bullet.startswith("- **"), "D-08", "the webhook bullet must stay a bold-titled list bullet")
    need(not bullet.startswith(OLD_BULLET_PREFIX), "D-08", "the webhook bullet must not keep the 'HMAC-verified import webhooks' title")
    need("Sonarr" in bullet and "Radarr" in bullet, "D-08", "the webhook bullet must name Sonarr and Radarr")
    need(re.search(r"(do not|don't|cannot|can't|never) (sign|compute)", bullet, re.I), "D-08",
         "the webhook bullet must say Sonarr/Radarr do not sign requests")
    need("`webhook_secret`" in bullet and re.search(r"`webhook_require_secret\s*=\s*true`", bullet, re.I), "D-08",
         "the webhook bullet must name `webhook_secret` and `webhook_require_secret = true`")
    need("401" in bullet and "503" in bullet, "D-08", "the webhook bullet must keep the 401 and 503 rejection facts")
    need(re.search(r"no secret|without a secret|no `webhook_secret`|`webhook_secret` (is )?(empty|unset|not set)", bullet, re.I), "D-08",
         "the webhook bullet must tie 503 to `webhook_require_secret = true` with no secret set")
    need(re.search(r"unsigned|missing or invalid|invalid", bullet, re.I), "D-08",
         "the webhook bullet must tie 401 to a configured secret meeting a missing or invalid signature")
    need(re.search(r"\bdirect\b", bullet, re.I), "D-08",
         "the webhook bullet must scope the incompatibility to direct Sonarr/Radarr webhooks")
    need(re.search(r"reject", bullet, re.I), "D-08", "the webhook bullet must say their webhooks would be rejected")
    need("X-Webhook-Signature" in bullet, "D-08", "the webhook bullet must name the X-Webhook-Signature header")
    need(re.search(r"\b8800\b|network", bullet, re.I), "D-08", "the webhook bullet must name network restriction as the practical protection")

    need(bearer, "WR-01", "the Bearer auth bullet must be corrected to name the routes `api_token` does not cover")
    for route in ("/server/status", "/server/stream", "webhook"):
        need(route in bearer, "WR-01", "the Bearer auth bullet must name {} as exempt from the token".format(route))

    changed = intro + "\n\n" + bullet + "\n\n" + bearer
    for problem in recommend_problems(changed):
        fail("D-08", "SECURITY.md " + problem)
    for problem in contradiction_problems(changed):
        fail("D-08", "SECURITY.md " + problem)


def group_scope():
    base = os.environ.get("BASE_REF") or PIN
    diff = git("diff", "--name-only", base, "--", ".", ":(exclude).planning")
    untracked = git("ls-files", "--others", "--exclude-standard", "--", ".", ":(exclude).planning")
    if diff.returncode != 0 or untracked.returncode != 0:
        fail("SCOPE", "git could not compute the changed-file list against " + base[:8])
        return
    changed = sorted(set(filter(None, (diff.stdout + "\n" + untracked.stdout).split("\n"))))
    extra = [name for name in changed if name not in ("README.md", "SECURITY.md")]
    # This list is every difference from the baseline, including untracked files
    # and commits this phase did not make. The check reports; it cannot tell who
    # made a change. Do not revert a file because it appears here (see Task 3).
    need(not extra, "SCOPE", "files outside README.md, SECURITY.md and .planning/ differ from {}: {}".format(base[:8], extra))
    for name in ("README.md", "SECURITY.md"):
        need(name in changed, "SCOPE", "{} is unchanged against {}".format(name, base[:8]))


# --------------------------------------------------------------------------
# Selftest: fixtures that must be rejected (and near-misses that must pass).
# --------------------------------------------------------------------------

def group_selftest():
    def expect(flagged, detector, text, label):
        got = bool(detector(text))
        need(got == flagged, "SELFTEST",
             "{} should {} flagged: {}".format(label, "be" if flagged else "NOT be", text[:110]))

    for text in (
        "We recommend setting `webhook_secret` if SeedSyncarr is not on a private network.",
        "Set `webhook_require_secret = true`.",
        "Enable `webhook_require_secret = true` (opt-in) to fail-closed.",
        "Consider setting `webhook_secret` for your install.",
        "We suggest a `webhook_secret`.",
        "We advise configuring `webhook_secret`.",
        "As a best practice, `webhook_secret` is configured on every install.",
        "For extra security, give `webhook_secret` a value.",
        "For better security you can fill in `webhook_secret`.",
        "You should set `webhook_secret`.",
        "To lock this down, turn on `webhook_require_secret`.",
        "Open settings.cfg, then configure `webhook_secret`.",
        "Do not leave it empty: use a `webhook_secret`.",
        "You may want to consider a `webhook_secret`.",
        "It is worth considering enabling `webhook_require_secret`.",
    ):
        expect(True, recommend_problems, text, "recommendation")
    for text in (
        "Setting `webhook_secret` or `webhook_require_secret = true` makes SeedSyncarr reject their calls.",
        "We do not recommend setting `webhook_secret` for direct Sonarr/Radarr webhooks.",
        "Setting `webhook_secret` is not recommended for direct Sonarr/Radarr webhooks.",
        "Do not set `webhook_secret` for direct Sonarr/Radarr webhooks.",
        "Verification is off unless `webhook_secret` is set.",
        "`webhook_require_secret` defaults to `False`.",
        "With `webhook_require_secret = true` and no secret, every call is rejected with 503.",
        "You should restrict who can reach port 8800.",
        "A call is considered unverified whenever `webhook_secret` is empty.",
        "With a direct Sonarr/Radarr webhook, a configured `webhook_secret` rejects every call (401) because the signed header is missing.",
    ):
        expect(False, recommend_problems, text, "factual statement")

    for text in (
        "API authentication is on when `api_token` is empty.",
        "- API authentication is enforced while `api_token` is unset",
        "Webhook verification is active when `webhook_secret` is empty.",
        "Webhook verification is enabled even if `webhook_secret` is not set.",
        "Encryption at rest is on by default.",
        "Stored secrets are encrypted by default and encryption is enabled by default.",
        "Webhook calls are verified by default.",
        "Sonarr and Radarr sign every request.",
        "Radarr signs each webhook with an HMAC.",
        "Pruning deletes the local and the remote copy.",
        "When enabled, pruning also removes remote copies.",
        "`api_token` protects the API and the UI.",
        "Setting a token secures the UI as well.",
        "Sonarr/Radarr webhooks are signed with the secret.",
        "Requests signed by Sonarr are accepted.",
        "Sonarr can sign each request once a secret is configured.",
        "The UI is protected by the token.",
    ):
        expect(True, contradiction_problems, text, "contradiction")
    for text in (
        "API authentication is off when `api_token` is empty.",
        "Webhook verification is off when `webhook_secret` is empty, so anything that can reach the endpoint can report an import.",
        "Encryption at rest is off by default; stored secrets are plaintext.",
        "Webhook calls are not verified by default.",
        "Verification needs a sender that signs each request; Sonarr and Radarr do not sign their webhooks.",
        "Pruning deletes the local copy only; the remote copy is not deleted by it.",
        "`api_token` protects the API but not the UI, and the UI contains that token.",
        "`api_token` does not authenticate the webhook endpoints.",
        # Accurate, decision-compliant sentences that earlier, broader rules rejected.
        "Verification therefore needs a sender that signs each request, and for direct Sonarr/Radarr webhooks the practical protection is restricting network access to port 8800.",
        "Only a sender that signs each request can pass verification, so for Sonarr and Radarr the practical protection is restricting who can reach port 8800.",
        "With a direct Sonarr/Radarr webhook, a configured `webhook_secret` rejects every call (401) because the signed header is missing.",
        "Sonarr and Radarr do not sign requests (they send only fixed headers or basic auth), so with a direct Sonarr/Radarr webhook either of those configurations rejects their import webhooks and pruning stops.",
        "The UI contains that token, so put an authenticating reverse proxy in front of it.",
        "Pruning removes only the local copy and leaves the remote copy alone.",
        "Encryption at rest is opt-in: by default stored secrets are plaintext, and encryption is enabled with `[Encryption] enabled = True`.",
        "A call is considered unverified whenever `webhook_secret` is empty.",
    ):
        expect(False, contradiction_problems, text, "accurate statement")

    with tempfile.TemporaryDirectory() as root:
        os.mkdir(os.path.join(root, "docs"))
        with open(os.path.join(root, "docs", "GUIDE.md"), "w", encoding="utf-8") as handle:
            handle.write("# Guide\n\n## Real Heading\n\n## Real Heading\n")
        with open(os.path.join(root, "LICENSE"), "w", encoding="utf-8") as handle:
            handle.write("x\n")

        def links(text):
            return link_problems("# Top\n\n## Section One\n\n" + text + "\n", root)

        for text in (
            '[x](docs/MISSING.md "A title")',
            "[x](docs/MISSING.md 'A title')",
            "[x][ref]\n\n[ref]: docs/MISSING.md",
            "[x][nodef]",
            "[nodef][]",
            "[x](docs/GUIDE.md#no-such-heading)",
            "[x](docs/GUIDE.md#real-heading-2)",
            "[x](LICENSE#frag)",
            "[x](#no-such-section)",
            "[x](docs/MISSING.md)",
            '<img src="doc/missing.png">',
            '<a href="docs/MISSING.md">x</a>',
            "<img src='doc/MISSING.png'>",
            "<a href=docs/MISSING.md>x</a>",
            '<source srcset="LICENSE 1x, doc/MISSING.png 2x">',
            '[x](docs/GUIDE.md "unterminated)',
            "```\ncode\n```\n[x]( docs/MISSING.md )",
        ):
            expect(True, links, text, "broken link")
        for text in (
            '[x](docs/GUIDE.md "A title")',
            "[x](docs/GUIDE.md#real-heading)",
            "[x](docs/GUIDE.md#real-heading-1)",
            "[x][ref] and [ref][]\n\n[ref]: docs/GUIDE.md",
            "[x](#section-one) and [y](#top)",
            "[x](LICENSE) and [y](https://example.com/nope) and [z](<docs/GUIDE.md>)",
            "```\n[x](docs/MISSING.md)\n```",
            "<a href=docs/GUIDE.md>x</a> and <img src='LICENSE'> and <a href='#section-one'>y</a>",
        ):
            expect(False, links, text, "valid link")

    old = ["# S", "", OLD_INTRO, "", "- **A** one", OLD_BULLET_PREFIX + " old text", "- **C** three", ""]

    def diff(new):
        return security_diff_problems(old, new)[0]

    good = list(old)
    good[2] = "SeedSyncarr is designed to be self-hosted on a private network. New:"
    good[5] = "- **Webhook signature verification (opt-in)** new text"
    need(not diff(good), "SELFTEST", "the two approved SECURITY.md replacements should be accepted")
    old_b = old[:7] + [OLD_BEARER_PREFIX + " old"] + old[7:]
    good_b = good[:7] + [OLD_BEARER_PREFIX + " new"] + good[7:]
    need(not security_diff_problems(old_b, good_b)[0], "SELFTEST", "an in-place Bearer auth bullet replacement should be accepted")
    need(security_diff_problems(old_b, good_b)[3] == OLD_BEARER_PREFIX + " new", "SELFTEST", "the Bearer bullet text should be returned")
    renamed = good[:7] + ["- **Other** new"] + good[7:]
    need(security_diff_problems(old_b, renamed)[0], "SELFTEST", "replacing the Bearer bullet with a different bullet should be rejected")
    wrapped = good[:2] + ["SeedSyncarr is designed to be self-hosted", "on a private network. New:"] + good[3:]
    need(not diff(wrapped), "SELFTEST", "a wrapped intro replacement should be accepted")
    wrapped_bullet = good[:6] + ["  continuation line one", "  continuation line two"] + good[6:]
    need(not diff(wrapped_bullet), "SELFTEST", "a webhook bullet wrapped onto indented continuation lines should be accepted")
    need(security_diff_problems(old, wrapped_bullet)[2] == good[5] + " continuation line one continuation line two",
         "SELFTEST", "a wrapped webhook bullet should be joined into one line of text for the content checks")
    for label, mutate in (
        ("a third changed line", lambda new: new.__setitem__(4, "- **A** changed")),
        ("an added bullet", lambda new: new.insert(7, "- **D** four")),
        ("a deleted line", lambda new: new.__delitem__(6)),
        ("only one of the two edits", lambda new: new.__setitem__(5, old[5])),
        ("an unindented line after the webhook bullet", lambda new: new.insert(6, "continuation")),
        ("a nested list item under the webhook bullet", lambda new: new.insert(6, "  - nested item")),
        ("a new sibling bullet right after the webhook bullet", lambda new: new.insert(6, "- **D** four")),
        ("a blank line inside the webhook bullet", lambda new: new.__setitem__(slice(6, 6), ["", "  continuation"])),
    ):
        candidate = list(good)
        mutate(candidate)
        need(diff(candidate), "SELFTEST", "SECURITY.md diff with {} should be rejected".format(label))
    need(diff(list(old)), "SELFTEST", "an unchanged SECURITY.md should be rejected")


def main():
    group = sys.argv[1] if len(sys.argv) == 2 else ""
    if group not in ("structure", "claims", "security", "scope", "selftest", "all"):
        print(__doc__)
        return 2
    if group in ("selftest", "all"):
        group_selftest()
    if group != "selftest":
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
