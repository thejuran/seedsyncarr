---
phase: quick-260604-gmy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/angular/src/app/pages/main/notification-bell.component.html
  - src/angular/src/app/pages/settings/settings-page.component.html
  - src/angular/src/app/pages/settings/settings-page.component.ts
  - src/angular/src/app/pages/settings/options-list.ts
autonomous: true
requirements: []
must_haves:
  truths:
    - "Production `ng build` (Angular v22, strict templates) compiles the Angular app with zero TS errors"
    - "The Build Docker Image CI job on PR #50 is green"
    - "PR #50 (Angular v21->v22 dependency bump) is squash-merged with the branch deleted"
    - "Type fixes are sound: no strictTemplates disabled, no `as any` / `as` casts in templates, any unavoidable cast is localized to ONE place in component .ts with a comment"
    - "notification-bell badge still only renders when there is at least one notification"
    - "Settings page still reads and writes every config option exactly as before (no behavior change)"
  artifacts:
    - path: "src/angular/src/app/pages/main/notification-bell.component.html"
      provides: "Null-safe notification count comparison"
      contains: "notifs?.size ?? 0"
    - path: "src/angular/src/app/pages/settings/settings-page.component.ts"
      provides: "Typed accessor that performs the nested Immutable get in one isolated, type-sound place"
      contains: "getConfigValue"
    - path: "src/angular/src/app/pages/settings/settings-page.component.html"
      provides: "Template bindings that no longer chain `.get().get()` on plain-interface-typed Immutable Records"
  key_links:
    - from: "src/angular/src/app/pages/settings/settings-page.component.html"
      to: "src/angular/src/app/pages/settings/settings-page.component.ts getConfigValue"
      via: "template binding calls the typed accessor instead of chained Immutable get"
      pattern: "getConfigValue\\("
    - from: "PR #50 dependabot branch"
      to: "GitHub Actions Build Docker Image job"
      via: "push to dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef triggers CI"
      pattern: "Build Docker Image"
---

<objective>
Fix the Angular v22 strict-template TypeScript errors that block the Dependabot PR #50 production `ng build` (the only failing CI job — "Build Docker Image"), then squash-merge PR #50 once CI is fully green.

PR #50 bumps Angular v21 -> v22 and only touches `package.json` / `package-lock.json`. Angular 22's compiler enables stricter template type-checking, surfacing latent template type errors that v21 tolerated. The source files are identical to `main`, so the fixes are planned against the current working tree but MUST land on the existing Dependabot branch, not on `main`.

Purpose: unblock the Angular v22 security/dependency upgrade without weakening type safety.
Output: type-sound source fixes pushed to the Dependabot branch; green CI; merged PR #50; local `main` updated.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Root-cause analysis (already fully diagnosed by the orchestrator — do NOT re-run CI to re-discover):

The `Config` class (`src/angular/src/app/services/settings/config.ts`) extends an Immutable.js `Record`. At RUNTIME each section is itself an Immutable `Record` instance (constructor does `lftp: LftpRecord(props.lftp)`, etc.), so `config.get('lftp').get('remote_address')` works at runtime. But the TypeScript declarations type each section as a PLAIN interface (`lftp!: ILftp`, `general!: IGeneral`, ...). Immutable's `Record.get<K>(key)` returns the VALUE type for that key — i.e. `config.get('lftp')` is typed `ILftp`, a plain interface with NO `.get()` method. v22's strict template checker therefore flags every `(config | async)?.get(SECTION)?.get(OPTION)` chain.

