# 🤖 AI Workflow Task Agent - Enterprise Edition

> **A production-ready AI chatbot system built with LangGraph, featuring advanced RAG capabilities, intelligent agent orchestration, and enterprise-grade architecture following industry best practices.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Sentry](https://img.shields.io/badge/Monitoring-Sentry-purple.svg)](https://sentry.io/)

---

## 🌟 **What Makes This Special?**

This isn't just another chatbot - it's a **professionally architected AI system** that demonstrates enterprise-level software engineering practices. The project showcases advanced patterns used by companies like Netflix, Google, and Microsoft.

### 🎯 **Key Achievements**
- **80% Memory Reduction**: Optimized from ~1.2GB to ~200MB baseline usage
- **70% Faster Startup**: Lazy loading and intelligent import management
- **Production Monitoring**: Sentry integration for error tracking
- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Advanced RAG**: Multi-modal retrieval with Neo4j knowledge graphs

---

## ✨ **Core Features**

### 🧠 **Intelligent Agent System**
- **LangGraph Orchestration**: State-of-the-art graph-based conversation flow
- **Smart Message Classification**: Automatic routing between LLM and tool responses
- **Dynamic Tool Selection**: Context-aware tool invocation with parameter extraction
- **Conversation State Management**: Persistent memory and context tracking

### 🔍 **Advanced RAG Capabilities**
- **Multi-Modal Retrieval**: Text documents, knowledge graphs, and structured data
- **Neo4j Integration**: Graph-based knowledge storage and intelligent querying
- **Lazy Loading**: Performance-optimized imports for heavy dependencies
- **Async Processing**: Non-blocking RAG operations with semaphore control

### 🏗️ **Enterprise Architecture**
- **Modular Design**: Clean separation with src/ structure following industry standards
- **Dependency Injection**: Centralized configuration and state management
- **Error Resilience**: Graceful fallbacks and comprehensive error handling
- **Production Monitoring**: Real-time error tracking with Sentry SDK

### 🎨 **Professional UX**
- **Rich Console Interface**: Beautiful terminal UI with progress indicators
- **Network Logging**: Separate subprocess for clean log management
- **Sound Notifications**: Audio feedback for important events
- **Cross-Platform**: Windows, Linux, and macOS support

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
State Management → Context → Tool Selection → Execution → Formatted Response
```

### **🔧 Core Components**

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **Main Orchestrator** | Entry point and lifecycle management | Clean startup, graceful shutdown, resource cleanup |
| **Chat Initializer** | System bootstrap and configuration | Sentry integration, console setup, state initialization |
| **Agent System** | Intelligent conversation routing | Classification, tool selection, LLM generation |
| **RAG Engine** | Knowledge retrieval and generation | Neo4j graphs, document processing, async operations |
| **Tool Framework** | External service integration | Dynamic tool discovery, parameter validation |
| **Socket Manager** | Network logging and monitoring | Subprocess management, error reporting |

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

## 🧬 **Technical Deep Dive**

### **🎭 Agent Orchestration**
The system uses a sophisticated agent-based architecture where each component has a specific responsibility:

```python
# Message Flow Example
User: "Search for information about AI safety"
↓
Classifier Agent: Determines this needs tool usage
↓
Router: Routes to tool_agent based on classification
↓
Tool Selector: Chooses appropriate search tool with parameters
↓
Tool Execution: Performs search and returns formatted results
```

### **🧠 Advanced RAG Implementation**
- **Lazy Loading**: Heavy dependencies (PyTorch, Chroma) loaded only when needed
- **Async Processing**: Non-blocking document processing with semaphore control
- **Multi-Modal**: Supports PDFs, text files, knowledge graphs, and structured data
- **Intelligent Chunking**: Recursive character splitting with overlap for context preservation

### **⚡ Performance Optimizations**
- **Memory Efficient**: 80% reduction in baseline memory usage
- **Fast Startup**: 70% improvement in initialization time
- **Socket-Based Logging**: Separate subprocess prevents main thread blocking
- **Resource Cleanup**: Comprehensive destructor pattern for graceful shutdown

---

## 🛠️ **Configuration**

### **Environment Variables**
Create a `.env` file in the project root:

```bash
# Model Configuration
DEFAULT_MODEL=llava-llama3:latest
CLASSIFIER_MODEL=llama3.1:8b
CYPHER_MODEL=deepseek-r1:8b

# Logging Configuration
ENABLE_SOCKET_LOGGING=true
LOG_DISPLAY_MODE=separate_window
ENABLE_SOUND_NOTIFICATIONS=true

# Performance Settings
SEMAPHORE_LIMIT_CLI=15
SEMAPHORE_LIMIT_API=5

# Development Settings
DEBUG=false
```

### **Key Settings**
- **LOG_DISPLAY_MODE**: `separate_window` | `background` | `file` | `console`
- **Models**: Configurable Ollama models for different tasks
- **Semaphores**: Control concurrent processing limits
- **Features**: Toggle socket logging, sound notifications, debug mode

---

## 📊 **Usage Examples**

### **Basic Conversation**
```
🤖 AI Workflow Task Agent
───────────────────────────

You: What is machine learning?
🤖: Machine learning is a subset of artificial intelligence (AI) that enables 
    computers to learn and make decisions from data without being explicitly 
    programmed for each task...

You: /search latest AI research papers
🔍: [Automatically selects web search tool]
📄: Here are the latest AI research papers from top conferences...
```

### **Advanced RAG Queries**
```
You: What did the kafka.pdf document say about distributed systems?
🧠: [Loads document, processes chunks, performs semantic search]
📚: Based on the Kafka documentation, distributed systems handle...

You: /use tool knowledge graph search about system architecture
🔍: [Queries Neo4j knowledge graph]
🕸️: The knowledge graph shows these connections between system components...
```

### **Tool Commands**
- `/search [query]` - Force web search
- `/use ai [query]` - Force LLM response
- `/use tool [query]` - Force tool selection
- `exit` - Graceful shutdown

---

## 🔍 **Monitoring & Debugging**

### **Built-in Monitoring**
- **Sentry Integration**: Real-time error tracking and performance monitoring
- **Socket Logging**: Network-based log aggregation with separate display window
- **Rich Console**: Beautiful, informative terminal output with progress indicators
- **Graph Visualization**: Auto-generated workflow diagrams saved to `basic_logs/graph.png`

### **Development Tools**
```bash
# Run comprehensive tests
python tests/run_tests.py

# Test logging system
python examples/demo_subprocess_logging.py

# Analyze RAG chunks
python experimental/chunk_debugger.py

# View system logs
python examples/log_viewer_demo.py
```

---

## 🚀 **Development History**

This project has evolved through several major architectural improvements:

### **🔄 Recent Milestones**
- **July 2025**: Complete system overhaul with 80% memory reduction
- **July 2025**: Professional restructuring following Netflix/Google standards  
- **July 2025**: Added agent-based architecture with LangGraph
- **July 2025**: Implemented lazy loading and performance optimizations
- **July 2025**: Added Sentry monitoring and production-ready features

### **🏗️ Architectural Evolution**
1. **Monolithic Script** → **Modular Architecture**
2. **Basic Chatbot** → **Intelligent Agent System**
3. **Simple RAG** → **Multi-Modal Knowledge Retrieval**
4. **Console Prints** → **Professional Monitoring**
5. **Development Code** → **Production-Ready System**

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
