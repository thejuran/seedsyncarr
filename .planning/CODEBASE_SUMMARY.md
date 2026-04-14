# SeedSync Codebase Summary & Navigation

## Project Overview

**SeedSync** is an automated file synchronization and queuing system with:
- Python backend handling file operations, transfers, and orchestration
- Angular TypeScript frontend providing web UI
- Clean layered architecture with zero circular dependencies
- Comprehensive test coverage (90+ test files)

---

## The 30-Second Overview

### What It Does
1. **Scans** remote/local filesystems for new content
2. **Models** file hierarchies with change detection
3. **Queues** files for processing
4. **Transfers** files via LFTP
5. **Extracts** archives automatically
6. **Reports** status via REST API and WebSocket streams

### How It's Organized
```
Backend (Python)
├── Utilities (common/)
├── Scanning (system/, ssh/)
├── Data Model (model/)
├── Business Logic (controller/)
└── API (web/)

Frontend (TypeScript/Angular)
├── Pages (pages/)
├── Services (services/)
└── Utilities (common/)
```

### Key Insight
- **Never edit a module without understanding what imports it** (see DEPENDENCY_MAP.md)
- **Test-driven structure:** Mirror directory structure in tests/
- **Layered dependencies:** No circular imports allowed

---

## File Structure at a Glance

### Python Backend (74 source files)

**Foundation Layer** (imports nothing internally)
- `common/` (13) - Logging, config, status, jobs, errors
- `system/` (3) - File system scanning
- `ssh/` (2) - Remote access
- `lftp/` (4) - File transfer protocol

**Data Layer**
- `model/` (4) - File hierarchy representation

**Logic Layer**
- `controller/` (22) - Business logic, orchestration
- `web/handler/` (9) - REST/WebSocket endpoints
- `web/serialize/` (6) - Response serialization

**Application**
- `seedsync.py` - Main entry point
- `scan_fs.py` - Utility scanner

### Angular Frontend (102 source files)

**Pages** (12 components)
- `main/` - App shell & header
- `files/` - File management UI
- `logs/` - Log viewer
- `settings/` - Configuration
- `about/` - About page

**Services** (30 services)
- Base services - HTTP, WebSocket abstractions
- Domain services - Business logic by feature
- Utility services - Notifications, storage, etc.

**Common**
- Directives, pipes, models, utilities

---

## The Mental Model

### Backend Flow
```
User Action (frontend)
  ↓ HTTP/WebSocket
REST API Handler (web/handler/*)
  ↓
Controller Method (controller/controller.py)
  ↓
Manager Classes (lftp_manager, scan_manager, etc.)
  ↓
Core Modules (model, system, ssh, lftp)
  ↓
External Systems (filesystem, remote server, LFTP)
  ↓ Status/Result
WebSocket Stream (web/stream_*.py)
  ↓ JSON over WebSocket
Frontend Service
  ↓ Observable update
Component Binding
  ↓
Template Render
```

### Key Components

