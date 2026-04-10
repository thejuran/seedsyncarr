---
phase: 61-branding-integration
plan: 05
status: complete
completed: 2026-04-10
---

# Plan 61-05 Summary: GitHub Repo Social Preview Upload

## What was done

Uploaded `doc/brand/social-banner.png` (1584×672 PNG) as the GitHub repo social preview image for `thejuran/seedsyncarr` via **Option C (Web UI fallback)** after Option A (`gh api`) produced an inconclusive result.

## Upload path taken

### Task 1 (auto) — source + gh CLI confirmed
- `doc/brand/social-banner.png`: PNG image data, 1584 x 672 (matches D-14)
- `gh --version`: 2.86.0
- `gh auth status`: logged in as `thejuran` with `repo` scope

### Task 2 Step 1 — Option A attempt (inconclusive)
```
gh api -X PATCH repos/thejuran/seedsyncarr -F social_preview=@doc/brand/social-banner.png
```
Returned a full repo JSON object with no error field (HTTP 200). **However**, GitHub's repo PATCH endpoint silently accepts and ignores unknown multipart fields — a 200 response does not prove the social preview was actually updated. The `social_preview` field is not part of the documented PATCH `/repos/{owner}/{repo}` schema. The OpenGraph endpoint continued to serve what appeared to be the default card after this call, so Option A was treated as failed.

### Task 2 Step 3 — Option C (Web UI) — succeeded
Per CONTEXT.md D-16 fallback, the user performed the upload manually via the GitHub web UI:
1. Navigated to https://github.com/thejuran/seedsyncarr/settings
2. Scrolled to the **Social preview** section
3. Clicked **Edit** → **Upload an image**
4. Selected `/Users/julianamacbook/seedsyncarr/doc/brand/social-banner.png`
5. Saved

User visually confirmed the SeedSyncarr banner is now set as the repo social preview via the Settings page (reply: "approved C").

## Verification

### Automated (post-approval)
```
$ curl -sL -o /tmp/og-preview-seedsyncarr.png https://opengraph.githubassets.com/1/thejuran/seedsyncarr
$ file /tmp/og-preview-seedsyncarr.png
/tmp/og-preview-seedsyncarr.png: PNG image data, 1200 x 600, 8-bit/color RGB, non-interlaced
$ ls -la /tmp/og-preview-seedsyncarr.png
-rw-r--r--  1 julianamacbook  wheel  78676 Apr 10 14:00 /tmp/og-preview-seedsyncarr.png
```
- Valid PNG served
- Non-zero size (78 KB)
- GitHub's OpenGraph endpoint may cache briefly; new banner will propagate to link previews on Reddit/Discord/Twitter as caches expire

### Human visual check
User confirmed via GitHub Settings → Social preview section that the uploaded SeedSyncarr banner (arrow mark + wordmark + tagline) is now set as the repo social preview.

## Outcome

- **Option used:** C (Web UI)
- **No file commits** — this plan's effect is on GitHub repo settings only (`files_modified: []` per plan front matter)
- PLSH-06 implemented
- ROADMAP.md success criterion #3 (social preview set) met

All acceptance criteria from 61-05-PLAN.md met.
