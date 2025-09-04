# 🤖 AI-Agent-Workflow Project

> **A production-ready, enterprise-grade consumer desktop AI assistant featuring LangGraph multi-agent architecture, OpenAI integration with NVIDIA API, dynamic tool registry (17 total tools: 3 fundamental + 14 dynamic MCP tools), advanced JSON-RPC MCP integration, and robust development practices.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Sentry](https://img.shields.io/badge/Monitoring-Sentry-purple.svg)](https://sentry.io/)

---

## 🌟 What Makes This Special?

This project is a **consumer desktop AI assistant** with:
- **OpenAI Integration**: Seamless switching between local Ollama and OpenAI/NVIDIA API models
- **17-Tool Dynamic System**: 3 fundamental tools (GoogleSearch, RAGSearch, Translate) + 14 dynamic MCP filesystem tools
- **Advanced JSON-RPC MCP Integration**: Full protocol implementation with dynamic tool discovery
- **Enterprise-grade LangGraph multi-agent architecture** with StateAccessor singleton pattern
- **Production-ready streaming**: Optimized OpenAI streaming with reasoning-first output
- **Local-first, privacy-focused design** with optional cloud model integration
- **Professional monitoring and logging infrastructure** with Sentry and socket logging

---

## ✨ **Core Features**

### 🧠 **LangGraph Multi-Agent System**
- **Production-Ready**: LangGraph orchestration with enterprise-grade architecture
- **Smart Message Classification**: Automatic routing between LLM and tool responses
- **StateAccessor Singleton**: Thread-safe state management across all agents
- **Conversation Memory**: Persistent context tracking and learning

### 🛠️ **Tool System**
- **Fundamental Tools**: GoogleSearch, RAGSearch, Translate (always available)
- **MCP Integration**: Filesystem MCP server with read/write/create capabilities
- **JSON-RPC Communication**: Professional MCP protocol implementation
- **Tool Registry**: Unified management of fundamental and MCP tools

### 🏗️ **Current Architecture**
- **LangGraph System**: Multi-agent conversation orchestration
- **StateAccessor**: Centralized state management with singleton pattern
- **Tool Registry**: Manages fundamental tools and MCP filesystem integration
- **MCP Manager**: JSON-RPC communication with subprocess management
- **RAG Engine**: Knowledge retrieval with Neo4j and vector search

### 🔒 **Privacy-First Design**
- **Local Processing**: No cloud dependency, all computation local
- **User-Controlled Data**: Complete control over information and privacy
- **Secure Architecture**: Enterprise-grade security patterns
- **Transparent Operations**: Full visibility into AI assistant behavior

### 📊 **Production Infrastructure**
- **Sentry Monitoring**: Real-time error tracking and performance monitoring
- **Socket Logging**: Separate subprocess for clean log management
- **ChatDestructor**: Comprehensive resource cleanup and graceful shutdown
- **Enterprise Patterns**: Singleton patterns, modular design, error resilience

---

## 🚀 **Quick Start**

### **Prerequisites**

1. **Python 3.11+** with pip
2. **Ollama** - [Download & Install](https://ollama.ai/)
3. **Neo4j Database** (Optional, for knowledge graph features)

### **Installation**

```bash
# Clone the repository
git clone https://github.com/PIRATE-E/ai-workflow-task-agent.git
cd ai-workflow-task-agent

# Install dependencies
pip install -r requirements.txt

# Pull required Ollama models
ollama pull llava-llama3:latest
ollama pull llama3.1:8b
ollama pull deepseek-r1:8b
```

### **Launch the Application**

```bash
# Start the AI Workflow Task Agent
python src/main_orchestrator.py
```

**That's it!** The system will automatically:
- Initialize the LangGraph workflow
- Start the logging subprocess
- Clear the console for a clean experience
- Display the beautiful ASCII banner
- Begin the interactive chat session

---

## 🏗️ **Architecture Overview**

### **🎯 System Flow**
```
User Input → Message Classifier → Router → [LLM Agent | Tool Agent] → Rich Output
     ↓              ↓               ↓              ↓           ↓
StateAccessor → Context → Tool Registry → [GoogleSearch | RAGSearch | Translate | MCP Filesystem]
```

### **🔧 Core Components**

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **LangGraph System** | Multi-agent conversation orchestration | State management, agent routing, memory integration |
| **StateAccessor** | Centralized state management | Thread-safe singleton, conversation context |
| **Tool Registry** | Unified tool management | Fundamental tools + MCP filesystem integration |
| **MCP Manager** | Model Context Protocol integration | JSON-RPC communication, subprocess management |
| **RAG Engine** | Knowledge retrieval and generation | Multi-modal retrieval, Neo4j graphs, async operations |
| **Monitoring Stack** | Production infrastructure | Sentry integration, socket logging, error tracking |

---

## 📁 **Project Structure**

```
ai-workflow-task-agent/                 🏗️ Enterprise-Grade Organization
├── src/                               📦 Main Source Code
│   ├── main_orchestrator.py          🚀 Application Entry Point
│   ├── agents/                        🤖 Intelligent Agent System
│   │   ├── chat_llm.py               ├─ LLM Response Generation
│   │   ├── classify_agent.py         ├─ Message Classification
│   │   ├── router.py                 ├─ Conversation Routing
│   │   ├── tool_selector.py          ├─ Dynamic Tool Selection
│   │   └── agents_schema/            └─ Pydantic Schemas & Validation
│   ├── core/                          🔧 Core System Components
│   │   ├── chat_initializer.py       ├─ System Bootstrap & Configuration
│   │   ├── chat_destructor.py        ├─ Resource Cleanup & Shutdown
│   │   └── graphs/                   └─ LangGraph Workflow Definition
│   │       └── node_assign.py
│   ├── models/                        📊 Data Models & State Management
│   │   └── state.py                  └─ LangGraph State & Accessor Pattern
│   ├── RAG/                           🧠 Retrieval-Augmented Generation
│   │   └── RAG_FILES/
│   │       ├── rag.py                ├─ Document Processing & Vector Search
│   │       ├── neo4j_rag.py          ├─ Knowledge Graph Operations
│   │       └── sheets_rag.py         └─ Structured Data Integration
│   ├── tools/                         🛠️ External Tool Integration
│   │   └── lggraph_tools/
│   │       ├── tool_assign.py        ├─ Tool Registry & Management
│   │       ├── tool_response_manager.py ├─ Response Handling
│   │       ├── tools/                ├─ Individual Tool Implementations
│   │       ├── wrappers/             ├─ Tool Wrapper Classes
│   │       └── tool_schemas/         └─ Tool Parameter Schemas
│   ├── prompts/                       📝 Centralized Prompt Management
│   │   ├── system_prompts.py         ├─ Core System Prompts
│   │   ├── rag_prompts.py            ├─ RAG-Specific Prompts
│   │   └── web_search_prompts.py     └─ Search & Classification Prompts
│   ├── config/                        ⚙️ Configuration Management
│   │   ├── settings.py               ├─ Environment Variables & Defaults
│   │   └── configure_logging.py      └─ Logging Configuration Utility
│   ├── utils/                         🔧 Utility Functions & Helpers
│   │   ├── socket_manager.py         ├─ Network Logging & Process Management
│   │   ├── model_manager.py          ├─ AI Model Lifecycle Management
│   │   ├── error_transfer.py         ├─ Network Error Reporting
│   │   └── structured_triple_prompt.py └─ Knowledge Graph Utilities
│   └── ui/                            🎨 User Interface Components
│       ├── print_banner.py           ├─ ASCII Art & Branding
│       ├── print_message_style.py    ├─ Rich Console Formatting
│       └── print_history.py          └─ Conversation History Display
├── examples/                          📚 Demo Applications & Tutorials
│   ├── demo_complete_system.py       ├─ Full System Demonstration
│   ├── demo_subprocess_logging.py    ├─ Logging System Demo
│   ├── log_viewer_demo.py            └─ Log Visualization Example
├── tests/                             🧪 Comprehensive Test Suite
│   ├── integration/                  ├─ Integration & E2E Tests
│   ├── error_handling/               ├─ Error Handling Tests
│   ├── model_manager_tests/          ├─ Model Management Tests
│   └── unit/                         └─ Unit Tests
├── experimental/                      🔬 Research & Development
│   ├── chunk_debugger.py             ├─ RAG Chunk Analysis Tools
│   └── gemini_style_cli/             └─ Advanced CLI Interface Experiments
├── basic_logs/                        📊 Logging & Monitoring
│   ├── error_log.txt                 ├─ Application Logs
│   ├── graph.png                     ├─ Workflow Visualization
│   └── requirements.txt              └─ Log Server Dependencies
└── screenshots/                       📸 Documentation Assets
```

---

## 🤝 **Contributing**

This project follows enterprise development practices:

### **Development Workflow**
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes with proper commit messages
git commit -m "feat: add new capability for X"

# Run tests
python tests/run_tests.py

# Create pull request
```

### **Code Standards**
- **Type Hints**: All functions include comprehensive type annotations
- **Documentation**: Docstrings for all classes and complex functions
- **Error Handling**: Graceful fallbacks and comprehensive exception management
- **Testing**: Unit tests for core functionality, integration tests for workflows

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **LangGraph Team** - For the excellent graph-based orchestration framework
- **Ollama** - For local LLM capabilities and easy model management
- **Rich Library** - For beautiful console interfaces and formatting
- **Neo4j** - For powerful graph database capabilities
- **Sentry** - For production-grade error monitoring

---

## 📞 **Support**

- **GitHub Issues**: [Report bugs and request features](https://github.com/PIRATE-E/ai-workflow-task-agent/issues)
- **Documentation**: Complete API docs in the `docs/` directory
- **Examples**: Working examples in the `examples/` directory
- **Tests**: Comprehensive test suite in the `tests/` directory

---

**Built with ❤️ by PIRAT-E** | **Enterprise-Ready AI Systems** | **Production Since 2025**
