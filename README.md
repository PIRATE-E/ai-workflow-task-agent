# 🤖 AI-Agent-Workflow Project

> **Enterprise-grade consumer desktop AI assistant featuring LangGraph multi-agent architecture, hybrid OpenAI/NVIDIA integration with local Ollama support, intelligent agent mode with `/agent` command, Rich Traceback debugging system, event-driven architecture, and professional development practices.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-v1.7.0-brightgreen.svg)]()

---

## 🌟 **What Makes This Special?**

This is a **production-ready consumer desktop AI assistant** with enterprise-grade architecture featuring:

- **🤖 Hybrid AI Integration**: Seamless switching between local Ollama models and OpenAI/NVIDIA API with intelligent rate limiting (30 requests/minute)
- **⚡ Agent Mode**: Revolutionary `/agent` command triggering multi-tool orchestration with AI-powered parameter generation
- **🛠️ 18-Tool Ecosystem**: 3 fundamental tools + 14 dynamic MCP filesystem tools + 1 shell command tool
- **🎨 Rich Traceback System**: Enterprise-grade error handling with visual debugging and separate debug windows
- **📡 Event-Driven Architecture**: Complete listener system with Rich.status integration for real-time updates
- **🔒 Privacy-First Design**: Local processing with optional cloud model integration
- **🏗️ LangGraph Multi-Agent**: Production-ready conversation orchestration with StateAccessor singleton pattern

---

## ✨ **Core Features**

### 🧠 **Hybrid AI System**
- **Local Ollama Support**: Privacy-focused local model processing
- **OpenAI/NVIDIA Integration**: Cloud models with intelligent rate limiting (30 requests/minute)
- **Automatic Model Switching**: Seamless hybrid operation based on availability and preferences
- **Rate Limit Management**: Built-in protection against API rate limit violations

### ⚡ **Agent Mode (`/agent` Command)**
- **Multi-Tool Orchestration**: Intelligent tool chain execution with AI parameter generation
- **Context-Aware Execution**: Maintains execution history and reasoning chains for better results
- **Tool Fallback Support**: Automatic recovery with alternative tools when primary tools fail
- **Simplified Final Evaluation**: Streamlined workflow quality assessment (v4.0)

### 🛠️ **Comprehensive Tool System (18 Total)**

#### **Fundamental Tools (3)**
- **GoogleSearch**: Web search capabilities for current information
- **RAGSearch**: Knowledge base search using retrieval-augmented generation
- **Translate**: Language translation services

#### **MCP Filesystem Tools (14)**
- **File Operations**: Read, write, create, delete files with proper encoding
- **Directory Management**: List, create, navigate directory structures
- **Search Capabilities**: Find files and content across the filesystem
- **JSON-RPC Protocol**: Professional MCP integration with dynamic tool discovery

#### **Shell Command Tool (1)**
- **Secure Execution**: Safe shell command execution with UTF-8 encoding
- **Error Handling**: Comprehensive error capture with structured output
- **Console Options**: Support for current console and new window execution

### 🎨 **Rich Traceback & Debugging System**
- **Visual Error Handling**: Beautiful tracebacks with syntax highlighting and variable inspection
- **Separate Debug Windows**: Error routing to dedicated debug panel vs user notifications
- **Structured Diagnostics**: Transport-agnostic logging with metadata-rich events
- **Socket-Based Routing**: Network-based log aggregation for clean separation
- **Performance Monitoring**: Error categorization, frequency tracking, and debugging statistics

### 📡 **Event-Driven Architecture**
- **RichStatusListener**: Automatic status updates with Rich.status integration
- **EventManager**: Singleton pattern with thread-safe event processing
- **Variable Change Detection**: Automatic event emission when object properties change
- **Memory Leak Prevention**: WeakKeyDictionary for automatic cleanup
- **Event Filtering**: Targeted event routing with metadata-based filtering

---

## 🚀 **Quick Start**

### **Prerequisites**
```bash
Python 3.11+ (recommended: 3.11 or 3.13)
Virtual environment (recommended)
```

