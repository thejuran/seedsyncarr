# Architecture Research

**Domain:** Repository rebrand — SeedSync to SeedSyncarr
**Researched:** 2026-04-08
**Confidence:** HIGH (direct codebase inspection, no inference required)

## Standard Architecture

### System Overview

This is not a runtime architecture question. The application's runtime architecture is unchanged. What changes is the identity layer: repo name, container namespace, docs site URL, and all in-code references. The diagram below maps the identity surface that must be updated and how the components connect.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Identity Surface                           │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  New GitHub  │  │  New GHCR    │  │  New Docs Site       │   │
│  │  Repo (fresh)│  │  Namespace   │  │  (gh-pages deploy)   │   │
│  │  seedsyncarr │  │  seedsyncarr │  │  seedsyncarr         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                      │               │
├─────────┴─────────────────┴──────────────────────┴───────────────┤
│                     CI/CD Pipeline                                │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  .github/workflows/master.yml                             │    │
│  │  lint → unittests → build-deb → build-docker             │    │
│  │  → e2etests → publish-docker / publish-deb / publish-docs│    │
│  └──────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│               Codebase Name References (per layer)                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │  Angular   │  │  Python    │  │  Debian Pkg │  │  Docker  │  │
│  │  UI text   │  │  constants │  │  package    │  │  image   │  │
│  │  nav brand │  │  service   │  │  name,      │  │  targets │  │
│  │  about pg  │  │  name,     │  │  service    │  │  user/   │  │
│  │  API URL   │  │  log paths │  │  unit file  │  │  group   │  │
│  └────────────┘  └────────────┘  └─────────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Rename Scope | Files Affected |
|-----------|--------------|----------------|
| GitHub Repo | Fresh repo creation, no fork | Manual step — not a file change |
| GHCR Registry | Image namespace in CI and all docs | `master.yml`, `mkdocs.yml`, `install.md`, `CLAUDE.md`, `README.md` |
| Docs site | `site_url`, `repo_url`, `site_name` in mkdocs | `src/python/mkdocs.yml`, all `.md` files under `src/python/docs/` |
| Angular UI | Brand name in nav, about page, `<title>`, localization strings, GitHub API URL | `app.component.html`, `about-page.component.html`, `index.html`, `localization.ts`, `version-check.service.ts` |
| Python backend | `SERVICE_NAME` constant, class name, log dir path, entry point file name | `constants.py`, `seedsync.py` (renamed to `seedsyncarr.py`) |
| Debian package | Package name, binary path, service unit file name | `control`, `changelog`, rename `seedsync.service` to `seedsyncarr.service` |
| Docker Dockerfiles | Build stage names (`seedsync_*`), user/group names, LABEL source URL, CMD entry | `src/docker/build/docker-image/Dockerfile`, `run_as_user`, `setup_default_config.sh` |
| Docker compose files | Image names, container names | All `compose.yml` files under `src/docker/test/` and `src/docker/stage/` |
| Makefile | Docker target names referencing `seedsync` string | Root `Makefile` |
| Version check service | GitHub releases API URL hardcoded to `thejuran/seedsync` | `version-check.service.ts` |
| CI workflow | `RELEASE_REGISTRY` hardcoded to `ghcr.io/thejuran` + `seedsync` in publish steps | `.github/workflows/master.yml` |
| CLAUDE.md / README | Docker pull commands, repo URLs | Root `CLAUDE.md`, `README.md` |

## Recommended Project Structure

The directory layout does not change. The Python entry point file `src/python/seedsync.py` will be renamed to `src/python/seedsyncarr.py`. All other directory names stay the same — renaming directories like `src/python/` would break imports and Dockerfile `COPY` paths throughout the build system for no user-visible benefit.

