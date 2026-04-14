# SeedSync Codebase Quick Reference

## File Locations & Key Files

### Python Backend

**Entry Points:**
- `src/python/seedsync.py` - Main application start
- `src/python/scan_fs.py` - Filesystem scanner utility
- `src/python/tests/conftest.py` - Test configuration

**Core Modules (alphabetical):**
- `src/python/common/` - Shared utilities, config, status, jobs
- `src/python/controller/` - Business logic orchestration
- `src/python/lftp/` - File transfer protocol handling
- `src/python/model/` - Data models (files, folders, diffs)
- `src/python/ssh/` - Remote access over SSH/SFTP
- `src/python/system/` - OS-level file operations
- `src/python/web/` - REST API and WebSocket handlers

### Angular Frontend

**Entry Points:**
- `src/angular/src/main.ts` - Bootstrap application
- `src/angular/src/app.config.ts` - App configuration
- `src/angular/src/routes.ts` - Routing definition
- `src/angular/src/index.html` - HTML shell

**Feature Modules:**
- `src/angular/src/app/pages/` - Page components
- `src/angular/src/app/services/` - Business logic services
- `src/angular/src/app/common/` - Shared components & utilities
- `src/angular/src/app/tests/` - Unit tests & mocks

---

## Module Import Map

### Quick Dependency Lookups

**What does `seedsync.py` import?**
```
common, controller, controller.webhook_manager, web
```

**What imports controller?**
```
seedsync.py, web (handlers), auto_queue
```

**What imports model?**
```
controller, web/handlers, web/serialize
```

**What imports common?**
```
Every other module (foundation layer)
```

---

## File Type & Location Guide

### Finding Code by Purpose

| Purpose | Location | Examples |
|---------|----------|----------|
| Application startup | `src/python/seedsync.py` | initialization, config loading |
| REST endpoints | `src/python/web/handler/*.py` | `/api/*` handlers |
| WebSocket streaming | `src/python/web/stream_*.py` | status updates, logs |
| Business logic | `src/python/controller/` | orchestration, workflow |
| File operations | `src/python/model/` | file structure, diffs |
| File transfers | `src/python/lftp/` | protocol handling |
| Remote access | `src/python/ssh/` | SFTP operations |
| File scanning | `src/python/system/` | filesystem traversal |
| Utilities | `src/python/common/` | logging, config, jobs |
| | | |
| Frontend UI | `src/angular/src/app/pages/` | components/templates |
| Frontend logic | `src/angular/src/app/services/` | data fetching, state |
| Test doubles | `src/angular/src/app/tests/mocks/` | mock services |

### Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| `angular.json` | Angular build config | `src/angular/` |
| `tsconfig.json` | TypeScript config | `src/angular/` |
| `karma.conf.js` | Test runner | `src/angular/` |
| `package.json` | npm dependencies | `src/angular/` |
| `Makefile` | Build commands | root |
| `.env.*` | Environment vars | root (if present) |

---

## Common Import Patterns

### Python Imports

**Importing from common:**
```python
from common import config, status, job
from common.error import ConfigError
```

**Importing from controller:**
```python
from controller import Controller
from controller.scan import ActiveScanner
from controller.extract import extract_archive
```

**Importing from model:**
```python
from model import Model
from model.file import File
from model.diff import ModelDiff
```

### TypeScript Imports

**Service injection:**
```typescript
constructor(private rest: RestService, private config: ConfigService) {}
```

**Observable subscription:**
```typescript
this.rest.get<Status>('/api/status').subscribe(...)
```

---

## How to Find Things

### "Where is the REST API for X?"
1. Check `src/angular/src/app/services/` for the service making the call
2. Look for the URL pattern (e.g., `/api/files`)
3. Find matching handler in `src/python/web/handler/`
4. Handler calls controller methods

**Example:** Finding file operations API
```
files-page.component.ts
  → file.component.ts
    → server-command.service.ts (calls /api/command)
      → src/python/web/handler/controller.py
```

### "Where is the code that handles X?"
1. Search for `X` in module `__init__.py` files
2. Check imports at top of likely files
3. Trace through class definitions

**Example:** Finding auto-queue logic
```
auto_queue.service.ts (frontend)
  → rest.service (calls /api/auto-queue)
    → src/python/web/handler/auto_queue.py (receives request)
      → src/python/controller/auto_queue.py (processes)
```

### "What tests exist for X?"
1. Look in `tests/unittests/` for unit tests
2. Look in `tests/integration/` for integration tests
3. Test filename mirrors source file: `test_X.py`

**Example:** Finding controller tests
```
src/python/controller/controller.py
  → tests/unittests/test_controller/test_controller_unit.py
  → tests/unittests/test_controller/test_controller_job.py
  → tests/integration/test_controller/test_controller.py
```

---

## Service Layer Architecture (Frontend)

### Request Flow

```
Component Event
  ↓
Service Method Call
  ↓
Rest Service (HTTP) or Base Stream Service (WebSocket)
  ↓
Backend Endpoint
  ↓
Response/Update
  ↓
Service State Update (Observable)
  ↓
Component Receives Update (Subscription)
  ↓
Template Renders
```

### Adding a New Service

1. Create file: `src/angular/src/app/services/category/new.service.ts`
2. Extend: `BaseWebService` (for HTTP) or `BaseStreamService` (for WebSocket)
3. Implement methods calling: `rest.get()`, `rest.post()`, etc.
4. Inject in components
5. Subscribe to observables in component

---

## Controller Architecture (Backend)

