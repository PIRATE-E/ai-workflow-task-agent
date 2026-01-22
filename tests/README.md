# 🧪 Tests Directory - Complete Guide

> **Last Updated:** January 1, 2026  
> **Status:** ✅ All imports fixed, redundant tests removed  
> **Total Tests:** 74 files (42 with 'src' imports, all fixed)

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Import Fix](#import-fix)
5. [Test Categories](#test-categories)
6. [Writing New Tests](#writing-new-tests)

---

## Overview

This directory contains all test files for the AI-Agent-Workflow project. All tests have been fixed to work from:
- ✅ **PyCharm** (Run Configuration)
- ✅ **Terminal** (python tests/test_name.py)
- ✅ **Project Root** (python tests/...)
- ✅ **Tests Directory** (cd tests; python test_name.py)

---

## Running Tests

### **From Terminal (Any Location)**

```powershell
# Run a specific test
python tests/test_browser_use/test_browser_comprehensive.py

# Run with pytest
pytest tests/test_browser_use/test_browser_comprehensive.py -v

# Run all tests in a directory
pytest tests/test_browser_use/ -v

# Run all tests
pytest tests/ -v
```

### **From PyCharm**

Right-click on any test file → "Run 'test_name'"

---

## Test Structure

```
tests/
├── test_utils.py                    # Shared utilities for all tests
├── fix_test_imports.py              # Automated import fixer (already applied)
│
├── test_browser_use/                # Browser automation tests
│   ├── __init__.py
│   ├── browser_use_test.py          # Simple browser test
│   └── test_browser_comprehensive.py # Complete test suite
│
├── test_agent_workflow/             # Agent workflow tests
│   ├── demo_workflow.py
│   ├── real_integration_test.py
│   ├── test_complete_workflow.py
│   └── ...
│
├── slashcommands/                   # Slash command tests
│   ├── test_commands.py
│   ├── test_handlers.py
│   └── ...
│
├── event_listener/                  # Event system tests
│   ├── test_event_listener_realistic.py
│   ├── test_exit_flag_behavior.py
│   └── ...
│
├── integration/                     # Integration tests
├── unit/                            # Unit tests
├── error_handling/                  # Error handling tests
├── serialization/                   # Serialization tests
└── model_manager_tests/             # Model manager tests
```

---

## Import Fix

### **Problem (Before Fix)**

```python
# ❌ This failed when run from terminal
from src.config import settings
# ModuleNotFoundError: No module named 'src'
```

### **Solution (After Fix)**

All test files now have this at the top:

```python
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[N]  # N depends on depth
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now this works everywhere! ✅
from src.config import settings
```

### **Automatic Fixing**

If you create a new test that imports from `src`, run:

```powershell
cd tests
python fix_test_imports.py --apply
```

This will automatically add proper path setup to all test files!

---

## Test Categories

### **1. Browser Tests** (`test_browser_use/`)

**Purpose:** Test browser automation functionality

**Files:**
- `browser_use_test.py` - Simple navigation test
- `test_browser_comprehensive.py` - Complete test suite with pytest integration

**Running:**
```powershell
python tests/test_browser_use/test_browser_comprehensive.py
```

**Test Coverage:**
- ✅ Import verification
- ✅ Function signatures
- ✅ Configuration settings
- ✅ Integration (manual only)

---

### **2. Agent Workflow Tests** (`test_agent_workflow/`)

**Purpose:** Test LangGraph agent orchestration

**Key Files:**
- `test_complete_workflow.py` - Full workflow test
- `test_hierarchical_agent.py` - Multi-agent tests
- `real_integration_test.py` - Real integration scenarios

**Status:** ✅ All imports fixed

---

### **3. Slash Command Tests** (`slashcommands/`)

**Purpose:** Test `/help`, `/clear`, `/agent` etc.

**Key Files:**
- `test_commands.py` - Command parsing
- `test_handlers.py` - Command execution
- `test_full_flow.py` - End-to-end flow

**Status:** ✅ All imports fixed

---

### **4. Event Listener Tests** (`event_listener/`)

**Purpose:** Test event system (exit listeners, variable watchers)

**Key Files:**
- `test_event_listener_realistic.py` - Realistic scenarios
- `test_exit_flag_behavior.py` - Exit handling
- `test_two_emit_exit_system.py` - Two-emit pattern

**Status:** ✅ All imports fixed

---

### **5. Integration Tests** (`integration/`)

**Purpose:** Test component integration

**Status:** ✅ All imports fixed

---

### **6. Unit Tests** (`unit/`)

**Purpose:** Isolated unit tests

**Status:** ⚠️ No 'src' imports (self-contained)

---

### **7. Error Handling Tests** (`error_handling/`)

**Purpose:** Test error routing and logging

**Status:** Mixed (some fixed, some self-contained)

---

### **8. Serialization Tests** (`serialization/`)

**Purpose:** Test Rich object serialization

**Status:** ⚠️ Self-contained (no 'src' imports)

---

### **9. Model Manager Tests** (`model_manager_tests/`)

**Purpose:** Test model loading and switching

**Status:** ⚠️ Self-contained

---

## Writing New Tests

### **Template for New Test File**

```python
"""
Test description here.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]  # Adjust number based on depth
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest


class TestYourFeature:
    """Test class for your feature."""
    
    def test_something(self):
        """Test description."""
        from src.your_module import your_function
        
        result = your_function()
        assert result == expected_value


if __name__ == "__main__":
    """Manual test runner (works without pytest)."""
    print("Running tests...")
    
    test = TestYourFeature()
    test.test_something()
    
    print("✅ All tests passed!")
```

### **Depth Calculation (parents[N])**

```
tests/test_name.py                    → parents[1]  (tests → project_root)
tests/subfolder/test_name.py          → parents[2]  (subfolder → tests → project_root)
tests/sub1/sub2/test_name.py          → parents[3]  (sub2 → sub1 → tests → project_root)
```

### **Using pytest**

```python
import pytest


# Simple test
def test_basic():
    assert 1 + 1 == 2


# Test with setup/teardown
@pytest.fixture
def setup_data():
    # Setup
    data = {"key": "value"}
    yield data
    # Teardown
    del data


def test_with_fixture(setup_data):
    assert setup_data["key"] == "value"


# Skip tests conditionally
@pytest.mark.skip(reason="Requires external service")
def test_external_api():
    pass


# Mark as integration test
@pytest.mark.integration
def test_full_integration():
    pass
```

---

## Summary of Changes

### **✅ Fixed (42 files)**

All test files with `from src` imports now work from terminal and PyCharm:
- test_browser_use (2 files)
- test_agent_workflow (8 files)
- slashcommands (5 files)
- event_listener (8 files)
- integration (1 file)
- error_handling (1 file)
- And 17 more root-level test files

### **🗑️ Deleted (5 files)**

Removed redundant browser tests:
- `actual_usage.py` - Duplicate of browser_use_test.py
- `browser_use_fun.py` - Duplicate functionality
- `example_usage.py` - Just examples, not real tests
- `headless_mode_test.py` - Covered by comprehensive test
- `implementation.py` - Covered by comprehensive test

### **➕ Created (3 files)**

- `test_utils.py` - Shared test utilities
- `fix_test_imports.py` - Automated import fixer
- `test_browser_comprehensive.py` - Complete browser test suite
- `README.md` - This file

---

## Troubleshooting

### **ImportError: No module named 'src'**

**Solution:** Run the import fixer:
```powershell
cd tests
python fix_test_imports.py --apply
```

### **Test works in PyCharm but not terminal**

**Cause:** PyCharm adds project root to path automatically, terminal doesn't.

**Solution:** Ensure your test file has the path setup code at the top (see template above).

### **Can't find project root**

**Error:** `Cannot find 'src' directory`

**Solution:** Check the `parents[N]` number matches your file's depth:
```python
# If your test is at tests/my_test.py
project_root = Path(__file__).resolve().parents[1]  # ✅ Correct

# If your test is at tests/subfolder/my_test.py
project_root = Path(__file__).resolve().parents[2]  # ✅ Correct
```

---

## Best Practices

1. ✅ **Always use path setup** for tests that import from `src`
2. ✅ **Use pytest for new tests** (better organization and features)
3. ✅ **Add manual runner** (`if __name__ == "__main__"`) for quick testing
4. ✅ **Skip heavy tests** (browser, external APIs) by default
5. ✅ **Group related tests** in classes
6. ✅ **Use descriptive names** (`test_browser_navigation_works` not `test1`)
7. ✅ **Add docstrings** to explain what the test does

---

## Quick Reference

```powershell
# Run single test
python tests/test_name.py

# Run with pytest
pytest tests/test_name.py -v

# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_name.py::TestClassName -v

# Run specific test method
pytest tests/test_name.py::TestClassName::test_method -v

# Fix imports in all tests
python tests/fix_test_imports.py --apply

# Create new test (use template above)
# Don't forget to add path setup!
```

---

**✅ All tests are now ready to use from anywhere!**

*Last verified: January 1, 2026*