```
src/
├── angular/                          # directory name unchanged
│   └── src/
│       ├── index.html                # <title> updated
│       └── app/
│           ├── common/localization.ts                    # brand strings
│           ├── pages/main/app.component.html             # nav brand text
│           ├── pages/about/about-page.component.html     # about page links
│           └── services/utils/version-check.service.ts  # GitHub API URL
├── python/
│   ├── seedsync.py                   # renamed → seedsyncarr.py
│   ├── common/constants.py           # SERVICE_NAME constant
│   └── docs/                         # all markdown content updated
├── debian/
│   ├── control                       # Package: seedsyncarr
│   ├── changelog                     # first entry: seedsyncarr (1.0.0)
│   └── seedsync.service              # renamed → seedsyncarr.service
└── docker/
    ├── build/docker-image/
    │   ├── Dockerfile                # stage names, user/group, LABEL, CMD
    │   ├── run_as_user               # HOME_DIR path
    │   └── setup_default_config.sh   # SCRIPT_PATH reference
    ├── test/                         # compose image/container names
    └── stage/                        # compose image/container names
```

### Structure Rationale

- **Do not rename `src/python/`:** Python import paths, all Dockerfile `COPY` statements, and `make` targets reference this directory. Renaming cascades across a dozen unrelated files for zero benefit.
- **Do rename `seedsync.py` → `seedsyncarr.py`:** This is the public-facing binary name. The deb package installs it to `/usr/lib/seedsyncarr/seedsyncarr` and Docker's `CMD` array references it directly. Leaving it as `seedsync.py` is visible to contributors and looks like an incomplete rename.
- **Rename `seedsync.service` → `seedsyncarr.service`:** The systemd unit filename is what users reference in `sudo service X restart`. It must match the project name.
- **Home directory path must change:** `~/.seedsync` is referenced in `seedsync.service`, `run_as_user`, `setup_default_config.sh`, docs, and FAQ. Leaving it as `.seedsync` means the docs say `~/.seedsyncarr` but the running process writes to `~/.seedsync`, which is invisible breakage.

## Architectural Patterns

### Pattern 1: Single-pass rename in one atomic commit

**What:** Before writing any code, run `grep -r "seedsync\|SeedSync\|SEEDSYNC" src/` across all file types to produce a complete inventory. Execute all renames in a single commit, not spread across multiple PRs.

**When to use:** Always for a brand rename. Partial renames create broken intermediate states that are harder to debug than doing everything at once.

**Trade-offs:** More upfront planning required, but avoids a state where Dockerfile stage names reference old names while compose files reference new names. A mid-rename Docker build fails with a confusing "target not found" error.

### Pattern 2: CI-first, but repo-second

**What:** The CI workflow uses `${GITHUB_REPOSITORY,,}` (lowercased full repo name) to derive the GHCR staging registry automatically. This means once CI runs in `thejuran/seedsyncarr`, it produces `ghcr.io/thejuran/seedsyncarr` without any explicit change to that derivation. The only hardcoded paths are the `RELEASE_REGISTRY=ghcr.io/thejuran` references in the publish jobs, which currently append `seedsync` — those need updating.

**Sequence constraint:** The new repo must exist before pushing the codebase. CI cannot push to a registry namespace derived from a repo that hasn't been created yet.

**When to use:** Any time the registry namespace changes alongside a repo move.

### Pattern 3: Docs site is repo-coupled via gh-pages branch

**What:** The `peaceiris/actions-gh-pages` action in CI commits the built mkdocs site to the `gh-pages` branch of whichever repo CI runs in. The `mkdocs.yml` `site_url` and `repo_url` must reference the new repo; otherwise generated links point to the old one.

**Trade-offs:** GitHub Pages must be explicitly enabled on the new repo (Settings > Pages > Source: `gh-pages` branch) before any deploy runs, or the first CI push will succeed but the site will serve a 404.

## Data Flow

### Rebrand Execution Flow

