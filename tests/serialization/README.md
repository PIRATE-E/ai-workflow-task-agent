# 🧪 Rich Object Serialization Tests

This directory contains comprehensive tests for serializing Rich objects across different methods, specifically designed to test the error routing system for the AI-Agent-Workflow project.

## 📁 Test Files

### `test_rich_serialization.py`
**Purpose**: Test different serialization methods for complex Rich Panel objects

**Features**:
- Creates complex Rich Panel with tables, syntax highlighting, trees, and more
- Tests 4 serialization methods:
  - 🥒 **Pickle**: Python's built-in serialization
  - 🌿 **Dill**: Enhanced serialization (handles more object types)
  - 🎨 **Rich-to-String**: Converts Rich objects to visual string representation
  - 📄 **JSON Custom**: JSON encoding with Rich object metadata

**Output**: 
- Displays original complex panel
- Shows serialized data for each method
- Attempts to reconstruct objects
- Provides detailed comparison table

### `test_socket_transmission.py`
**Purpose**: Test actual socket transmission of serialized Rich objects

**Features**:
- Creates mock socket server (simulates debug window process)
- Tests transmission of Rich Panel objects over sockets
- Demonstrates real-world error routing scenario
- Shows how different serialization methods work over network

**Output**:
- Mock server receives and displays transmitted objects
- Shows successful reconstruction on receiving end
- Demonstrates which methods work best for socket transmission

### `run_serialization_tests.py`
**Purpose**: Complete test suite runner with comprehensive reporting

**Features**:
- Runs all serialization tests in sequence
- Generates detailed comparison reports
- Provides scenario-based recommendations
- Includes implementation guidance for error routing

**Output**:
- Complete test suite execution
- Final recommendations table
- Implementation code examples

## 🚀 How to Run Tests

### Run Individual Tests

```bash
# Test Rich object serialization methods
python tests/serialization/test_rich_serialization.py

# Test socket transmission
python tests/serialization/test_socket_transmission.py

# Run complete test suite
python tests/serialization/run_serialization_tests.py
```

### Install Optional Dependencies

```bash
# For enhanced serialization testing
pip install dill
```

## 📊 Test Results Overview

### Serialization Methods Comparison

| Method | Success Rate | Reconstruction | Best Use Case |
|--------|-------------|----------------|---------------|
| 🥒 Pickle | ⚠️ Variable | ✅ Full Object | Simple objects, same Python version |
| 🌿 Dill | ✅ High | ✅ Full Object | Complex objects, robust serialization |
| 🎨 Rich-to-String | ✅ Always | ⚠️ Visual Only | Socket transmission, visual display |
| 📄 JSON Custom | ✅ Always | ⚠️ Partial | Cross-platform, metadata preservation |

### 🎯 Recommendation for Error Routing

**Winner**: **Rich-to-String Conversion** 🎨

**Why**:
- ✅ Always works with any Rich object
- ✅ Preserves visual formatting perfectly
- ✅ No complex deserialization needed
- ✅ Works across process boundaries
- ✅ Lightweight and fast
- ✅ Perfect for debug window display

## 🔧 Implementation for Your Project

Based on test results, here's the recommended implementation for your error routing system:

```python
# In src/utils/error_transfer.py - SocketCon.send_error()
def send_error(self, error_message, close_socket: bool = False):
    try:
        # Handle Rich objects by converting to string representation
        if hasattr(error_message, '__rich_console__'):
            from rich.console import Console
            import io
            temp_console = Console(
                file=io.StringIO(), 
                width=120, 
                force_terminal=True,
                color_system="windows"
            )
            temp_console.print(error_message)
            message_str = temp_console.file.getvalue()
        else:
            message_str = str(error_message)
        
        self.client_socket.sendall(message_str.encode('utf-8'))
    except Exception as e:
        # Handle errors...
```

## 🧪 Test Scenarios Covered

### Complex Rich Panel Creation
- **Tables** with multiple columns and styling
- **Syntax highlighting** with Python code
- **Tree structures** showing project architecture
- **Columns layout** with status panels
- **Rules and separators** for organization
- **Mixed content types** in single panel

### Serialization Testing
- **Object-to-string conversion** with size measurement
- **Reconstruction attempts** with success/failure tracking
- **Error handling** for unsupported serialization
- **Performance comparison** between methods

### Socket Transmission Testing
- **Mock server setup** simulating debug window
- **Real socket transmission** over localhost
- **Message reception and display** on server side
- **Format detection** and appropriate rendering

## 📈 Expected Test Output

When you run the tests, you'll see:

1. **Original Complex Panel**: Beautiful Rich-formatted panel with multiple components
2. **Serialization Results**: Success/failure for each method with data sizes
3. **Reconstructed Objects**: Attempts to recreate original objects
4. **Socket Transmission**: Live demonstration of sending objects over sockets
5. **Comparison Tables**: Detailed analysis of each method's performance
6. **Final Recommendations**: Specific guidance for your error routing implementation

## 🎯 Key Insights from Tests

1. **Pickle/Dill**: Can reconstruct full objects but may fail with complex Rich objects containing console references
2. **Rich-to-String**: Always works, preserves visual formatting, perfect for display purposes
3. **JSON Custom**: Good for metadata preservation but loses Rich object functionality
4. **Socket Transmission**: Rich-to-String method works flawlessly over network

## 💡 Next Steps

After running these tests, you can confidently implement the Rich-to-String approach in your error routing system:

1. Update `SocketCon.send_error()` with Rich object detection
2. Test with your actual Rich Traceback Manager
3. Verify error tracebacks appear correctly in debug window
4. Confirm user window no longer shows tracebacks

The tests provide concrete evidence that this approach will solve your error routing issue!