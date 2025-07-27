# 🤖 AI LangGraph Chatbot - Professional Edition

A professionally structured AI chatbot implementation using LangGraph framework with advanced RAG capabilities, modular architecture, and industrial-grade organization following Netflix/Google standards.

---

## ✨ Key Features

### 🏗️ **Professional Architecture**
- **Modular Design**: Clean separation of concerns with organized src/ structure
- **Industrial Standards**: Follows Netflix/Google-level project organization
- **Team-Ready**: Multiple developers can collaborate simultaneously
- **Scalable Foundation**: Easy to extend and maintain

### 🤖 **Advanced AI Capabilities**
- **LangGraph Framework**: State-of-the-art graph-based conversation flow
- **Intelligent Routing**: Smart message classification and tool selection
- **Multi-Modal RAG**: Support for text, knowledge graphs, and structured data
- **Neo4j Integration**: Graph-based knowledge retrieval and storage
- **Ollama Integration**: Local LLM support with model management

### 🛠️ **Production Features**
- **Rich Console Interface**: Beautiful terminal UI with progress indicators
- **Comprehensive Logging**: Network-based error reporting and monitoring
- **Configuration Management**: Environment-based settings with .env support
- **Error Resilience**: Graceful handling of API failures and network issues
- **Memory Management**: Conversation state persistence and history

---

## 🏗️ Professional Architecture

### 🎯 **LangGraph Implementation** (`lggraph.py`) - **Production Ready**
- **State Graph Architecture**: Advanced conversation flow management
- **Intelligent Message Classification**: Automatic routing between LLM and tools
- **Conditional Routing**: Smart decision-making for optimal responses
- **Structured Tool System**: Type-safe interactions with Pydantic models
- **Multi-Modal RAG**: Text, knowledge graphs, and structured data support
- **Neo4j Integration**: Graph-based knowledge storage and retrieval
- **Error Resilience**: Graceful handling of API failures
- **Rich Console UI**: Professional terminal interface with progress indicators

### 🎨 **System Flow**
```
User Input → Message Classifier → Router → [LLM Response | Tool Agent] → Rich Output
     ↓              ↓                ↓              ↓           ↓
State Management → Context → Tool Selection → Execution → Formatted Response
```

### 🧠 **Core Components**
1. **Message Classifier**: Intelligent routing based on user intent
2. **Tool Agent**: Smart tool selection and parameter extraction  
3. **RAG System**: Multi-modal retrieval and generation
4. **State Manager**: Conversation context and memory
5. **Error Handler**: Network-based logging and recovery

