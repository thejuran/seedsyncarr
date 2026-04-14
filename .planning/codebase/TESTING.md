# Testing Patterns

**Analysis Date:** 2026-02-03

## Test Framework

**Runner (Angular):**
- **Framework**: Karma 6.4.4 with Jasmine 5.1.0
- **Config**: `/Users/julianamacbook/seedsync/src/angular/karma.conf.js`
- **Test command**: `npm run test` (runs in watch mode)
- **Headless CI**: Uses ChromeHeadlessCI custom launcher with flags for sandboxless execution
- **Timeout**: 10 second timeout for async tests (configurable)
- **Test order**: Consistent (random: false) for reproducible debugging

**Assertion Library:**
- **Jasmine** 5.1.0 for expectations
- **API**: `expect(value).toBe(expected)`, `expect(value).toEqual(expected)`
- **Spies**: `jasmine.createSpyObj()` for mocking services
- **Setup/Teardown**: `beforeEach()`, `afterEach()` hooks

**Runner (Python):**
- **Framework**: pytest 7.4.4
- **Config**: `/Users/julianamacbook/seedsync/src/python/pyproject.toml`
- **Command**: `poetry run pytest` (from `/Users/julianamacbook/seedsync/src/python/`)
- **Timeout**: 60 seconds per test (pytest-timeout plugin)
- **Test discovery**: Automatic (test_*.py and *_test.py files)

**Runner (E2E):**
- **Framework**: Playwright 1.48.0 with TypeScript
- **Angular E2E**: `/Users/julianamacbook/seedsync/src/angular/playwright.config.ts`
  - Test pattern: `**/*.e2e-spec.ts`
  - Base URL: `http://localhost:4200`
  - Web server: Auto-starts with `npm run start`
  - Single worker for consistent test isolation
- **Main E2E**: `/Users/julianamacbook/seedsync/src/e2e/playwright.config.ts`
  - Test pattern: `**/*.spec.ts`
  - Base URL: `http://myapp:8800` (configurable via `APP_BASE_URL`)
  - Single worker for stateful test execution
  - Timeout: 30 seconds per test
  - Expect timeout: 5 seconds for assertions

## Test File Organization

**Location (Angular):**
- **Co-located pattern**: Tests are separate in dedicated test directory
- **Path**: `/Users/julianamacbook/seedsync/src/app/tests/unittests/`
- **Structure**:
  ```
  src/app/tests/unittests/
  ├── common/           # Pipe tests
  ├── pages/            # Component tests
  │   └── files/
  │       ├── file.component.spec.ts
  │       ├── file-list.component.spec.ts
  │       └── bulk-actions-bar.component.spec.ts
  ├── services/         # Service tests
  │   ├── autoqueue/
  │   ├── files/
  │   ├── server/
  │   └── utils/
  └── mocks/            # Test doubles
      ├── mock-view-file.service.ts
      ├── mock-rest.service.ts
      └── mock-model-file.service.ts
  ```

**Naming (Angular):**
- Test file matches source: `file.component.ts` → `file.component.spec.ts`
- Suffix: `.spec.ts` (Karma convention)

**Location (Python):**
- **Path**: `/Users/julianamacbook/seedsync/src/python/tests/`
- **Structure**:
  ```
  tests/
  └── integration/
      ├── test_web/
      │   ├── test_web_app.py      # Base test class
      │   └── test_handler/
      │       ├── test_status.py
      │       ├── test_server.py
      │       └── test_stream_status.py
      └── test_lftp/
          └── test_lftp.py
  ```

**Location (E2E):**
- **Angular E2E**: `/Users/julianamacbook/seedsync/src/angular/e2e/` with `*.e2e-spec.ts` pattern
- **Main E2E**: `/Users/julianamacbook/seedsync/src/e2e/tests/` with `*.spec.ts` pattern
- **Page Objects**: `/Users/julianamacbook/seedsync/src/e2e/tests/` (app.ts, dashboard.page.ts, etc.)

## Test Structure

