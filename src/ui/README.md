# 🎨 UI Package

**User Interface Components for AI-Agent-Workflow**

> Beautiful, interactive terminal UI using Rich library with structured debug messaging and error handling.

---

## 📋 **Table of Contents**

1. [Why We Need This Package](#why-we-need-this-package)
2. [Architecture Overview](#architecture-overview)
3. [Components Explained](#components-explained)
4. [Quick Start Guide](#quick-start-guide)
5. [Debug Helpers](#debug-helpers)
6. [Message Protocol](#message-protocol)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 **Why We Need This Package**

### **The Problem We Solved**

Console output can be messy:
- ❌ Plain text logs hard to read
- ❌ No structure to debug messages
- ❌ Errors lost in output flood
- ❌ No visual distinction between message types

### **What This Package Provides**

A **beautiful terminal UI** with:
- ✅ **Rich Formatting** - Colors, panels, progress bars
- ✅ **Structured Messages** - Debug protocol with metadata
- ✅ **Debug Helpers** - Easy-to-use logging functions
- ✅ **Error Handling** - Beautiful error displays
- ✅ **Message Styles** - Visual distinction (user, AI, tool)

---

## 🏗️ **Architecture Overview**

```
┌──────────────────────────────────────────────────────────┐
│                  UI PACKAGE ARCHITECTURE                  │
│             (Terminal UI Components)                      │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 1. Debug Helpers (diagnostics/debug_helpers.py)    │ │
│  │    • debug_info(), debug_warning(), debug_error()  │ │
│  │    • debug_tool_response(), debug_api_call()       │ │
│  │    • Simple wrapper for debug messaging            │ │
│  └────────────────────┬────────────────────────────────┘ │
│                       ↓                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 2. Debug Protocol (diagnostics/debug_message_*)    │ │
│  │    • DebugMessageSender - Sends structured JSON    │ │
│  │    • LogLevel, DataType, ObjectType enums          │ │
│  │    • Metadata support for rich debugging           │ │
│  └────────────────────┬────────────────────────────────┘ │
│                       ↓                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 3. Socket Connection (via settings.socket_con)     │ │
│  │    • Sends JSON to error_transfer.py subprocess    │ │
│  │    • TCP socket communication                      │ │
│  └────────────────────┬────────────────────────────────┘ │
│                       ↓                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 4. Rich Display (error_transfer.py subprocess)     │ │
│  │    • Receives JSON messages                        │ │
│  │    • Displays in Rich console (separate window)    │ │
│  │    • Beautiful panels, colors, formatting          │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 5. Message Styles (print_message_style.py)         │ │
│  │    • print_message(msg, sender="user"|"ai"|"tool") │ │
│  │    • Displays in main console with icons           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 🧩 **Components Explained**

### **1. Debug Helpers (`diagnostics/debug_helpers.py`)**

**What it does:** Convenience functions for sending debug messages.

**Simple API:**
```python
from src.ui.diagnostics.debug_helpers import (
    debug_info,
    debug_warning,
    debug_error,
    debug_critical
)

# Send messages with different levels
debug_info("APP • STARTED", "Application initialized")
debug_warning("API • SLOW", "API took 5 seconds", {"duration": 5.0})
debug_error("TOOL • FAILED", "Tool crashed", {"error": str(e)})
debug_critical("SYSTEM • FAILURE", "Critical error!")
```

**Specialized Functions:**
```python
# Tool responses
debug_tool_response(
    tool_name="google_search",
    status="success",
    response_summary="Found 10 results",
    execution_time=1.2,
    metadata={"query": "Python"}
)

# API calls
debug_api_call(
    api_name="OpenAI",
    operation="chat_completion",
    status="completed",
    duration=2.5,
    metadata={"model": "gpt-4"}
)

# Performance warnings
debug_performance_warning(
    operation="database_query",
    duration=5.2,
    threshold=2.0,
    context="User search",
    metadata={"query": "SELECT *"}
)

# Error logs
debug_error_log(
    error_type="ValueError",
    error_message="Invalid input",
    context="Parameter validation",
    traceback_summary="File x.py, line 10",
    metadata={"input": "bad_value"}
)
```

**Output (in debug window):**
```
╭─────────── ℹ️ APP • STARTED • 10:30:45 ────────────╮
│ Application initialized                            │
╰────────────────────────────────────────────────────╯
```

---

### **2. Debug Message Protocol (`diagnostics/debug_message_protocol.py`)**

**What it does:** Structured JSON protocol for debug messages.

**Data Types:**
```python
class DataType(Enum):
    PLAIN_TEXT = "PlainText"
    DEBUG_MESSAGE = "DebugMessage"
    ERROR_LOG = "ErrorLog"
    PERFORMANCE_WARNING = "PerformanceWarning"
    TOOL_RESPONSE = "ToolResponse"
    API_CALL = "ApiCall"
```

**Log Levels:**
```python
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

**Message Structure:**
```json
{
  "obj_type": "str",
  "data_type": "DebugMessage",
  "timestamp": "2025-12-24T10:30:45.123456",
  "data": {
    "heading": "APP • STARTED",
    "body": "Application initialized",
    "level": "INFO",
    "metadata": {}
  }
}
```

**Sender Class:**
```python
from src.ui.diagnostics.debug_message_protocol import DebugMessageSender

sender = DebugMessageSender(socket_connection)

# Send debug message
sender.send_debug_message(
    heading="APP • STARTED",
    body="Application initialized",
    level="INFO",
    metadata={"version": "1.0"}
)

# Send plain text
sender.send_plain_text("Simple message")
```

---

### **3. Rich Error Print (`rich_error_print.py`)**

**What it does:** Beautiful error display using Rich panels.

**Usage:**
```python
from rich.console import Console
from src.ui.rich_error_print import RichErrorPrint

console = Console()
error_printer = RichErrorPrint(console)

# Print rich formatted messages
error_printer.print_rich("Error occurred!")
error_printer.print_rich("[green]Success![/green]")
```

---

### **4. Print Message Style (`print_message_style.py`)**

**What it does:** Display messages in main console with visual styles.

**API:**
```python
from src.ui.print_message_style import print_message

# User message (blue panel)
print_message("Hello, AI!", sender="user")

# AI response (green panel)
print_message("Hello, human!", sender="ai")

# Tool output (yellow panel)
print_message("Search completed", sender="tool")
```

**Output:**
```
╭──────────────────────────────────────────────────╮
│ 👤 [USER] Hello, AI!                             │
╰──────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────╮
│ 🤖 [AI] Hello, human!                            │
╰──────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────╮
│ 🛠️ [TOOL] Search completed                       │
╰──────────────────────────────────────────────────╯
```

---

### **5. Rich Traceback Manager (`diagnostics/rich_traceback_manager.py`)**

**What it does:** Beautiful exception tracebacks using Rich.

**Usage:**
```python
from src.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler
)

# Auto-install rich tracebacks
RichTracebackManager.install()

# Decorator for functions
@rich_exception_handler("My Function")
def my_function():
    raise ValueError("Something went wrong")

# Manual exception handling
try:
    risky_operation()
except Exception as e:
    RichTracebackManager.handle_exception(
        e,
        context="My Operation",
        extra_context={"user_id": 123}
    )
```

**Output:**
```
╭─────────────────────── Traceback (most recent call last) ────────────────────────╮
│ File "my_file.py", line 42, in my_function                                       │
│   39 │   def my_function():                                                      │
│   40 │       try:                                                                 │
│   41 │           risky_operation()                                                │
│ ❱ 42 │       except Exception as e:                                              │
│   43 │           raise                                                            │
│                                                                                   │
│ ValueError: Something went wrong                                                 │
╰───────────────────────────────────────────────────────────────────────────────────╯
```

---

## 🚀 **Quick Start Guide**

### **Step 1: Basic Debug Messages**

```python
from src.ui.diagnostics.debug_helpers import debug_info, debug_error

# Send info message
debug_info("STARTUP", "Application started successfully")

# Send error message
try:
    risky_operation()
except Exception as e:
    debug_error("OPERATION_FAILED", str(e), {"operation": "risky"})
```

### **Step 2: Print User Messages**

```python
from src.ui.print_message_style import print_message

# User input
user_input = input("You: ")
print_message(user_input, sender="user")

# AI response
ai_response = "Here's my response"
print_message(ai_response, sender="ai")
```

### **Step 3: Advanced Debug Logging**

```python
from src.ui.diagnostics.debug_helpers import (
    debug_tool_response,
    debug_api_call
)

# Log tool execution
debug_tool_response(
    tool_name="web_search",
    status="success",
    response_summary="Found 10 results",
    execution_time=1.5
)

# Log API call
debug_api_call(
    api_name="OpenAI",
    operation="completion",
    status="completed",
    duration=2.3
)
```

---

## 📚 **Debug Helpers API**

### **Message Levels**

```python
debug_info(heading, body, metadata=None)
debug_warning(heading, body, metadata=None)
debug_error(heading, body, metadata=None)
debug_critical(heading, body, metadata=None)
```

### **Specialized Logging**

```python
debug_tool_response(tool_name, status, response_summary, execution_time, metadata)
debug_api_call(api_name, operation, status, duration, metadata)
debug_performance_warning(operation, duration, threshold, context, metadata)
debug_error_log(error_type, error_message, context, traceback_summary, metadata)
```

### **Plain Text**

```python
debug_plain_text(text)
```

---

## 🎨 **Message Protocol**

### **Debug Message Structure**

```python
{
    "obj_type": "str",          # Object type (str or pickle)
    "data_type": "DebugMessage", # Message type
    "timestamp": "ISO8601",      # When sent
    "data": {
        "heading": "CATEGORY • ACTION",
        "body": "Detailed message",
        "level": "INFO",
        "metadata": {
            "key": "value"
        }
    }
}
```

### **Heading Convention**

Format: `CATEGORY • ACTION`

**Examples:**
- `APP • STARTED`
- `MCP • SERVER_INITIALIZED`
- `TOOL • EXECUTION_COMPLETE`
- `API • REQUEST_FAILED`
- `ERROR • VALIDATION_ERROR`

---

## 🐛 **Troubleshooting**

### **Problem: Debug Messages Not Showing**

**Cause:** Socket connection not established

**Fix:**
```python
from src.config import settings

# Check socket
if settings.socket_con is None:
    print("Socket not initialized!")
else:
    print("Socket connected")
```

---

### **Problem: Messages Go to Wrong Console**

**Issue:** Messages appear in main console instead of debug window

**Fix:**
- Debug messages → Debug window (separate subprocess)
- User/AI messages → Main console

```python
# For debug window
from src.ui.diagnostics.debug_helpers import debug_info
debug_info("TEST", "Debug message")

# For main console
from src.ui.print_message_style import print_message
print_message("User message", sender="user")
```

---

## 📝 **Best Practices**

### **1. Use Descriptive Headings**

```python
# ❌ Bad
debug_info("Error", "Something failed")

# ✅ Good
debug_error("API • CONNECTION_TIMEOUT", "OpenAI API request timed out", {
    "timeout": 60,
    "endpoint": "/v1/chat/completions"
})
```

### **2. Include Metadata**

```python
# ❌ Bad
debug_info("Tool executed", "Success")

# ✅ Good
debug_tool_response(
    tool_name="google_search",
    status="success",
    response_summary="Found 10 results",
    execution_time=1.2,
    metadata={
        "query": "Python tutorials",
        "results_count": 10
    }
)
```

### **3. Use Appropriate Levels**

```python
# INFO - Normal operations
debug_info("USER_INPUT", "Received user message")

# WARNING - Recoverable issues
debug_warning("RETRY", "Retrying failed request", {"attempt": 2})

# ERROR - Errors that affect functionality
debug_error("TOOL_FAILED", "Tool execution failed", {"error": str(e)})

# CRITICAL - System-breaking errors
debug_critical("SYSTEM_FAILURE", "Cannot continue", {"reason": "..."})
```

---

## 🆘 **Support**

**Questions?** Check:
1. This README
2. Code comments in `debug_helpers.py`
3. `debug_message_protocol.py` docstrings

**Found a bug?** Create an issue with:
- Function called
- Expected output
- Actual output

---

**Status:** ✅ **Production-Ready**

**Maintainer:** AI-Agent-Workflow Team

**Last Updated:** December 24, 2025