Concrete errors from the failing build (run 26962884144):
- notification-bell.component.html:5 — TS2532 "Object is possibly 'undefined'": `notifs?.size > 0` where `notifs?.size` is `number | undefined`.
- settings-page.component.html — TS2339 "Property 'get' does not exist on type 'ILftp'" (and on the union `IGeneral | ILftp | ...` when the key is the variable `option.valuePath[0]`) at the chained `.get(...).get(...)` bindings (lines incl. :42, :69, :73, :77, :81, :85, :91, :95, :99, :117, :122, :153, :163, :195, :409, and the `[ngModel]`/`fieldset`/`webhook` `.get('section')?.get('option')` chains).
- settings-page.component.html — TS2345 "Argument of type 'string' is not assignable to parameter of type 'keyof IConfig'": `option.valuePath[0]` is typed `string` (see `IOption.valuePath: [string, string]` in options-list.ts) but `Config.get` expects `keyof IConfig`.
- settings-page.component.html:41 / :116 — TS2322 "Type 'string | null' is not assignable to type 'string'": `app-option`'s `[value]` is declared NON-nullable (`@Input() value!: string | number | boolean`), but the chained async binding is nullable.

Relevant existing contracts (do not re-explore the codebase — these are the contracts you need):

```typescript
// config.ts — section getters are typed as plain interfaces, but are Immutable Records at runtime
export interface IConfig {
  general: IGeneral; lftp: ILftp; controller: IController; web: IWeb;
  autoqueue: IAutoQueue; sonarr: ISonarr; radarr: IRadarr; autodelete: IAutoDelete;
}
export class Config extends ConfigRecord implements IConfig { /* ... */ }

// options-list.ts — valuePath first element is typed `string`, not keyof IConfig
export interface IOption { type: OptionType; label: string; valuePath: [string, string]; description: string | null; }

// option.component.ts — value input is NON-nullable; template uses `[disabled]="value == null"` so it already tolerates null at runtime
@Input() value!: string | number | boolean;
@Output() changeEvent = new EventEmitter<string | number | boolean>();

// settings-page.component.ts
public config: Observable<Config | null>;
onSetConfig(section: string, option: string, value: string | number | boolean): void
formatMs(val: unknown): string   // already accepts unknown
```

