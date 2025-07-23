# Test Suite for LangGraph Chatbot

This directory contains all tests for the LangGraph Chatbot project, organized by category.

## 📁 Directory Structure

```
tests/
├── README.md                           # This file
├── run_tests.py                        # Main test runner
├── __init__.py                         # Tests package init
│
├── error_handling/                     # Error handling and logging tests
│   ├── __init__.py
│   ├── run_all_tests.py               # Error handling test runner
│   ├── test_socket_connection.py      # Basic socket connection tests
│   ├── test_socket_manager.py         # Socket manager singleton tests
│   └── test_logging_system.py         # Complete logging system tests
│
└── unit/                              # Unit tests
    ├── __init__.py
    └── test_class_examples.py          # OOP concepts and examples
```

## 🚀 Quick Start

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Categories

#### Unit Tests (No prerequisites)
```bash
python tests/run_tests.py
# Choose option 1
```

#### Error Handling Tests (Requires log server)
```bash
# Terminal 1: Start log server
python utils/error_transfer.py

# Terminal 2: Run tests
python tests/run_tests.py
# Choose option 2
```

## 📋 Test Categories

### 1. Unit Tests (`unit/`)
- **Purpose**: Test individual components and concepts
- **Prerequisites**: None
- **Files**:
  - `test_class_examples.py`: Demonstrates OOP concepts (classes, objects, singleton pattern)

### 2. Error Handling Tests (`error_handling/`)
- **Purpose**: Test logging system, socket connections, and error handling
- **Prerequisites**: Log server must be running (`python utils/error_transfer.py`)
- **Files**:
  - `test_socket_connection.py`: Tests basic socket functionality
  - `test_socket_manager.py`: Tests singleton pattern and connection management
  - `test_logging_system.py`: Tests complete logging workflow

## 🔧 Prerequisites

### For Unit Tests
- No special requirements
- Can run anytime

### For Error Handling Tests

**🚀 NEW: Automatic Subprocess Management**
- Log server now starts automatically when needed
- No need to manually run `utils/error_transfer.py`
- Automatic cleanup when application exits

**Manual Testing (Optional)**:
1. **Start the log server manually** (if you want to see logs in separate terminal):
   ```bash
   python utils/error_transfer.py
   ```
2. **Check configuration** in `config.py`:
   - `ENABLE_SOCKET_LOGGING = True`
   - `SOCKET_HOST = "localhost"`
   - `SOCKET_PORT = 5390`

## 📊 Understanding Test Results

### Success Indicators
- ✅ **PASS** - Test completed successfully
- 🎉 **All tests passed** - Everything working correctly

### Failure Indicators
- ❌ **FAIL** - Test failed (check error messages)
- ⚠️ **Some tests failed** - Review output for details

### Common Issues
- **Connection refused**: Log server not running
- **Import errors**: Run from project root directory
- **Socket timeout**: Check host/port configuration

## 🧪 Individual Test Files

### Running Individual Tests
```bash
# Run a specific test file
python tests/error_handling/test_socket_manager.py
python tests/unit/test_class_examples.py
```

### Test File Descriptions

#### `test_socket_connection.py`
- Tests basic socket creation and connection
- Tests error scenarios (invalid host, port, etc.)
- Tests message format handling
- Tests connection cleanup

#### `test_socket_manager.py`
- Tests singleton pattern implementation
- Tests connection sharing between modules
- Tests error handling and recovery
- Tests connection lifecycle management

#### `test_logging_system.py`
- Tests complete logging workflow
- Tests message sending and receiving
- Tests various message formats
- Tests concurrent logging scenarios

#### `test_class_examples.py`
- Educational examples of OOP concepts
- Demonstrates regular vs singleton classes
- Shows class vs instance variables
- Explains different method types

## 🎯 What Each Test Validates

### Socket Manager Tests
- ✅ Only one connection is created (singleton)
- ✅ Connection is shared between modules
- ✅ Graceful error handling
- ✅ Proper resource cleanup

### Logging System Tests
- ✅ Messages are sent successfully
- ✅ Server receives messages correctly
- ✅ Various message formats work
- ✅ Error scenarios are handled

### Class Concept Tests
- ✅ Understanding of OOP principles
- ✅ Singleton pattern implementation
- ✅ Class vs instance variables
- ✅ Method types and usage

## 🔍 Troubleshooting

### Test Failures
1. **Read error messages carefully**
2. **Check prerequisites** (especially log server)
3. **Verify configuration** in `config.py`
4. **Run tests individually** to isolate issues

### Common Solutions
- **"Connection refused"**: Start log server first
- **"Module not found"**: Run from project root
- **"Permission denied"**: Check file permissions
- **"Port in use"**: Stop other programs using the port

## 📚 Learning Resources

The tests are designed to be educational. Study the code to understand:
- **Singleton Pattern**: How to ensure only one instance exists
- **Socket Programming**: How client-server communication works
- **Error Handling**: How to gracefully handle failures
- **Test Organization**: How to structure test suites

## 🤝 Contributing

When adding new tests:
1. **Choose the right category** (unit, error_handling, etc.)
2. **Follow naming convention**: `test_*.py`
3. **Add docstrings** explaining what the test does
4. **Update this README** if adding new categories
5. **Test your tests** before committing

## 📞 Support

If tests fail consistently:
1. Check the main project README
2. Verify your environment setup
3. Review configuration files
4. Check for conflicting processes on socket ports