### **Installation**
```bash
# Clone the repository
git clone https://github.com/PIRAT-E/AI-Agent-Workflow-Project.git
cd AI-Agent-Workflow-Project

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### **Configuration**
Create `.env` file in the project root:
```env
# OpenAI/NVIDIA API Configuration (Optional - for cloud models)
OPEN_AI_API_KEY=your_nvidia_api_key_here
OPENAI_TIMEOUT=30

# Sentry Monitoring (Optional)
SENTRY_DSN=your_sentry_dsn_here

# Local Model Configuration (Ollama)
OLLAMA_HOST=http://localhost:11434
GPT_MODEL=llama3.2:latest  # or your preferred local model
```

### **Run the Application**
```bash
python src/main_orchestrator.py
```

---

## 💬 **Usage Guide**

### **Basic Conversation**
```
You: What is the capital of France?
AI: The capital of France is Paris...
```

### **Tool Commands**
```bash
# Force web search
/search latest AI developments

# Force LLM response
/use ai explain quantum computing

# Force tool selection
/use tool translate "hello" to Spanish

# Shell command execution
/shell dir
/shell python --version
```

### **Agent Mode**
```bash
# Trigger intelligent agent orchestration
/agent search for Python tutorials and save the best ones to a file

# Agent will automatically:
# 1. Use GoogleSearch to find Python tutorials
# 2. Evaluate and filter results
# 3. Use filesystem tools to save content
# 4. Provide comprehensive summary
```

### **Application Control**
```bash
exit           # Graceful shutdown with cleanup
Ctrl+C         # Emergency exit
```

---

## 🏗️ **Project Architecture**

### **Core System (src/)**
```
📁 src/
├── 🎯 main_orchestrator.py          # Application entry point with Rich Traceback
├── 📁 agents/                       # Multi-agent system
│   ├── agent_mode_node.py          # Agent mode orchestration with context tracking
│   ├── chat_llm.py                 # LLM communication
│   ├── classify_agent.py           # Message classification (/agent detection)
│   ├── router.py                   # Message routing
│   └── tool_selector.py            # Tool selection logic
├── 📁 config/                      # Configuration management
│   ├── settings.py                 # Application settings
│   └── configure_logging.py        # Logging configuration
├── 📁 core/                        # Core system components
│   ├── chat_initializer.py         # Chat system initialization
│   └── graphs/                     # LangGraph workflow definitions
├── 📁 models/                      # Data models
│   └── state.py                    # StateAccessor singleton
├── 📁 prompts/                     # AI prompt templates
│   ├── agent_mode_prompts.py       # Agent orchestration prompts
│   └── open_ai_prompt.py           # OpenAI-specific prompts
└── 📁 utils/                       # Utility modules
    ├── model_manager.py            # Hybrid model management
    ├── open_ai_integration.py      # OpenAI/NVIDIA integration
    └── listeners/                  # Event system
        ├── event_listener.py       # Core event management
        └── rich_status_listen.py   # Rich status integration
```

### **Tools Ecosystem (src/tools/)**
```
📁 tools/lggraph_tools/
├── tool_assign.py                  # Tool registry management
├── tool_response_manager.py        # Response handling
├── 📁 tools/                       # Tool implementations
│   ├── google_search_tool.py       # Web search
│   ├── rag_search_tool.py          # Knowledge base search
│   ├── translate_tool.py           # Translation
│   ├── run_shell_command_tool.py   # Shell command execution
│   └── 📁 mcp_integrated_tools/    # MCP filesystem tools
│       └── filesystem.py           # File operations (14 tools)
└── 📁 tool_schemas/                # Tool argument schemas
```

### **UI & Diagnostics (src/ui/)**
```
📁 ui/
├── print_message_style.py          # Message formatting
├── print_banner.py                 # Application banner
└── 📁 diagnostics/                 # Rich Traceback system
    ├── rich_traceback_manager.py   # Enterprise error handling
    ├── debug_helpers.py            # Structured debug messages
    └── debug_message_protocol.py   # Debug transport protocol
