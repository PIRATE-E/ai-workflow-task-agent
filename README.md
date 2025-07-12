# ai-workflow-task-agent PROJECT 🤖

A flexible and extensible AI agent implementation using LangChain and LangGraph frameworks, designed to connect custom tools with AI models for intelligent task execution.

---

## 🌟 Features

- **Dual Framework Support**: Implementations using both LangChain (`test.py`) and LangGraph (`lggraph.py`)
- **Web Search Integration**: Built-in DuckDuckGo search capabilities
- **Flexible Tool System**: Easy integration of custom tools with structured data classes
- **Intelligent Message Classification**: Automatic routing between direct LLM responses and tool usage
- **Ollama Integration**: Uses local Ollama models (llava-llama3:latest)
- **Rich Console Output**: Enhanced formatting for better user experience
- **RAG (Retrieval-Augmented Generation) Support**: Multiple functions for converting text/data chunks for RAG, making it easy to use your data flexibly with AI
- **Neo4j-based RAG**: Specialized support for extracting and storing knowledge (triples) in a Neo4j graph database for advanced RAG workflows
- **Concurrency for Speed**: Handles multiple tasks in parallel for faster responses
- **Flexible Error Logging**: Print error logs anywhere in your code—or even send them across the network—using scripts from the `utils` package

---

## 🏗️ Architecture

### LangChain Implementation (`test.py`)
- Simple ReAct (Reasoning + Acting) agent pattern
- Zero-shot React description agent
- Basic tool integration with error handling

### LangGraph Implementation (`lggraph.py`) ⭐ **Recommended**
- Advanced state graph architecture
- Intelligent message classification system
- Conditional routing between chat and tool usage
- Structured tool definitions with Pydantic models
- **RAG integration:** Functions for converting and processing text/data chunks for RAG, with extra utilities in the `rag/` folder
- **Neo4j graph support for RAG:** The `rag/neo4j_rag.py` script can extract and save triples in a Neo4j database, enabling graph-based knowledge retrieval
- **Concurrency:** Processes multiple tasks at the same time, resulting in quicker responses to user queries
- **Error Logging:** Use scripts from the `utils` package, including network error reporting via `error_transpher.py`

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
   git clone https://github.com/PIRATE-E/ai_AGent.git
   cd ai_AGent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

#### Running the LangGraph Implementation (Recommended)
```bash
python lggraph.py
```

#### Running the LangChain Implementation
```bash
python test.py
```

---

## 🛠️ Project Structure

```
ai_AGent/
├── lggraph.py            # LangGraph implementation (recommended)
├── test.py               # LangChain implementation
├── tools.py              # Tool definitions
├── utils/                # Utility package with useful scripts
│   ├── __init__.py
│   └── error_transpher.py # Show error logs over the network using sockets
├── rag/                  # RAG utilities and graph database RAG support
│   ├── __init__.py
│   ├── rag.py            # General RAG utilities for chunking, retrieval, etc.
│   └── neo4j_rag.py      # Extract and save triples to Neo4j for graph-based retrieval
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

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