**Suite Organization (Jasmine):**
```typescript
describe("Testing file component", () => {
    let component: FileComponent;
    let fixture: ComponentFixture<FileComponent>;
    let fileSelectionService: FileSelectionService;
    let mockConfirmModalService: jasmine.SpyObj<ConfirmModalService>;

    beforeEach(async () => {
        // Setup: Configure test module
        await TestBed.configureTestingModule({
            imports: [FileComponent],
            providers: [
                FileSelectionService,
                {provide: ConfirmModalService, useValue: mockConfirmModalService}
            ]
        })
        .compileComponents();

        // Get service instances
        fileSelectionService = TestBed.inject(FileSelectionService);
        fixture = TestBed.createComponent(FileComponent);
        component = fixture.componentInstance;
    });

    it("should create an instance", () => {
        expect(component).toBeDefined();
    });

    it("should perform action on event", () => {
        // Test implementation
        expect(result).toBe(expected);
    });
});
```

**Patterns (Angular):**
- **TestBed pattern**: Setup DI provider configuration before each test
- **Fixture creation**: `TestBed.createComponent(ComponentClass)` returns `ComponentFixture<T>`
- **Service injection**: `TestBed.inject(ServiceClass)` gets singleton instances
- **Override template**: `.overrideTemplate()` simplifies testing component logic without HTML
- **Async timing**: `fakeAsync()` + `tick()` for controlling async operations

**Suite Organization (pytest):**
```python
class BaseTestWebApp(unittest.TestCase):
    """Base class for testing web app"""

    def setUp(self):
        self.context = MagicMock()
        self.controller = MagicMock()
        # Real instances where needed
        self.context.status = Status()
        self.context.config = Config()
        # Setup captured listeners
        self.model_listener = None

    def test_status(self):
        resp = self.test_app.get("/server/status")
        self.assertEqual(200, resp.status_int)
```

**Patterns (Python):**
- **unittest.TestCase**: Standard base class
- **setUp/tearDown**: Automatic test setup/cleanup
- **MagicMock**: Extensive mocking of controller and context
- **Real instances**: Config, Status, and other data objects are real (not mocked)
- **assertions**: `self.assertEqual()`, `self.assertTrue()`, etc.

## Mocking

**Framework (Angular):**
- **Jasmine Spies**: `jasmine.createSpyObj()` for creating mock services
- **HttpTestingController**: `TestBed.inject(HttpTestingController)` for mocking HTTP
- **Expectation/Flush pattern**:
  ```typescript
  httpMock.expectOne("/endpoint").flush(responseData);
  ```
- **Error simulation**:
  ```typescript
  httpMock.expectOne("/endpoint").flush(
      "Error message",
      {status: 404, statusText: "Not Found"}
  );
  ```

**Patterns to Mock:**
- **HTTP Services**: All external API calls via HttpTestingController
- **Service dependencies**: Use `jasmine.createSpyObj()` for test doubles
- **Modal/Dialog services**: Mock confirmation dialogs

**What NOT to Mock:**
- **Component dependencies injected via DI**: Keep real when testing integration
- **Core Angular services**: Use TestBed-provided instances
- **Data models**: Create real instances for validation

**Framework (Python):**
- **unittest.mock**: `MagicMock` for services and external dependencies
- **WebTest**: TestApp wrapper for WSGI application testing
- **Side effects**: Configure mocks with `.side_effect = capture_listener`

Example from test_web_app.py:
```python
self.controller.get_model_files_and_add_listener = MagicMock()
self.controller.get_model_files_and_add_listener.side_effect = capture_listener
```

## Fixtures and Factories

**Test Data (Angular):**
- **Created inline in tests**: Hard-coded test objects
- **Example from file.component.spec.ts**:
  ```typescript
  const testFile = new ViewFile({
      name: "test-file.mkv",
      isQueueable: true,
      isStoppable: false,
      isExtractable: true,
      isArchive: true,
      isLocallyDeletable: true,
      isRemotelyDeletable: true
  });

  const testOptions = new ViewFileOptions({showDetails: false});
  ```
- **Location**: Defined at top of spec file (not in separate fixtures directory)