```

### **MCP Integration (src/mcp/)**
```
📁 mcp/
└── manager.py                      # MCP server lifecycle management
```

### **RAG System (src/RAG/)**
```
📁 RAG/
└── RAG_FILES/                      # Knowledge retrieval system
    ├── neo4j_rag.py               # Neo4j graph database integration
    └── rag.py                     # RAG orchestration
```

---

## 🔧 **Advanced Features**

### **Rate Limiting & API Management**
- **OpenAI/NVIDIA**: Automatic 30 requests/minute rate limiting
- **Request Tracking**: Real-time monitoring with status updates
- **Intelligent Waiting**: Automatic delays when limits approached
- **Error Recovery**: Graceful handling of rate limit violations

### **Rich Traceback Debugging**
- **Visual Tracebacks**: Syntax highlighting and variable inspection
- **Context Preservation**: Detailed error context with timestamps
- **Debug Window Routing**: Separate error display from user interface
- **Performance Monitoring**: Error frequency tracking and statistics

### **Event System Capabilities**
- **Variable Change Detection**: Automatic events when object properties change
- **Rich Status Integration**: Live status updates with spinning indicators
- **Memory Management**: WeakKeyDictionary prevents memory leaks
- **Thread Safety**: Proper locking for concurrent operations

### **Agent Mode Features**
- **Execution Context Tracking**: Maintains tool execution history and reasoning chains
- **Success/Failure Patterns**: Learns from previous executions for better results
- **Tool Fallback Logic**: Automatic recovery when primary tools fail
- **Comprehensive Evaluation**: Final workflow quality assessment

---

## 🛠️ **Development Tools**

### **Testing**
```bash
# Run comprehensive test suite
python tests/run_tests.py

# Test specific components
python tests/error_handling/test_rich_traceback.py
python tests/event_listener/test_event_system.py
python tests/test_shell_command_fix.py
```

### **Examples & Demonstrations**
```bash
# Event system examples
python examples/event_listener/main.py

# Subprocess logging demo
python examples/demo_subprocess_logging.py

# RAG chunk analysis
python experimental/chunk_debugger.py
```

### **Monitoring & Debugging**
```bash
# View system logs
python examples/log_viewer_demo.py

# Monitor error handling
# (Debug window opens automatically during errors)

# Check tool registration
# (Tools table displayed on startup)
```

---

## 🎨 **Technical Highlights**

### **Enterprise Patterns**
- **Singleton StateAccessor**: Thread-safe state management across all agents
- **Rich Traceback Manager**: Enterprise-grade error handling with visual debugging
- **Socket-Based Logging**: Network log aggregation with structured message protocol
- **MCP JSON-RPC**: Professional protocol implementation with dynamic tool discovery
- **Event-Driven Architecture**: Complete listener system with automatic cleanup

### **Performance Features**
- **Hybrid Model Management**: Intelligent switching between local and cloud models
- **Request Rate Limiting**: Built-in protection with automatic wait management
- **Memory Management**: WeakKeyDictionary prevents memory leaks
- **Resource Cleanup**: Comprehensive cleanup functions for graceful shutdown
- **Streaming Support**: Optimized OpenAI streaming with reasoning-first output

### **Development Practices**
- **Type Hints**: Comprehensive type annotations throughout codebase
- **Error Handling**: Graceful fallbacks and comprehensive exception management
- **Modular Design**: Clean separation of concerns with well-defined interfaces
- **Professional Logging**: Structured diagnostics with metadata-rich events
- **Test Coverage**: Comprehensive test suite for core functionality

---

## 📋 **Configuration Options**

### **Environment Variables**
```bash
# API Configuration
OPEN_AI_API_KEY=your_api_key        # OpenAI/NVIDIA API key
OPENAI_TIMEOUT=30                   # API timeout in seconds

# Model Configuration
GPT_MODEL=openai/gpt-oss-120b      # Default model name
OLLAMA_HOST=http://localhost:11434  # Local Ollama server