| Component | What It Does | Example Files |
|-----------|-------------|----------------|
| **common/** | Shared foundation | config, logging, job scheduling |
| **model/** | File/folder representation | File, Model, Diff classes |
| **controller/** | Orchestrates operations | Scan, transfer, delete workflows |
| **lftp/** | File transfer protocol | Job parsing, status tracking |
| **web/** | REST API + WebSockets | Endpoints, serialization, streaming |
| **system/** | OS-level operations | File scanning, path traversal |
| **ssh/** | Remote access | SFTP copy, remote execution |

---

## Common Questions & Answers

### "Where do I add a new feature?"

**Answer depends on feature type:**

**REST Endpoint?**
1. Add handler: `src/python/web/handler/feature_name.py`
2. Register route: `web_app_builder.py`
3. Add service: `src/angular/src/app/services/category/`
4. Add component: uses service above

**Business Logic?**
1. Identify logical manager: scan, lftp, file_operations, etc.
2. Add method to manager class
3. Call from controller.py
4. Expose via web handler

**UI Page?**
1. Create component: `src/angular/src/app/pages/name/`
2. Add to routing: `routes.ts`
3. Create services it needs
4. Connect to backend via REST

### "How do I understand a module?"

**Steps:**
1. Read module's `__init__.py` - shows public API
2. Check what imports it - understand dependencies
3. Check what it imports - understand uses
4. Look at tests - understand behavior
5. Read main classes - understand implementation

**Example for `model/`:**
- `__init__.py` exports: Model, File, Diff
- Imported by: controller, web, extract
- Imports: common only
- Tests: test_model/, test_file.py, test_diff.py

### "How do I debug an issue?"

**Depends on where the bug is:**

**Backend:**
1. Check logs via `logger.debug()` statements
2. Add breakpoint in IDE
3. Look at status via `/api/status` endpoint
4. Check database/persistence layer

**Frontend:**
1. Browser DevTools → Console tab
2. Check Network tab for API calls
3. Look at service state via debugger
4. Check localStorage for persisted state

### "How do I add a test?"

**For Python:**
1. Create `test_X.py` in `tests/unittests/{module}/`
2. Use pytest fixtures from `conftest.py`
3. Test isolated behavior
4. Run via Makefile: `make test`

**For TypeScript:**
1. Create `X.spec.ts` next to source file
2. Use Angular testing utilities
3. Mock dependencies using test doubles
4. Run via: `ng test`

### "What's the test structure?"

```
tests/
├── unittests/         ← Individual component tests
│   └── test_{module}/
├── integration/       ← Multi-component tests
│   └── test_{module}/
└── conftest.py        ← Shared fixtures & config
```

**Rule of thumb:**
- Unit test: One class, mocked dependencies
- Integration test: Multiple classes, real dependencies where possible
- E2E test: Full system, everything real

---

## Code Navigation Tricks

### Finding Code by Grep

**Find where Status is used:**
```bash
grep -r "from common import status" src/python/
```

**Find all REST endpoints:**
```bash
grep -r "def handle_" src/python/web/handler/
```

**Find all service instantiations (Angular):**
```bash
grep -r "constructor.*Service" src/angular/src/app/
```

### Using IDE Features

**Go to Definition:**
- Python: Jump to class/function definition
- TypeScript: Jump to interface/class definition

**Find References:**
- Shows everywhere a class/function is used
- Perfect for understanding impact of changes

**Find in Files:**
- Search for specific patterns
- Use regex for complex queries

---

## Dependency Reference

### What Each Module Depends On

```
seedsync.py
  ├── common (config, status, logging)
  ├── controller (main orchestration)
  └── web (REST API)

web/
  ├── common (logging, status)
  ├── controller (for state)
  └── model (for serialization)

controller/
  ├── common (logging, jobs)
  ├── model (file representation)
  ├── lftp (transfers)
  ├── system (scanning)
  ├── ssh (remote access)
  └── submodules (scan, extract, delete)

model/
  └── common (only)

lftp/
  └── common (only)

ssh/
  └── common (only)

system/
  └── (none - leaf)

common/
  └── (none - foundation)
```

### What Each Module Is Used By

```
common/
  ← Everything (foundation)

system/
  ← controller/scan, model_builder

ssh/
  ← controller/scan/remote, controller/delete

lftp/
  ← controller/lftp_manager, model_builder

model/
  ← controller, web, extract, auto_queue

controller/
  ← seedsync, web, auto_queue

web/
  ← seedsync (main API)
```

---

## Performance Considerations

### Backend Bottlenecks
- **Filesystem scanning**: Handled via threading
- **Large file lists**: Model is memory-optimized
- **File transfers**: Parallelized via LFTP

### Frontend Bottlenecks
- **Large file lists**: Use virtual scrolling
- **WebSocket updates**: Batched and throttled
- **Change detection**: OnPush strategy used

### Optimization Tips
- Don't load entire model if not needed
- Cache frequently accessed data
- Use pagination for large result sets
- Throttle WebSocket updates

---

## Testing Checklist

Before committing:
- [ ] Unit tests pass: `make test`
- [ ] New code has tests
- [ ] Integration tests pass (if applicable)
- [ ] No circular imports
- [ ] Type checking passes
- [ ] Code follows style guide
- [ ] Docstrings/comments added

---

## Common Patterns

### Creating a New Service (Angular)

```typescript
import { Injectable } from '@angular/core';
import { RestService } from '../utils/rest.service';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class NewService {
  private state$ = new BehaviorSubject(initialState);
  public state = this.state$.asObservable();

  constructor(private rest: RestService) {}

  loadData(): Observable<any> {
    return this.rest.get('/api/endpoint');
  }
}
```

### Creating a Handler (Python)

```python
from web.handler import Handler
from common import status

class NewHandler(Handler):
    def handle_request(self, request_data):
        """Process request and return response."""
        result = self.controller.do_something()
        return {
            'success': True,
            'data': result
        }
```

### Creating a Manager (Python)

```python
from common import logging_config

class NewManager:
    def __init__(self, controller):
        self.controller = controller
        self.logger = logging_config.get_logger(__name__)

    def do_work(self):
        """Orchestrate some operation."""
        self.logger.info("Starting work")
        # Implementation
        self.logger.info("Work complete")
```

---

## Key Files You'll Modify Often

### Backend
- `src/python/controller/controller.py` - Core logic
- `src/python/web/handler/*.py` - API endpoints
- `src/python/web/serialize/*.py` - Response formatting
- `src/python/model/model.py` - Data representation

### Frontend
- `src/angular/src/app/services/*.service.ts` - Data fetching
- `src/angular/src/app/pages/*/*.component.ts` - UI logic
- `src/angular/src/app/routes.ts` - Navigation

### Tests
- `tests/unittests/test_*.py` - Unit test files
- `src/angular/src/app/tests/` - Angular test files

---

## Getting Unstuck

### "Module not found"
1. Check if file exists at path
2. Verify `__init__.py` exports the symbol
3. Check for typos in import statement
4. Check for circular imports

### "Test fails unexpectedly"
1. Run single test with `-v` flag for verbosity
2. Add `print()` or `console.log()` statements
3. Check test fixtures in `conftest.py`
4. Compare with passing tests in same suite

### "API endpoint not working"
1. Check handler exists: `src/python/web/handler/`
2. Verify route registered in `web_app_builder.py`
3. Check service method in Angular matches endpoint
4. Look at browser Network tab for HTTP errors

### "WebSocket not updating"
1. Check `web/stream_*.py` for the handler
2. Verify event is triggered in controller
3. Check frontend subscription is active
4. Look at browser console for connection errors

---

## Reference Documents

Created in `.planning/` directory:

1. **`DEPENDENCY_MAP.md`** - Detailed dependency documentation
   - Module breakdown
   - What imports what
   - Architecture patterns
   - How to navigate the code

2. **`DEPENDENCY_GRAPH.txt`** - Visual dependency tree
   - ASCII diagrams
   - Import relationships
   - Module hierarchy
   - Critical paths

3. **`QUICK_REFERENCE.md`** - Quick lookup guide
   - File locations
   - Common tasks
   - Finding things
   - Common patterns

4. **`CODEBASE_SUMMARY.md`** - This file
   - Overview
   - Mental models
   - Q&A
   - Getting unstuck

---

## Next Steps

### To Get Started
1. Read this summary (you're here!)
2. Check `QUICK_REFERENCE.md` for file locations
3. Look at `DEPENDENCY_MAP.md` for detailed architecture
4. Read `DEPENDENCY_GRAPH.txt` for visual overview

### To Add a Feature
1. Check `QUICK_REFERENCE.md` → "Adding" section
2. Look at similar existing code
3. Follow the same pattern
4. Add tests in parallel
5. Run all tests before committing

### To Fix a Bug
1. Find the buggy code (use grep/IDE)
2. Understand what calls it (find references)
3. Add test that reproduces bug
4. Fix the bug
5. Run all related tests
6. Commit with clear message

---

## Stats at a Glance

| Metric | Count |
|--------|-------|
| Python source files | 74 |
| TypeScript source files | 102 |
| Test files | 90+ |
| Lines of Python code | ~15,000 |
| Lines of TypeScript code | ~3,000 |
| REST endpoints | ~15 |
| WebSocket streams | ~5 |
| Angular services | 30 |
| Angular components | 24 |
| Circular dependencies | 0 ✓ |

---

## Architecture Scorecard

| Aspect | Score | Notes |
|--------|-------|-------|
| Modularity | ⭐⭐⭐⭐⭐ | Clear separation of concerns |
| Testability | ⭐⭐⭐⭐⭐ | Comprehensive test coverage |
| Dependencies | ⭐⭐⭐⭐⭐ | Zero circular dependencies |
| Documentation | ⭐⭐⭐⭐ | Good, these docs help |
| Code Quality | ⭐⭐⭐⭐ | Consistent patterns |
| Performance | ⭐⭐⭐⭐ | Optimized hot paths |

---

## Pro Tips

1. **Always check tests first** when learning a module
2. **Use grep + IDE** to find patterns quickly
3. **Trace data flow** to understand complex operations
4. **Run tests continuously** while developing
5. **Keep change scope small** - easier to test and review
6. **Follow existing patterns** - consistency matters
7. **Document assumptions** - helps future readers
8. **Commit frequently** - easier to revert if needed

---

Generated: 2026-03-28