**Test Data (Python):**
- **Fixtures**: Minimal - mostly rely on real object instantiation
- **Model data**: Created in test methods as needed
- **Location**: `/Users/julianamacbook/seedsync/src/python/tests/`

**Factories:**
- Not widely used - tests create objects directly
- Mock services use `.side_effect` callbacks to capture state during tests

## Coverage

**Requirements (Angular):**
- No coverage target enforced
- Coverage reports generated: `coverage/` directory in HTML format

**View Coverage:**
```bash
# Run tests with coverage
cd /Users/julianamacbook/seedsync/src/angular
npm run test -- --code-coverage

# View HTML report
open coverage/index.html
```

**Requirements (Python):**
- No explicit coverage requirement
- pytest-timeout plugin prevents hanging tests (60 second timeout)

**View Coverage:**
```bash
cd /Users/julianamacbook/seedsync/src/python
poetry run pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Test Types

**Unit Tests (Angular):**
- **Scope**: Individual components, services, pipes
- **Location**: `/Users/julianamacbook/seedsync/src/app/tests/unittests/`
- **Approach**: TestBed-based tests with mocked dependencies
- **Coverage**:
  - Component logic: render, event handlers, state changes
  - Service methods: data transformation, error handling
  - Pipes: format transformations

Example:
```typescript
describe("FileComponent", () => {
    it("should mark file as selected when checkbox is checked", () => {
        fileSelectionService.selectFile("test-file.mkv");
        expect(component.isSelected()).toBe(true);
    });
});
```

**Unit Tests (Python):**
- **Scope**: Individual classes and functions
- **Location**: `/Users/julianamacbook/seedsync/src/python/tests/integration/`
  (named "integration" but tests individual handlers)
- **Approach**: unittest.TestCase with real WebApp and mocked controller
- **Coverage**: HTTP endpoints, handler logic, data transformation

Example from test_status.py:
```python
class TestStatusHandler(BaseTestWebApp):
    def test_status(self):
        resp = self.test_app.get("/server/status")
        self.assertEqual(200, resp.status_int)
        json_dict = json.loads(str(resp.html))
        self.assertEqual(True, json_dict["server"]["up"])
```

**Integration Tests:**
- Not explicitly separated in this codebase
- Web handler tests use real WebApp instance with mocked controller

**E2E Tests (Playwright):**
- **Scope**: Full user workflows across UI
- **Location**:
  - Angular E2E: `/Users/julianamacbook/seedsync/src/angular/e2e/`
  - Main E2E: `/Users/julianamacbook/seedsync/src/e2e/tests/`
- **Approach**: Page Object Model (app.ts, dashboard.page.ts, etc.)
- **Coverage**:
  - Navigation and page loads
  - User interactions (clicks, form submissions)
  - Data display and updates

Example from e2e tests:
```typescript
test('should have all the sidebar items', async ({ page }) => {
    const app = new App(page);
    const items = await app.getSidebarItems();
    expect(items).toEqual([
        'Dashboard',
        'Settings',
        'AutoQueue',
        'Logs',
        'About',
        'Restart'
    ]);
});
```

## Common Patterns

**Async Testing (Angular/Jasmine):**

Using `fakeAsync()` and `tick()` to control timing:
```typescript
it("should send correct status on event", fakeAsync(() => {
    let count = 0;
    let latestStatus: ServerStatus = null;

    serverStatusService.status.subscribe({
        next: status => {
            count++;
            latestStatus = status;
        }
    });

    // Initial status
    tick();
    expect(count).toBe(1);
    expect(latestStatus.server.up).toBe(false);

    // Send new status
    const statusJson = {...};
    serverStatusService.notifyEvent("status", JSON.stringify(statusJson));
    tick();

    // Verify new status
    expect(count).toBe(2);
    expect(latestStatus.server.up).toBe(true);
}));
```

**HTTP Testing Pattern:**
```typescript
it("should send http GET on sendRequest", fakeAsync(() => {
    restService.sendRequest("/server/request").subscribe({
        next: reaction => {
            expect(reaction.success).toBe(true);
        }
    });

    // Expect the HTTP call and respond
    httpMock.expectOne("/server/request").flush("success");

    // Verify no outstanding requests
    httpMock.verify();
}));
```

**Error Testing (Angular):**
```typescript
it("should get error message on sendRequest error", fakeAsync(() => {
    restService.sendRequest("/server/request").subscribe({
        next: reaction => {
            expect(reaction.success).toBe(false);
            expect(reaction.errorMessage).toBe("Not found");
        }
    });

    httpMock.expectOne("/server/request").flush(
        "Not found",
        {status: 404, statusText: "Not Found"}
    );

    httpMock.verify();
}));
```

**Component Testing Pattern:**
```typescript
beforeEach(async () => {
    mockConfirmModalService = jasmine.createSpyObj(
        "ConfirmModalService",
        ["confirm"]
    );
    mockConfirmModalService.confirm.and.returnValue(Promise.resolve(true));

    await TestBed.configureTestingModule({
        imports: [FileComponent],
        providers: [
            FileSelectionService,
            {provide: ConfirmModalService, useValue: mockConfirmModalService}
        ]
    })
    .overrideTemplate(FileComponent, `<div>...</div>`)
    .compileComponents();

    fileSelectionService = TestBed.inject(FileSelectionService);
    fixture = TestBed.createComponent(FileComponent);
    component = fixture.componentInstance;
});