# Debugging
LOG_DISPLAY_MODE=true               # Enable debug window
SENTRY_DSN=your_sentry_dsn         # Error monitoring

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=30          # API rate limit (built-in)
```

### **Tool Configuration**
```python
# Customize tool behavior in src/tools/lggraph_tools/tool_assign.py
# Add new tools by implementing ToolAssign interface
# Configure MCP server endpoints in src/mcp/manager.py
```

---

## 🚀 **Recent Milestones**

### **v1.7.0 - Rich Traceback System (August 2025)**
- ✅ Enterprise-grade error handling with visual debugging
- ✅ Structured diagnostics framework with transport-agnostic logging
- ✅ Debug window routing for clean user experience
- ✅ Comprehensive test suite for error handling

### **v1.6.0 - Agent Mode Enhancement (August 2025)**
- ✅ `/agent` command for multi-tool orchestration
- ✅ AI-powered parameter generation with context tracking
- ✅ Tool fallback logic and execution history
- ✅ Simplified final evaluation system (v4.0)

### **Previous Milestones**
- ✅ **Event-Driven Architecture**: Complete listener system with Rich.status integration
- ✅ **Shell Command Integration**: Secure execution with UTF-8 support
- ✅ **OpenAI/NVIDIA Integration**: Hybrid model system with rate limiting
- ✅ **MCP Integration**: JSON-RPC protocol with 14 filesystem tools
- ✅ **LangGraph Architecture**: Multi-agent conversation orchestration

---

## 🎯 **Current Status**

### **Production Readiness: 95%**
- ✅ **Core Architecture**: LangGraph multi-agent system operational
- ✅ **Tool Ecosystem**: 18 tools fully functional with comprehensive coverage
- ✅ **Error Handling**: Enterprise-grade Rich Traceback system
- ✅ **Agent Mode**: 90%+ quality with multi-tool orchestration
- ✅ **API Integration**: Hybrid OpenAI/Ollama with rate limiting
- ✅ **Event System**: Complete architecture (ready for expanded usage)

### **Active Development Areas**
- 🔄 **Performance Optimization**: Memory usage and response time improvements
- 🔄 **Enhanced Agent Features**: Advanced reasoning and tool chaining
- 🔄 **Event System Expansion**: Broader utilization across components
- 🔄 **Documentation**: API documentation and advanced usage guides

---

## 🤝 **Contributing**

### **Development Workflow**
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Follow professional commit standards
git commit -m "feat: add new capability for X"

# Run tests before submitting
python tests/run_tests.py

# Create pull request with detailed description
```

### **Code Standards**
- **Type Hints**: All functions require comprehensive type annotations
- **Error Handling**: Graceful fallbacks with Rich Traceback integration
- **Documentation**: Docstrings for classes and complex functions
- **Testing**: Unit tests for new functionality

### **Architecture Guidelines**
- **Singleton Patterns**: Use for shared resources (StateAccessor, RichTracebackManager)
- **Event-Driven Design**: Utilize listener system for component communication
- **MCP Integration**: Follow JSON-RPC standards for tool development
- **Rich Traceback**: Integrate @rich_exception_handler for error handling

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **LangGraph Team** - Graph-based orchestration framework
- **OpenAI & NVIDIA** - AI model API services
- **Ollama** - Local LLM capabilities
- **Rich Library** - Beautiful console interfaces and error handling
- **Sentry** - Production-grade error monitoring

---

## 📞 **Support & Resources**

- **GitHub Issues**: [Report bugs and request features](https://github.com/PIRATE-E/AI-Agent-Workflow-Project/issues)
- **Documentation**: Complete guides in the `docs/` directory
- **Examples**: Working demonstrations in the `examples/` directory
- **Tests**: Comprehensive test suite in the `tests/` directory

---

**Built with ❤️ by PIRAT-E** | **Enterprise AI Systems** | **Production Ready Since 2025**

---

## 🎓 **Learning Resources**

This project demonstrates enterprise-grade Python development with:
- **Advanced Architecture Patterns**: Singleton, Observer, Strategy patterns
- **Error Handling Best Practices**: Rich Traceback with visual debugging
- **Event-Driven Programming**: Complete listener system implementation
- **API Integration**: Rate limiting, hybrid model management, JSON-RPC
- **Production Practices**: Professional logging, monitoring, and testing

Perfect for developers learning industrial-level AI application development.