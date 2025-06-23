# ai-workflow-task-agent PROJECT 🤖

A flexible and extensible AI agent implementation using LangChain and LangGraph frameworks, designed to connect custom tools with AI models for intelligent task execution.

## 🌟 Features

- **Dual Framework Support**: Implementations using both LangChain (`test.py`) and LangGraph (`lggraph.py`)
- **Web Search Integration**: Built-in DuckDuckGo search capabilities
- **Flexible Tool System**: Easy integration of custom tools with structured data classes
- **Intelligent Message Classification**: Automatic routing between direct LLM responses and tool usage
- **Ollama Integration**: Uses local Ollama models (llava-llama3:latest)
- **Rich Console Output**: Enhanced formatting for better user experience

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
- Better flexibility and versatility for multiple tools and LLMs

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

## 🛠️ Project Structure

```
ai_AGent/
├── lggraph.py          # LangGraph implementation (recommended)
├── test.py             # LangChain implementation
├── tools.py            # Tool definitions
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## 🔧 Architecture Details

### LangGraph Flow
```
User Input → Message Classifier → Router → [ChatBot | Tool Agent] → Response
```

1. **Message Classifier**: Determines if the input requires tool usage or direct LLM response
2. **Router**: Routes the message to appropriate handler based on classification
3. **ChatBot**: Handles general conversation and follow-up questions
4. **Tool Agent**: Selects and executes appropriate tools for information gathering

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

## 🎯 Why LangGraph is Better

### Advantages of LangGraph Implementation:

1. **Flexibility**: Easy to add new tools by defining argument and response data classes
2. **Versatility**: Support for multiple LLMs and tools with minimal configuration
3. **Intelligent Routing**: Automatic classification between chat and tool usage
4. **State Management**: Better conversation context handling
5. **Structured Outputs**: Type-safe tool interactions with Pydantic models
6. **Scalability**: Graph-based architecture for complex workflows

### LangChain vs LangGraph Comparison:

| Feature | LangChain (`test.py`) | LangGraph (`lggraph.py`) |
|---------|----------------------|--------------------------|
| Tool Integration | Basic | Advanced with structured schemas |
| Message Routing | Manual | Intelligent classification |
| State Management | Limited | Full conversation state |
| Extensibility | Moderate | High |
| Error Handling | Basic | Comprehensive |
| Performance | Good | Better |

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

## 📋 Dependencies

Key dependencies include:
- `langchain` - LangChain framework
- `langgraph` - LangGraph framework
- `langchain-ollama` - Ollama integration
- `langchain-community` - Community tools
- `duckduckgo-search` - Web search functionality
- `pydantic` - Data validation
- `rich` - Enhanced console output

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

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

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the code comments for implementation details

---

**Note**: The LangGraph implementation (`lggraph.py`) is recommended for production use due to its superior flexibility, structured approach, and better tool management capabilities.