it("should call confirm modal on delete", async () => {
    component.file = testFile;
    fixture.detectChanges();

    component.deleteLocalEvent.emit(component.file);

    expect(mockConfirmModalService.confirm).toHaveBeenCalled();
});
```

**Python Web Testing Pattern:**
```python
class TestStatusHandler(BaseTestWebApp):
    def test_status_endpoint(self):
        # Send HTTP request
        resp = self.test_app.get("/server/status")

        # Assert response
        self.assertEqual(200, resp.status_int)

        # Parse and validate JSON
        json_dict = json.loads(str(resp.html))
        self.assertEqual(True, json_dict["server"]["up"])
```

**Playwright E2E Pattern:**
```typescript
test('should navigate to page', async ({ page }) => {
    const app = new App(page);

    // Navigate to app
    await app.navigateTo();

    // Perform actions
    await app.clickSidebar("Dashboard");

    // Assert results
    const title = await app.getPageTitle();
    expect(title).toBe("Dashboard");
});
```

## Test Execution

**Angular Unit Tests:**
```bash
cd /Users/julianamacbook/seedsync/src/angular
npm run test                          # Watch mode
npm run test -- --browsers=Chrome    # Specific browser
npm run test -- --watch=false         # Single run for CI
```

**Python Unit Tests:**
```bash
cd /Users/julianamacbook/seedsync/src/python
poetry run pytest                     # All tests
poetry run pytest tests/integration/test_web/test_handler/test_status.py  # Specific file
poetry run pytest -v                  # Verbose output
```

**E2E Tests:**
```bash
# Angular E2E
cd /Users/julianamacbook/seedsync/src/angular
npm run e2e

# Main E2E (requires app running at localhost:8800 or APP_BASE_URL)
cd /Users/julianamacbook/seedsync/src/e2e
npm test
npm test -- --headed           # Show browser
npm test -- tests/app.spec.ts  # Specific test
```

**Docker-based test execution (from Makefile):**
```bash
make run-tests-python           # Python unit tests
make run-tests-angular          # Angular unit tests
make run-tests-e2e              # E2E tests
```

## Known Testing Gaps

**Unit Test Coverage:**
- Component integration with services tested but not comprehensively
- Some edge cases in pipes (eta.pipe.ts) may lack coverage
- Error recovery paths may have limited tests

**E2E Test Coverage:**
- Core workflows covered (dashboard, settings, file operations)
- Some error scenarios and edge cases not explicitly tested
- Performance testing not included

**Python Test Coverage:**
- Handler endpoints tested
- LFTP integration tests basic scenarios
- Some controller logic paths may lack tests

---

*Testing analysis: 2026-02-03*