```
Step 1: Create thejuran/seedsyncarr (fresh, empty, no fork)
    ↓
Step 2: Copy codebase from seedsync working tree (no .git directory)
    ↓
Step 3: git init + initial commit with all original files (pre-rename)
    ↓
Step 4: Rename pass — one atomic commit covering all layers:

    src/python/constants.py             SERVICE_NAME = "seedsyncarr"
    src/python/seedsync.py              → renamed to seedsyncarr.py
    src/python/web/web_app.py           any seedsync log/path strings
    src/debian/control                  Package: seedsyncarr
    src/debian/seedsync.service         → renamed to seedsyncarr.service
                                          ExecStartPre/ExecStart paths updated
    src/angular/src/index.html          <title>SeedSyncarr</title>
    src/angular/src/app/*/              all "SeedSync" UI text
    src/angular/src/.../version-check   GitHub API URL
    src/python/docs/                    all docs content + mkdocs.yml
    src/docker/build/Dockerfile         stage names, user/group, LABEL, CMD
    src/docker/{test,stage}/compose     image names, container names
    src/docker/build/run_as_user        HOME_DIR path
    src/docker/build/setup_default.sh   SCRIPT_PATH reference
    Makefile                            RELEASE_REGISTRY target references
    .github/workflows/master.yml        RELEASE_REGISTRY publish steps
    CLAUDE.md / README.md              docker pull commands, URLs
    ↓
Step 5: Push to new repo → CI green (all jobs must pass)
    ↓
Step 6: Configure GitHub Pages on new repo
        (Settings > Pages > Deploy from branch: gh-pages)
    ↓
Step 7: Tag v1.0.0
        → CI publishes ghcr.io/thejuran/seedsyncarr:1.0.0 + :latest + :1.0
    ↓
Step 8: Archive thejuran/seedsync with pointer to new repo
```

### CI Registry Path — How it works

The staging registry is derived automatically from `${GITHUB_REPOSITORY,,}`. When CI runs in `thejuran/seedsyncarr`, this produces `ghcr.io/thejuran/seedsyncarr` with no explicit change required. The only hardcoded references are in the publish steps:

```yaml
# Current (must change):
RELEASE_REGISTRY=ghcr.io/thejuran
RELEASE_VERSION=seedsync

# After rename (the RELEASE_VERSION here is the docker tag, not the project name —
# these were actually fine; it's the make target that embeds "seedsync" in the image name)
```

The Makefile `docker-image-release` target constructs the full image path as `${RELEASE_REGISTRY}/seedsync:${RELEASE_VERSION}`. The `seedsync` embedded here is the actual part that needs updating to `seedsyncarr`.

## Scaling Considerations

Not applicable. This is a rename operation, not a scalability concern. The runtime architecture is unchanged and sized for single-user self-hosted deployment.

## Anti-Patterns

### Anti-Pattern 1: Incremental rename across multiple commits

**What people do:** Rename one layer (Angular UI), commit and push, then rename another (Python), commit — treating each commit as an independent "green" state.

**Why it's wrong:** Docker build stage names and compose file `target:` references are tightly coupled. A Dockerfile with stages renamed to `seedsyncarr_build_angular_env` but compose files still referencing `seedsync_build_angular_env` produces a confusing build failure. If a release tag is created during the rename window, it ships a broken image.

**Do this instead:** Do all renames in one atomic commit batch. Run the full CI pipeline once against the complete rename.

### Anti-Pattern 2: Rename Dockerfile stages but miss compose file targets

**What people do:** Update `FROM ... AS seedsync_build_angular_env` to `seedsyncarr_build_angular_env` in the Dockerfile but miss the corresponding `target: seedsync_build_angular_env` in compose files.

**Why it's wrong:** Docker build fails with "target not found" — a confusing error that does not mention the rename.

**Do this instead:** When renaming a Dockerfile stage, grep for all references to that stage name across all compose files in the same pass. The Dockerfile has 12+ stage names, all prefixed with `seedsync_`. Each one has corresponding compose references.

### Anti-Pattern 3: Leave the home directory path as `.seedsync`

**What people do:** Rename the service and binary but leave `~/.seedsync` as the config/log directory because it's less visible.