### Processing Flow

```
Web Handler (receives request)
  ↓
Controller Method
  ↓
Manager Classes (*_manager)
  ↓
Core Modules (model, lftp, system, ssh)
  ↓
External Tools (lftp, ssh, etc.)
  ↓
Return Result to Handler
  ↓
Serialize Response
  ↓
Send to Client
```

### Adding Business Logic

1. Identify which manager should handle it
   - `scan_manager` - scanning operations
   - `lftp_manager` - transfers
   - `file_operation_manager` - copy/delete
   - `webhook_manager` - webhooks
   - `auto_queue` - auto-queueing

2. Add method to manager class
3. Call from `controller.py` orchestrator
4. Expose via `web/handler/` endpoint
5. Add corresponding service in Angular

---

## Testing Strategy

### Unit Tests (Isolated)

**Location:** `tests/unittests/test_{module}/`

```python
# Test specific function/class in isolation
def test_job_status_parser():
    parser = JobStatusParser()
    # Test parsing logic
```

### Integration Tests (With Dependencies)

**Location:** `tests/integration/test_{module}/`

```python
# Test module with real dependencies
def test_controller_scan():
    controller = Controller(config, model)
    # Test full scanning workflow
```

### E2E Tests (Full System)

**Location:** `src/docker/test/e2e/` or `src/e2e/`

```python
# Test entire application behavior
def test_sync_workflow():
    # Start container, run sync, verify results
```

---

## Configuration & Secrets

### Backend Config

**Location:** Runtime config file (path varies)

**Common settings:**
- Server address/port
- Remote server credentials
- LFTP options
- Scan intervals
- etc.

**Loading:** `common/config.py`

### Frontend Environment

**Location:** `src/angular/src/environments/`

**Files:**
- `environment.ts` - Development
- `environment.prod.ts` - Production

**Usage:**
```typescript
import { environment } from '../../environments/environment';
const apiUrl = environment.apiUrl;
```

---

## Build & Deployment

### Build Commands

Check `Makefile` for available targets:
```bash
make build        # Build all
make test         # Run tests
make docker-build # Build Docker image
make run          # Run locally
```

### Docker Build

**Location:** `src/docker/` or root `Dockerfile`

**Process:**
1. Build Python backend
2. Build Angular frontend
3. Package in container

---

## Debug Techniques

### Backend Debugging

**Logging:**
```python
from common import logging_config
logger = logging_config.get_logger(__name__)
logger.debug("message")
```

**Status inspection:**
```python
from common import status
current_status = status.get_current()
```

### Frontend Debugging

**Browser console:**
```typescript
console.log('Debug message', data);
```

**Using logger service:**
```typescript
constructor(private logger: LoggerService) {}
// In method:
this.logger.log('message', data);
```

**Check local storage:**
```
localStorage.getItem('key')
```

---

## Common Tasks

### Adding a New API Endpoint

1. Add handler in `src/python/web/handler/{feature}.py`
2. Register route in `web_app_builder.py`
3. Add service in `src/angular/src/app/services/{category}/`
4. Call service from component
5. Add tests in `tests/unittests/test_web/`

### Adding a New File Operation

1. Add logic to `controller/file_operation_manager.py`
2. Create corresponding lftp/ssh command if needed
3. Update model after operation
4. Notify clients via WebSocket (`stream_model.py`)
5. Add test in `tests/integration/test_controller/`

### Adding a New Page

1. Create component: `src/angular/src/app/pages/{name}/{name}-page.component.ts`
2. Add to routing: `src/angular/src/app/routes.ts`
3. Create supporting services as needed
4. Add template: `{name}-page.component.html`
5. Add styles: `{name}-page.component.scss`

---

## Performance Notes

### Frontend Bottlenecks
- Large file lists (handled by virtualScrolling)
- Frequent WebSocket updates (batched)
- DOM operations (OnPush change detection)

### Backend Bottlenecks
- Filesystem scanning (threaded)
- File transfers (parallel LFTP)
- Memory with large models (monitored)

---

## Version & Compatibility

**Angular version:** Check `package.json`
**Python version:** Check `requirements.txt` or `Makefile`
**Node.js version:** Check `.nvmrc` or `package.json` engines

---

## Common Error Patterns

### ImportError (Python)
- Check that module is in `__init__.py`
- Verify relative import paths
- Check for circular imports

### Type Errors (TypeScript)
- Ensure service is injected
- Verify interfaces match API response
- Check null safety

### 404 Errors (API)
- Verify endpoint name matches handler
- Check route registration in app builder
- Ensure CORS is configured

---

## IDE Setup

### For Python
- Install: `python-lsp-server` or `pylance`
- Format: `black` (via Makefile)
- Lint: `pylint` or `flake8`

### For TypeScript
- Install: `@angular/language-service`
- Format: `prettier` (configured in project)
- Lint: `eslint` (via npm scripts)

---

## Getting Help

### Code Organization Questions
→ See `DEPENDENCY_MAP.md` for detailed module docs

### Finding Something Specific
→ See `DEPENDENCY_GRAPH.txt` for visual dependency tree

### Understanding a Module
→ Check module `__init__.py` for public API

### Understanding a Service
→ Check `constructor` for dependencies, public methods for API

---

## Quick Stats

```
Python Code:     ~74 source files, ~15,000 LOC
TypeScript Code: ~102 source files, ~3,000 LOC
Test Files:      90 Python test files
Test Coverage:   Unit + Integration + E2E
Dependencies:    Clean layered architecture, zero circular deps
```