---

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama**: Download and install [Ollama](https://ollama.ai/)
2. **Pull the required model**:
   ```bash
   ollama pull llava-llama3:latest
   ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/PIRATE-E/AI_llm.git
   cd AI_llm
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (optional):
   ```bash
   cp src/config/.env.example .env
   # Edit .env with your API keys and preferences
   ```

### Usage

#### Running the Professional LangGraph Chatbot
```bash
python lggraph.py
```

#### Exploring Demo Examples
```bash
# Run system demonstration
python examples/demo_complete_system.py

# View logging capabilities
python examples/log_viewer_demo.py

# Test error handling
python examples/demo_subprocess_logging.py
```

---

## 🛠️ Professional Project Structure

```
AI_llm/                           # 🏗️ Professional Organization
├── src/                          # 📁 Source Code (Industry Standard)
│   ├── __init__.py              # Python package initialization
│   ├── config/                   # ⚙️ Configuration Management
│   │   ├── __init__.py
│   │   ├── settings.py          # Environment-based configuration
│   │   ├── configure_logging.py # Logging configuration utility
│   │   └── .env.example         # Environment variables template
│   ├── utils/                    # 🛠️ Utility Helpers
│   │   ├── __init__.py
│   │   ├── model_manager.py     # AI model management (singleton)
│   │   ├── socket_manager.py    # Network connection management
│   │   ├── error_transfer.py    # Network-based error reporting
│   │   └── structured_triple_prompt.py # RAG prompt utilities
│   ├── RAG/                      # 🧠 Retrieval-Augmented Generation
│   │   ├── __init__.py
│   │   └── RAG_FILES/
│   │       ├── __init__.py
│   │       ├── rag.py           # Text-based RAG implementation
│   │       ├── neo4j_rag.py     # Graph-based RAG with Neo4j
│   │       └── sheets_rag.py    # Structured data RAG
│   └── tools/                    # 🔧 External Tool Integrations
│       ├── __init__.py
│       └── lggraph_tools/
│           ├── __init__.py
│           └── tools.py         # Google Search and other tools
├── examples/                     # 📚 Demo Files & Examples
│   ├── demo_complete_system.py  # Full system demonstration
│   ├── demo_subprocess_logging.py # Logging system demo
│   ├── log_viewer_demo.py       # Log visualization demo
│   └── langchain_example/       # LangChain comparison examples
├── tests/                        # 🧪 Comprehensive Test Suite
│   ├── __init__.py
│   ├── integration/             # Integration tests
│   ├── error_handling/          # Error handling tests
│   ├── model_manager_tests/     # Model management tests
│   └── unit/                    # Unit tests
├── experimental/                 # 🔬 Innovation Lab
│   ├── chunk_debugger.py        # RAG chunk analysis tools
│   └── gemini_style_cli/        # CLI interface experiments
├── copilot_instructions/         # 🤖 AI Assistant Instructions
│   ├── ENHANCED_LEARNING_FOCUSED_INSTRUCTIONS.md
│   ├── ENHANCED_PIRATE_COPILOT_INSTRUCTIONS.md
│   └── PERSONAL_LEARNING_TUTOR_INSTRUCTIONS.md
├── lggraph.py                    # 🚀 Main Application Entry Point
├── README.md                     # 📖 Project Documentation
└── requirements.txt              # 📦 Dependencies
```

### 🎯 **Architecture Benefits**
- **🏢 Enterprise-Ready**: Follows Netflix/Google organization standards
- **👥 Team-Collaborative**: Multiple developers can work simultaneously
- **🔧 Maintainable**: Clear separation of concerns and responsibilities
- **📈 Scalable**: Easy to extend with new features and components
- **🧪 Testable**: Comprehensive test coverage with organized test suites

---

## 🔧 Architecture Details

### LangGraph Flow
```
User Input → Message Classifier → Router → [ChatBot | Tool Agent] → Response
```

1. **Message Classifier**: Determines if the input requires tool usage or direct LLM response
2. **Router**: Routes the message to appropriate handler based on classification
3. **ChatBot**: Handles general conversation and follow-up questions
4. **Tool Agent**: Selects and executes appropriate tools for information gathering
5. **RAG Functions**: Converts and processes text chunks for smarter, context-aware responses; use functions from the `rag/` folder for maximum flexibility

---

### Tool System

Tools are defined using Pydantic models for structured input/output:

```python
class duckduckgo_search(BaseModel):
    query: str = Field(description="Search query for DuckDuckGo...")

search_tool = StructuredTool.from_function(
    func=search_duckduckgo,
    name="DuckDuckGoSearch",
    description="For general web searches (recent info, facts, news).",
    args_schema=duckduckgo_search,
)
```

---

### RAG (Retrieval-Augmented Generation) Integration

- **Flexible RAG Functions:**  
  Use the functions in the `rag/` folder to convert text or document chunks for use with retrieval-augmented generation. This gives your AI the flexibility to pull in the most relevant information from your own data.
- **Neo4j Graph Support:**  
  The `rag/neo4j_rag.py` script lets you extract knowledge triples and store them in a Neo4j graph database. This is useful for graph-based retrieval, allowing the AI to reason over relationships in your data.

---

### Concurrency for Faster Responses

- **How it's used:**  
  The agent can handle multiple tasks at the same time, making it much faster for users—especially when dealing with many requests or complex workflows.

---

### Flexible Error Logging with `utils` Package

- **Log errors anywhere:**  
  Use scripts from the `utils` package to log errors wherever you need—whether to the console, to a file, or even across the network (using sockets) with `error_transpher.py`. This is perfect for debugging distributed systems or logging errors from remote processes.

---

## 🎯 Why LangGraph is Better

### Advantages of LangGraph Implementation:

1. **Flexibility**: Easy to add new tools by defining argument and response data classes
2. **Versatility**: Support for multiple LLMs and tools with minimal configuration
3. **Intelligent Routing**: Automatic classification between chat and tool usage
4. **State Management**: Better conversation context handling
5. **Structured Outputs**: Type-safe tool interactions with Pydantic models
6. **Scalability**: Graph-based architecture for complex workflows
7. **RAG Integration**: Advanced retrieval-augmented generation features, including graph-based retrieval with Neo4j
8. **Concurrency**: Handles multiple requests at once for faster user experience
9. **Flexible Logging**: Print or transmit error logs anywhere using scripts from the `utils` package

---

### LangChain vs LangGraph Comparison:

| Feature            | LangChain (`test.py`)   | LangGraph (`lggraph.py`)      |
|--------------------|------------------------|-------------------------------|
| Tool Integration   | Basic                  | Advanced with structured schemas |
| Message Routing    | Manual                 | Intelligent classification    |
| State Management   | Limited                | Full conversation state       |
| Extensibility      | Moderate               | High                          |
| Error Handling     | Basic                  | Comprehensive & flexible      |
| Performance        | Good                   | Better (with concurrency)     |
| RAG Support        | No                     | Yes, with flexible chunk & graph handling |
| Logging            | Basic                  | Flexible, via `utils` package |

---

## 🔌 Adding Custom Tools

To add a new tool to the LangGraph implementation:

1. **Define the tool function**:
   ```python
   def my_custom_tool(param1: str, param2: int) -> str:
       # Your tool logic here
       return "Tool result"
   ```

2. **Create a Pydantic model for arguments**:
   ```python
   class MyCustomToolArgs(BaseModel):
       param1: str = Field(description="Description of param1")
       param2: int = Field(description="Description of param2")
   ```

3. **Register the tool**:
   ```python
   custom_tool = StructuredTool.from_function(
       func=my_custom_tool,
       name="MyCustomTool",
       description="What this tool does",
       args_schema=MyCustomToolArgs,
   )
   
   # Add to tools list
   tools.append(custom_tool)
   ```

---

## 📋 Dependencies

Key dependencies include:
- `langchain` - LangChain framework
- `langgraph` - LangGraph framework
- `langchain-ollama` - Ollama integration
- `langchain-community` - Community tools
- `duckduckgo-search` - Web search functionality
- `pydantic` - Data validation
- `rich` - Enhanced console output
- `neo4j` - For graph database-based RAG
- Python concurrency libraries (e.g., `asyncio`, `threading`)
- `socket` (Python standard library) - For network error reporting in `utils/error_transpher.py`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🆘 Troubleshooting

### Common Issues:

1. **Ollama Model Not Found**:
   ```bash
   ollama pull llava-llama3:latest
   ```

2. **Import Errors**:
   ```bash
   pip install -r requirements.txt
   ```

3. **DuckDuckGo Search Errors**:
   - Check internet connection
   - Verify DuckDuckGo search is not blocked

4. **Neo4j Connection Issues**:
   - Make sure you have a running Neo4j instance
   - Check your connection & authentication settings

5. **Concurrency Issues**:
   - Make sure your Python version supports concurrency libraries (e.g., `asyncio`)
   - Check for correct usage of async functions or threads

6. **Error Logs Not Showing or Not Sent Over Network**:
   - Ensure you are using the logging scripts from the `utils` package (like `error_transpher.py`) in your code

---

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the code comments for implementation details

---

**Note**: The LangGraph implementation (`lggraph.py`) is recommended for production use due to its superior flexibility, RAG support (including Neo4j graph-based retrieval), concurrency, and comprehensive error logging via the `utils` package.