**Why it's wrong:** Users following the new docs will mount `-v ~/.seedsyncarr:/config` and get an empty config. Existing installs will silently continue reading from `~/.seedsync`. The service unit, Docker entrypoint, setup script, FAQ, and installation docs all reference this path explicitly.

**Do this instead:** Update `~/.seedsync` in `seedsyncarr.service` (`ExecStartPre`, `ExecStart`), `run_as_user` (`HOME_DIR`), `setup_default_config.sh` (`SCRIPT_PATH`), and all docs in the same rename pass.

### Anti-Pattern 4: Deploy docs before configuring GitHub Pages source

**What people do:** Run `mkdocs gh-deploy --force` locally or push a commit that triggers CI's publish-docs job, then find `thejuran.github.io/seedsyncarr` returns a 404.

**Why it's wrong:** GitHub Pages must be explicitly enabled on the new repo (Settings > Pages > Deploy from branch: `gh-pages`). The branch can exist with content and still 404 until this setting is saved.

**Do this instead:** Configure GitHub Pages source immediately after creating the new repo, before any docs deploy is attempted. This is a one-time repo configuration step, not a code change.

### Anti-Pattern 5: Treating acknowledgment of the upstream fork as optional

**What people do:** Remove all references to `ipsingh06/seedsync` to make SeedSyncarr look like a fully original project.

**Why it's wrong:** Apache 2.0 requires preservation of attribution notices. More practically, the `*arr` community will check the original project lineage. Trying to obscure it damages credibility; acknowledging it with a clear statement of divergence ("~80-90% diverged, 770+ commits of modernization") actually builds trust.

**Do this instead:** Keep the acknowledgment in the About page and README exactly as specified in the rebrand design spec. The current `about-page.component.html` already has an `ipsingh06/seedsync` link — keep it, just update the framing from "maintained fork" to "evolved from."

## Integration Points

### External Services

| Service | Integration Pattern | Change Required |
|---------|---------------------|-----------------|
| GitHub Container Registry (GHCR) | `ghcr.io/thejuran/seedsync` → `ghcr.io/thejuran/seedsyncarr` | Makefile `docker-image-release` target, all docs pull commands, Dockerfile `LABEL org.opencontainers.image.source` |
| GitHub Releases API | `api.github.com/repos/thejuran/seedsync/releases/latest` | `version-check.service.ts` — one hardcoded URL string |
| GitHub Pages (mkdocs) | `thejuran.github.io/seedsync` → `thejuran.github.io/seedsyncarr` | `mkdocs.yml` `site_url`, docs internal cross-links |
| Sonarr/Radarr webhooks | No change — webhook URLs use host address, not app name | None |

### Internal Boundaries

| Boundary | Communication | Change Required |
|----------|---------------|-----------------|
| Python binary ↔ systemd | Service unit `ExecStart=` path | Rename `seedsync.service` → `seedsyncarr.service`; update binary path inside |
| Docker `CMD` ↔ Python entry point | Hardcoded `seedsync.py` in Dockerfile `CMD` array | Update `CMD` to reference `seedsyncarr.py` |
| Deb post-install ↔ service name | `dpkg` installs service by unit file name | Rename unit file; `postinst` script references service by name |
| Angular About page ↔ upstream repo | Attribution link to `ipsingh06/seedsync` | Keep attribution link; update surrounding text from "maintained fork" to "evolved from" |
| Angular version check ↔ GitHub API | Hardcoded repo path | Update `version-check.service.ts` URL string |
| Docker test/stage containers ↔ build stages | Compose `target:` references Dockerfile stage names | Update all compose `target:` and `image:` values in `src/docker/test/` and `src/docker/stage/` |

## Build Order

The ordering constraint is: CI must run a complete green pipeline (lint, unit tests, E2E tests, Docker image build) before tagging v1.0.0. Within that constraint:

```
Step 1: Infrastructure — must precede all code changes
  - Create thejuran/seedsyncarr on GitHub (empty, not a fork)
  - Configure GitHub Pages: Settings > Pages > Source = gh-pages branch
  - Reason: CI derives registry namespace from GITHUB_REPOSITORY;
    the repo must exist before CI can push to its associated registry.

Step 2: Codebase copy + initial commit
  - Copy working tree (exclude .git, .planning/*, planning docs/*) to new location
  - git init, commit everything as-is (pre-rename)
  - Reason: Establishes a clean baseline commit; the rename commit is then a single
    focused diff that is easy to review.

Step 3: Rename pass — one atomic commit
  All files listed in "Component Responsibilities" above, in any order within the commit.
  Suggested sed targets for verification before committing:
    grep -r "seedsync" src/ --include="*.py" --include="*.ts" --include="*.html"
                             --include="*.yml" --include="*.yaml" --include="*.md"
                             --include="Dockerfile" -l

Step 4: CI green validation
  - Push to master
  - Confirm all jobs pass: lint, Python unit tests, Angular unit tests,
    build-deb (amd64 + arm64), build-docker-image, e2e-deb, e2e-docker-image
  - Manually pull :dev image: docker pull ghcr.io/thejuran/seedsyncarr:dev
  - Run the app locally to verify ~/ directory is ~/.seedsyncarr (not ~/.seedsync)

Step 5: Tag v1.0.0
  - Only after Step 4 is fully confirmed
  - git tag -a v1.0.0 -m "v1.0.0"
  - git push origin v1.0.0
  - CI publishes :1.0.0, :latest in ghcr.io/thejuran/seedsyncarr

Step 6: Archive old repo
  - Add README notice pointing to SeedSyncarr
  - Archive thejuran/seedsync via GitHub repo settings
  - Reason: Do this last so the old repo remains accessible during the transition.
```

**Why this order prevents breakage:**

- Step 1 before Step 3: Without the new repo, `GITHUB_REPOSITORY` resolves to `thejuran/seedsync` during any CI run pushed from the old working tree. The staging registry would still be the old namespace.
- Step 3 as one commit: Dockerfile stage renames and compose `target:` renames must be in sync. A partial rename leaves CI in a broken state that cannot build Docker images.
- Step 4 before Step 5: The E2E tests run the actual Docker image end-to-end, including config path resolution. If `~/.seedsync` was not renamed to `~/.seedsyncarr`, the E2E tests will catch it here rather than after v1.0.0 is tagged and published.
- Step 5 before Step 6: The old repo should remain accessible and unarchived until the new one has a confirmed release at the correct registry.

## Sources

All findings are HIGH confidence — derived from direct inspection of the codebase. No external research was required for integration mapping.

- `/Users/julianamacbook/seedsync/.github/workflows/master.yml` — CI pipeline structure
- `/Users/julianamacbook/seedsync/src/docker/build/docker-image/Dockerfile` — Docker stage names, user/group, CMD
- `/Users/julianamacbook/seedsync/src/python/common/constants.py` — SERVICE_NAME
- `/Users/julianamacbook/seedsync/src/python/seedsync.py` — entry point class and binary name
- `/Users/julianamacbook/seedsync/src/debian/control`, `seedsync.service` — deb package structure
- `/Users/julianamacbook/seedsync/src/angular/src/app/common/localization.ts` — brand strings
- `/Users/julianamacbook/seedsync/src/angular/src/app/pages/about/about-page.component.html` — about page links
- `/Users/julianamacbook/seedsync/src/angular/src/app/services/utils/version-check.service.ts` — hardcoded GitHub API URL
- `/Users/julianamacbook/seedsync/src/python/mkdocs.yml` — docs site configuration
- `/Users/julianamacbook/seedsync/docs/superpowers/specs/2026-04-08-seedsyncarr-rebrand-design.md` — rebrand spec

---
*Architecture research for: SeedSync to SeedSyncarr rebrand*
*Researched: 2026-04-08*
