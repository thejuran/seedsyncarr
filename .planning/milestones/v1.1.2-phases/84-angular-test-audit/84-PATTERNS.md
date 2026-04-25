# Phase 84: Angular Test Audit - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 7 (6 spec files to migrate + 1 config file to verify)
**Analogs found:** 7 / 7

---

## File Classification

| File to Modify | Role | Data Flow | Closest Analog | Match Quality |
|----------------|------|-----------|----------------|---------------|
| `tests/unittests/services/autoqueue/autoqueue.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `tests/unittests/services/server/bulk-command.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `tests/unittests/services/settings/config.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `tests/unittests/services/files/model-file.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `tests/unittests/services/utils/rest.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `tests/unittests/services/server/server-command.service.spec.ts` | test | request-response | `tests/unittests/services/utils/auth.interceptor.spec.ts` | exact |
| `src/angular/karma.conf.js` | config | — | `src/angular/karma.conf.js` (self — verify only) | self |

All files are in `src/angular/src/app/` unless shown as `src/angular/`.

---

## Pattern Assignments

### The Migration Pattern (applies to all 6 spec files)

**Analog:** `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts`

This is the single established pattern in the codebase. All 6 spec files perform the same mechanical substitution.

**Imports — before (deprecated, lines 2 in each file):**
```typescript
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Imports — after (copy from auth.interceptor.spec.ts lines 2-3):**
```typescript
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

Note: Some files also need `HttpClient` from `@angular/common/http` if they inject it directly. `auth.interceptor.spec.ts` imports `HttpClient` alongside `provideHttpClient` (line 2):
```typescript
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
```
For service specs that do not inject `HttpClient` directly, only `provideHttpClient` is needed (no `HttpClient` import).

**TestBed configuration — before (deprecated pattern shared across all 6 files):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        // ... service providers ...
    ]
});
```

**TestBed configuration — after (copy from auth.interceptor.spec.ts lines 29-34):**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        // ... existing service providers unchanged ...
    ]
});
```

**HttpTestingController injection — UNCHANGED (copy from auth.interceptor.spec.ts line 37):**
```typescript
httpMock = TestBed.inject(HttpTestingController);
```
This line does not change. `HttpTestingController` injection is unaffected by the migration.

---

### `autoqueue.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/autoqueue/autoqueue.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 25-37):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        AutoQueueService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        AutoQueueService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

---

### `bulk-command.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {TestBed, fakeAsync, tick} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {TestBed, fakeAsync, tick} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 14-21):**
```typescript
TestBed.configureTestingModule({
    imports: [HttpClientTestingModule],
    providers: [
        BulkCommandService,
        {provide: LoggerService, useValue: mockLogger}
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        BulkCommandService,
        {provide: LoggerService, useValue: mockLogger}
    ]
});
```

---

### `config.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 25-37):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        ConfigService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ConfigService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

---

### `model-file.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 20-32):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        LoggerService,
        RestService,
        ModelFileService
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        LoggerService,
        RestService,
        ModelFileService
    ]
});
```

---

### `rest.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {fakeAsync, TestBed} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {fakeAsync, TestBed} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 14-23):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        RestService,
        LoggerService,
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        RestService,
        LoggerService,
    ]
});
```

---

### `server-command.service.spec.ts` (service test, request-response)

**Full path:** `src/angular/src/app/tests/unittests/services/server/server-command.service.spec.ts`

**Current deprecated imports (lines 1-2):**
```typescript
import {TestBed} from "@angular/core/testing";
import {HttpClientTestingModule, HttpTestingController} from "@angular/common/http/testing";
```

**Replace with:**
```typescript
import {TestBed} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
```

**Current TestBed block (lines 17-29):**
```typescript
TestBed.configureTestingModule({
    imports: [
        HttpClientTestingModule
    ],
    providers: [
        ServerCommandService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

**Replace with:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ServerCommandService,
        LoggerService,
        RestService,
        ConnectedService,
        {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
    ]
});
```

---

### `karma.conf.js` (config — verify/possibly modify)

**Full path:** `src/angular/karma.conf.js`

**Potentially stale key (lines 27-29):**
```javascript
angularCli: {
    environment: 'dev'
},
```
This is a legacy Angular CLI v1 option. In `@angular/build:karma` (Angular 21), this key is silently ignored or may produce a deprecation warning. Verification action: run `ng test --watch=false` and inspect output for any warning mentioning `angularCli`. If a warning appears, remove lines 27-29. If silent, leave unchanged.

**captureConsole setting (line 17) — confirmed correct, do not change:**
```javascript
captureConsole: false,
```
This suppresses client-side `console.debug/warn/error` calls from test code (including `base-stream.service.spec.ts` line 16), so those do not surface in Karma output.

---

## Shared Patterns

### HttpClientTestingModule → provideHttpClient Migration
**Source:** `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` (lines 2-3, 29-34, 37)
**Apply to:** All 6 spec files listed in File Classification above

The three-part substitution:
1. Remove `HttpClientTestingModule` from the `imports` in `TestBed.configureTestingModule`
2. Add `provideHttpClient()` and `provideHttpClientTesting()` to `providers`
3. Add `provideHttpClient` to the `@angular/common/http` import; keep `HttpTestingController` import from `@angular/common/http/testing`
4. Leave `httpMock = TestBed.inject(HttpTestingController)` unchanged in all files

### Staleness Audit (zero-removal)
**Source:** RESEARCH.md exhaustive cross-reference (2026-04-24)
**Apply to:** Inventory documentation task

All 40 spec files reference live production code. The inventory table (D-06) records zero removals. No spec files are deleted; no mock files are deleted.

### Coverage Baseline (D-09)
**Command:** `cd src/angular && node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false --code-coverage`
**Output:** `src/angular/coverage/`
**Apply to:** Pre-migration baseline capture, post-migration baseline capture (two runs)

---

## No Analog Found

None. All 6 spec files have an exact analog in `auth.interceptor.spec.ts` which already uses the target migration pattern.

---

## Metadata

**Analog search scope:** `src/angular/src/app/tests/unittests/` (37 files), `src/angular/src/app/pages/` (3 co-located specs)
**Files scanned:** 7 (auth.interceptor.spec.ts as primary analog + 6 migration targets + karma.conf.js)
**Key finding:** Zero stale spec files, zero orphaned mocks. Work is purely: (1) document zero-removal audit, (2) capture coverage baseline, (3) migrate 6 HttpClientTestingModule usages, (4) verify karma.conf.js angularCli key, (5) confirm green suite.
**Pattern extraction date:** 2026-04-24