Environment / merge facts:
- Target branch: `dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` (already has commit 6255efe adding the `istanbul-lib-instrument` devDep).
- Only the "Build Docker Image" CI job fails today; all others (Lint Angular, Angular unit tests, Python, CodeQL) pass on v22. The authoritative gate is the Build Docker Image job (production `ng build` with strict templates). Lint + Karma do NOT exercise strict template type-checking, so a passing local lint/test is NOT proof.
- Merge convention (matches #51/#49): `gh pr merge 50 --squash --delete-branch`.
- No git worktree isolation. Do NOT commit to `main`. Do NOT commit `.planning/` artifacts to the Dependabot branch.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Check out the Dependabot branch and apply type-sound source fixes</name>
  <files>
    src/angular/src/app/pages/main/notification-bell.component.html
    src/angular/src/app/pages/settings/settings-page.component.ts
    src/angular/src/app/pages/settings/settings-page.component.html
    src/angular/src/app/pages/settings/options-list.ts
  </files>
  <action>
First, get onto the Dependabot branch (this work must land there, NOT on main):
- `git fetch origin dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef`
- Check out as a tracking branch: `git checkout -b dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef --track origin/dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` (if the local branch already exists, `git checkout` it then `git pull --ff-only`). Confirm HEAD is at or after commit 6255efe and that `git status` is clean before editing.

Then apply the following fixes. After checkout the working-tree source for these files is identical to main (PR #50 only changes package.json/lock), so the edits below describe the exact transformations.

FIX 1 — notification-bell.component.html (TS2532):
- Line 5: change `@if (notifs?.size > 0) {` to `@if ((notifs?.size ?? 0) > 0) {`. Nullish-coalesce the size to 0 before the `> 0` comparison. Do NOT use a non-null assertion `!` (CLAUDE.md forbids `!` without a preceding guard).

FIX 2 — settings-page.component.ts: add a typed accessor that isolates the one unavoidable cast.
- Add a public method `getConfigValue(config: Config | null, section: keyof IConfig, option: string): string | number | boolean`. It reads the nested Immutable value in ONE place and returns a non-nullable value with a sensible default of empty string `""` so the non-nullable `app-option [value]` input is satisfied. Implementation approach (type-sound, CLAUDE.md-compliant): use Immutable's `getIn` — `config?.getIn([section, option])` returns `unknown`. Narrow it: if the value is `string | number | boolean`, return it; otherwise return `""`. Keep the narrowing explicit (typeof checks), NOT an `as` cast. If `getIn`'s typing proves awkward, the single localized cast permitted is to treat the section Record via Immutable's `Record` get — but isolate ANY cast to this one method and add a comment explaining that `Config` stores sections as Immutable Records at runtime though they are typed as plain interfaces. There must be ZERO casts in templates.
- Import `IConfig` (and `Config` if not already imported) at the top: `import {Config, IConfig} from "../../services/settings/config";` (currently only `Config` is imported — add `IConfig`).
- Change `onSetConfig(section: string, ...)` signature to `onSetConfig(section: keyof IConfig, option: string, value: string | number | boolean)` to resolve the TS2345 keyof IConfig error at the call sites. Verify the body still compiles: `section + "." + option` (string concat of a keyof IConfig string literal is fine) and `this._configService.set(section, option, value)` — if `ConfigService.set` declares its first param as `string`, a `keyof IConfig` is assignable to `string`, so no change needed there. Do NOT widen ConfigService.

FIX 3 — options-list.ts: type valuePath's section element as `keyof IConfig`.
- Change `IOption.valuePath: [string, string]` to `valuePath: [keyof IConfig, string]`. Import the type: `import {IConfig} from "../../services/settings/config";` at the top of options-list.ts. This makes every `option.valuePath[0]` a `keyof IConfig`, satisfying both `getConfigValue`'s `section` param and `onSetConfig`'s new `section` param. The existing literal values ("lftp", "controller", "web", "general", "autoqueue", "autodelete") are already valid `keyof IConfig` members, so the object literals stay unchanged.

FIX 4 — settings-page.component.html: replace every chained `.get(SECTION)?.get(OPTION)` value binding with the typed accessor.
- For `app-option [value]` bindings: replace `[value]="(config | async)?.get(option.valuePath[0])?.get(option.valuePath[1])"` with `[value]="getConfigValue(config | async, option.valuePath[0], option.valuePath[1])"`. Apply to ALL such bindings (the *ngFor app-option bindings at ~:42, :117, :153, :163, :195, :409, the optionsList ng-template at :14, and every hardcoded lftp/sonarr/radarr app-option `[value]` binding at :69, :73, :77, :81, :85, :91, :95, :99, :267, :276, :337, :345). For the hardcoded ones the section is a string literal (e.g. `'lftp'`) which is already a valid `keyof IConfig`, so `getConfigValue(config | async, 'lftp', 'remote_address')` type-checks.
- For the `formatMs(...)` hint at :122: replace the inner chained get with the accessor — `{{formatMs(getConfigValue(config | async, option.valuePath[0], option.valuePath[1]))}}`. `formatMs(val: unknown)` accepts the `string | number | boolean` return fine.
- For the `[ngModel]` toggle bindings and `fieldset [attr.disabled]` / `settings-card-body` `[class...]` / `[attr.inert]` bindings that read `(config | async)?.get('autoqueue')?.get('enabled')`, `(config | async)?.get('sonarr')?.get('enabled')`, `(config | async)?.get('radarr')?.get('enabled')`, `(config | async)?.get('autodelete')?.get('enabled')`: these are boolean reads, also hitting TS2339. Replace each with `getConfigValue(config | async, 'sonarr', 'enabled')` etc. The accessor returns `string | number | boolean`; for `[ngModel]` on a checkbox and for `!(...)` / `[class.x]` / `[attr.disabled]` truthiness this is acceptable (same runtime behavior). If the `(ngModelChange)="onSetConfig('sonarr', 'enabled', $event)"` companion needs its section literal typed — it already is a literal assignable to `keyof IConfig`, no change.
- For the webhook port bindings `((config | async)?.get('web')?.get('port'))` at :304 and :373 (string concatenation building the webhook URL): replace with `getConfigValue(config | async, 'web', 'port')`. Returns a number/empty-string; string concatenation works the same.
- After edits, NO `.get(` chained call on the config async value should remain in the template. Verify with the grep in <verify>.

Optional best-effort local build (NOT the gate): you MAY run `npm install --legacy-peer-deps` inside `src/angular` to pull the v22 toolchain locally, then `npx ng build --configuration production` (or the project's prod build script) to reproduce strict templates locally. If the local toolchain stays on v21 or install is slow/flaky, skip it — the binding gate is CI. Do not commit any node_modules or lockfile changes from a local install beyond what is already on the branch.
  </action>
  <verify>
Run from repo root, on the Dependabot branch:
- Confirm branch: `git rev-parse --abbrev-ref HEAD` shows `dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef`.
- No bare unsafe size comparison remains: `grep -n 'notifs?.size >' src/angular/src/app/pages/main/notification-bell.component.html` returns NOTHING (the only match should be the `?? 0` form). Positively confirm: `grep -c 'notifs?.size ?? 0' src/angular/src/app/pages/main/notification-bell.component.html` returns `1`.
- No chained `.get(` on the config async value remains feeding bindings: `grep -nE '\(config \| async\)\?\.get\(' src/angular/src/app/pages/settings/settings-page.component.html` returns NOTHING.
- Accessor is wired in the template: `grep -c 'getConfigValue(' src/angular/src/app/pages/settings/settings-page.component.html` returns a count > 0 (every replaced binding).
- Accessor exists in the component: `grep -n 'getConfigValue' src/angular/src/app/pages/settings/settings-page.component.ts` shows the method definition.
- No `as any` or unsafe casts in templates: `grep -nE '\$any\(|as any' src/angular/src/app/pages/settings/settings-page.component.html` returns NOTHING.
- valuePath retyped: `grep -n 'valuePath: \[keyof IConfig' src/angular/src/app/pages/settings/options-list.ts` shows the change.
- strictTemplates NOT disabled: `grep -rn 'strictTemplates' src/angular/ 2>/dev/null` shows it either still `true` or absent (NOT set to `false`).
- Best-effort: if a local v22 build was run, `npx ng build --configuration production` exits 0. (Authoritative gate is CI in Task 2.)
  </verify>
  <done>
On the Dependabot branch, all template type-error sources are removed using a typed accessor (no template casts, strictTemplates intact). The four files are edited; grep verifications pass. Local prod build passes if it was attempted; otherwise local check is deferred to CI.
  </done>
</task>

<task type="auto">
  <name>Task 2: Commit + push to the Dependabot branch, watch CI, then squash-merge PR #50</name>
  <files>
    (git operations only — no new files)
  </files>
  <action>
Still on branch `dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef`:

1. Stage ONLY the four source fixes (never `.planning/`):
   `git add src/angular/src/app/pages/main/notification-bell.component.html src/angular/src/app/pages/settings/settings-page.component.ts src/angular/src/app/pages/settings/settings-page.component.html src/angular/src/app/pages/settings/options-list.ts`
   Run `git status` and confirm nothing under `.planning/` and no stray files (node_modules, lockfiles) are staged.

2. Commit:
   `git commit -m "fix(angular): resolve v22 strict-template type errors (TS2532/TS2339/TS2345/TS2322)"`
   (Follow the repo's existing commit style — no Co-Authored-By trailer is required for a fix commit on a dependabot branch; match the branch's existing commit 6255efe style.)

3. Push to the same remote Dependabot branch:
   `git push origin dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef`

4. Watch CI to completion:
   `gh pr checks 50 --watch`
   The AUTHORITATIVE gate is the "Build Docker Image" job. Confirm it (and all non-skipped jobs) report `pass`. Jobs marked `skipping` (Publish*, End-to-end, Publish Documentation) are expected to skip on a non-release PR and are fine.

5. If the Build Docker Image job now surfaces ADDITIONAL v22 template/type errors of the SAME class (strict-template TS errors, small in number): fix them using the same typed-accessor / nullish-coalesce patterns from Task 1, commit with a similar `fix(angular):` message, push, and re-watch. If new errors balloon into a large migration (many unrelated files, runtime/behavioral changes, or non-template TS errors), STOP and report back rather than expanding scope.

6. Once ALL checks are green, squash-merge with branch deletion (matches the repo's #51/#49 convention):
   `gh pr merge 50 --squash --delete-branch`
   Confirm the merge succeeded (`gh pr view 50 --json state,mergedAt` shows `MERGED`).

7. Return local repo to main and sync:
   `git checkout main && git pull --ff-only origin main`
   Confirm `git rev-parse --abbrev-ref HEAD` is `main` and the merge commit for PR #50 is present in `git log --oneline -5`.
  </action>
  <verify>
- `gh pr view 50 --json state,mergedAt` reports `"state":"MERGED"` with a non-null `mergedAt`.
- `gh pr checks 50` shows the "Build Docker Image" job as `pass` (no `fail`).
- Local HEAD is `main`: `git rev-parse --abbrev-ref HEAD` returns `main`.
- The PR #50 squash commit is in main history: `git log --oneline -5` includes the merged dependabot bump.
- The remote dependabot branch is deleted: `git ls-remote --heads origin dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` returns NOTHING.
  </verify>
  <done>
PR #50 is squash-merged with the dependabot branch deleted, CI fully green (Build Docker Image passing), and the local checkout is back on an up-to-date `main` containing the merge. No `.planning/` artifacts were committed to the dependabot branch.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Dependabot branch -> main (via squash merge) | A third-party dependency bump (Angular v21->v22, 18 npm updates) crosses into the trusted main branch. CI is the gate. |
| package-lock changes -> build/runtime | npm dependency tree changes could introduce malicious or broken transitive deps. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-gmy-01 | Tampering | Type-soundness regression (disabling strictTemplates or `as any` to "make it build") | mitigate | Plan forbids disabling strictTemplates and forbids template casts; grep verification gates in Task 1 assert strictTemplates intact and no `$any(`/`as any` in templates. |
| T-gmy-02 | Tampering | Wrong branch target (committing fixes to main instead of the dependabot branch) | mitigate | Task 1 checks out and verifies the dependabot branch by name before editing; Task 2 verifies branch name before commit/push. |
| T-gmy-03 | Information Disclosure | Accidentally committing `.planning/` or local secrets to the public-facing dependabot branch | mitigate | Task 2 stages only the four named source files and runs `git status` to confirm no `.planning/` / stray files staged. |
| T-gmy-SC | Tampering | npm dependency bump (Angular v22 + 17 others) supply-chain risk | accept | Dependabot-sourced group bump already reviewed at the dependency level in prior quick task 260604-g9c; CI (CodeQL, Build, unit tests) is the gate. No new packages are hand-added here beyond the already-present istanbul-lib-instrument devDep on the branch. Behavioral change is limited to type annotations + a null-safe template accessor. |
</threat_model>

<verification>
- Production `ng build` (strict templates, Angular v22) compiles with zero TS errors — proven by the "Build Docker Image" CI job turning green on PR #50.
- Type safety preserved: strictTemplates not disabled; no `as any` / template casts; any unavoidable cast confined to one commented place in `settings-page.component.ts`.
- No behavior change: notification badge logic and every settings read/write path are functionally identical (only type annotations + a value-accessor indirection changed).
- PR #50 squash-merged, dependabot branch deleted, local main updated.
</verification>

<success_criteria>
- [ ] Dependabot branch checked out; four source files fixed with the typed-accessor + nullish-coalesce approach
- [ ] All grep gates in Task 1 pass (no chained `.get(`, no bare `notifs?.size >`, accessor wired, strictTemplates intact, no template casts)
- [ ] Fixes committed and pushed to `dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` (no `.planning/` committed)
- [ ] "Build Docker Image" CI job on PR #50 is green; all other non-skipped checks pass
- [ ] PR #50 squash-merged with `--delete-branch`; `gh pr view 50` shows MERGED
- [ ] Local repo back on an up-to-date `main` containing the merge
</success_criteria>

<output>
Create `.planning/quick/260604-gmy-fix-angular-v22-typescript-template-type/260604-gmy-SUMMARY.md` when done.
</output>
