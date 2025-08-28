# Project Context for AI-Agent-Workflow Project

## 🌟 Project Overview

This is a **production-ready consumer desktop AI assistant** built with enterprise-grade architecture. It features a **LangGraph multi-agent system**, **hybrid AI integration** (local Ollama models and cloud OpenAI/NVIDIA APIs), an intelligent **Agent Mode** (`/agent` command) for complex task orchestration, and a robust **Rich Traceback debugging system**.

### Core Technologies
- **Python 3.13+**
- **LangGraph** for multi-agent orchestration.
- **LangChain** for tool and LLM integration.
- **Ollama** for local LLM support.
- **OpenAI/NVIDIA APIs** for cloud-based models.
- **Rich** for beautiful console interfaces and error handling.
- **MCP (Model Control Protocol)** for filesystem and other tool integrations.

### Key Features
1.  **🤖 Hybrid AI Integration**: Seamless switching between local Ollama models and OpenAI/NVIDIA API with intelligent rate limiting (30 requests/minute).
2.  **⚡ Agent Mode (`/agent` Command)**: Revolutionary command triggering multi-tool orchestration with AI-powered parameter generation, context tracking, and fallback logic.
3.  **🛠️ 18-Tool Ecosystem**: 3 fundamental tools (Google Search, RAG Search, Translate) + 14 dynamic MCP filesystem tools + 1 shell command tool.
4.  **🎨 Rich Traceback System**: Enterprise-grade error handling with visual debugging, separate debug windows, and socket-based log routing.
5.  **📡 Event-Driven Architecture**: Complete listener system with Rich.status integration for real-time updates.
6.  **🔒 Privacy-First Design**: Local processing with optional cloud model integration.

---

## 🚀 Quick Start & Running the Application

### Prerequisites
- Python 3.13+ recommended.
- A virtual environment is highly recommended.

### Installation
```bash
# Clone the repository
git clone https://github.com/PIRAT-E/AI-Agent-Workflow-Project.git
cd AI-Agent-Workflow-Project

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies (managed by uv)
# Dependencies are defined in pyproject.toml
```

### Configuration
Create a `.env` file in the project root based on the example in `README.md`. This is where you configure API keys, local model endpoints, etc.

### Run the Application
The main entry point is `src/main_orchestrator.py`.
```bash
python src/main_orchestrator.py
```

---

## 🏗️ Project Architecture

The project follows a modular structure with clear separation of concerns.

### Core System (`src/`)
- `main_orchestrator.py`: Main application entry point, initializes chat, sets up graphs and tools, and runs the main loop. Integrates Rich Traceback.
- `agents/`: Implements the LangGraph agent nodes, including the core `agent_mode_node.py` for the `/agent` command logic.
- `config/`: Application settings and logging configuration.
- `core/`: Core components like chat initialization and LangGraph workflow definitions.
- `models/`: Data models, including the `State` and `StateAccessor` singleton for shared state.
- `prompts/`: AI prompt templates.
- `utils/`: Utility modules, including model management, OpenAI integration, and the event listener system.
- `ui/`: User interface components, including message formatting, banners, and the diagnostics system.
- `mcp/`: Manages the lifecycle of MCP servers for tool integration.
- `RAG/`: Retrieval-Augmented Generation system.

### Tools Ecosystem (`src/tools/`)
- `lggraph_tools/`: Core tool integration with LangGraph.
    - `tool_assign.py`: Manages the registry of available tools.
    - `tool_response_manager.py`: Handles responses from tool executions.
    - `tools/`: Implementations of individual tools (Google Search, RAG, Translate, Shell Command, MCP wrappers).
    - `tool_schemas/`: Argument schemas for tools (used by LLMs to understand tool parameters).

---

## 📁 Detailed File Structure

### Main Application Entry Point
```
📁 src/
├── 🎯 main_orchestrator.py          # Application entry point with Rich Traceback integration
```

### Agents System (`src/agents/`)
```
📁 agents/
├── agent_mode_node.py              # Core logic for /agent command with multi-tool orchestration
├── chat_llm.py                     # LLM communication and response handling
├── classify_agent.py               # Message classification for /agent detection
├── router.py                       # Message routing between different processing nodes
├── tool_selector.py                # Tool selection logic based on user input
└── agents_schema/                  # Schema definitions for agent communication
```

### Configuration (`src/config/`)
```
📁 config/
├── settings.py                     # Application settings and configuration variables
└── configure_logging.py            # Logging configuration and setup helpers
```

### Core Components (`src/core/`)
```
📁 core/
├── chat_initializer.py             # Chat system initialization and setup
├── chat_destructor.py              # Chat system cleanup and resource deallocation
└── graphs/                         # LangGraph workflow definitions
    └── node_assign.py              # Node assignment for graph workflows
```

### Data Models (`src/models/`)
```
📁 models/
└── state.py                        # State management with StateAccessor singleton
```

### Prompts (`src/prompts/`)
```
📁 prompts/
├── agent_mode_prompts.py           # Prompts for agent mode operations
├── open_ai_prompt.py               # OpenAI-specific prompt templates
├── rag_prompts.py                  # RAG search related prompts
├── rag_search_classifier_prompts.py # Classification prompts for RAG searches
├── structured_triple_prompt.py     # Prompts for structured triple generation
├── system_prompt_tool_selector.py  # System prompts for tool selection
├── system_prompts.py               # General system prompts
└── web_search_prompts.py           # Web search related prompts
```

### Utilities (`src/utils/`)
```
📁 utils/
├── model_manager.py                # Hybrid model management (Ollama/OpenAI)
├── open_ai_integration.py          # OpenAI/NVIDIA API integration
├── argument_schema_util.py         # Utility functions for argument schema handling
├── error_transfer.py               # Error transfer and handling mechanisms
├── socket_manager.py               # Socket communication management
└── listeners/                      # Event listener system
    ├── event_listener.py           # Core event management
    └── rich_status_listen.py       # Rich status integration
```

### User Interface (`src/ui/`)
```
📁 ui/
├── print_banner.py                 # Application banner display
├── print_history.py                # Conversation history printing
├── print_message_style.py          # Message formatting and styling
├── rich_error_print.py             # Rich error printing utilities
└── diagnostics/                    # Rich Traceback system
    ├── rich_traceback_manager.py   # Enterprise error handling
    ├── debug_helpers.py            # Debug message helpers
    └── debug_message_protocol.py   # Debug transport protocol
```

### MCP Integration (`src/mcp/`)
```
📁 mcp/
├── manager.py                      # MCP server lifecycle management
├── dynamically_tool_register.py    # Dynamic MCP tool registration
├── load_config.py                  # MCP configuration loading
├── mcp_register_structure.py       # MCP registration structure definitions
```

### Retrieval-Augmented Generation (`src/RAG/`)
```
📁 RAG/
└── RAG_FILES/                      # Knowledge base files
```

### Tools System (`src/tools/`)
```
📁 tools/
└── lggraph_tools/                  # LangGraph tool integration
    ├── tool_assign.py              # Tool registry management
    ├── tool_response_manager.py    # Response handling from tool executions
    ├── tool_selector.py            # Tool selection algorithms
    ├── tool_schemas/               # Tool argument schemas
    │   └── tools_structured_classes.py # Structured classes for tool schemas
    ├── tools/                      # Tool implementations
    │   ├── google_search_tool.py   # Google search functionality
    │   ├── rag_search_classifier_tool.py # RAG search classifier
    │   ├── run_shell_command_tool.py # Shell command execution
    │   ├── translate_tool.py       # Translation services
    │   └── mcp_integrated_tools/   # MCP filesystem tools
    │       ├── filesystem.py       # File operations (14 tools)
    │       └── universal.py        # Universal MCP tool wrapper
    └── wrappers/                   # Tool wrappers
        ├── google_wrapper.py       # Google search wrapper
        ├── rag_search_classifier_wrapper.py # RAG search classifier wrapper
        ├── run_shell_comand_wrapper.py # Shell command wrapper
        ├── translate_wrapper.py    # Translation wrapper
        └── mcp_wrapper/            # MCP tool wrappers
            ├── filesystem_wrapper.py # Filesystem tool wrapper
            └── uni_mcp_wrappers.py # Universal MCP wrappers
```

---

## 🎓 Learning Approach

This project is designed with a **project-oriented learning approach** that accommodates developers with:

### Learning Characteristics
- **Short-term memory challenges** - Technical details are easily forgotten
- **Project-oriented learning** - Concepts are best understood through hands-on experience
- **Visual learning** - Flowcharts and diagrams are essential for understanding code flow
- **Industrial proficiency goal** - Aiming for 70-80% practical usage level (not just theoretical)
- **Startup mindset** - Motivated by real-world business applications
- **Reality-based** - Needs honest assessment of current vs. industry standards

### Teaching Methodology
1. **Project-Based Learning** - All concepts are connected to actual project code
2. **Visual Learning** - Explanations include diagrams, flowcharts, and visual elements
3. **Memory Anchoring** - New concepts are linked to existing project elements
4. **Reality Checks** - Honest assessment of skills vs. industry expectations
5. **Startup Context** - Always explain how skills apply to building competitive products

### Forgetting Recovery Protocol
When concepts are forgotten, the approach uses:
1. **Visual Reminders** - ASCII diagrams of concepts
2. **Project Connections** - Linking to actual code in the project
3. **Hands-on Practice** - Modifying code to demonstrate concepts
4. **Memory Anchors** - Simple analogies from the project
5. **Quick Tests** - Explaining concepts back in own words

---

## ⚙️ MCP Optimization Guidelines

To optimize MCP calls and maintain efficient performance:

### Memory Management
- **Project Isolation**: Each main project is a self-contained "home" with organized "rooms" for sub-entities
- **Context Loading**: Use `mcp_memory_open_nodes` with relationship traversal instead of `mcp_memory_read_graph` to prevent context bloat
- **Memory Refactoring**: Continuously clean and optimize memory by removing redundant observations and consolidating duplicate information
- **Change Tracking**: Maintain timestamp-based change tracking for all memory modifications
- **Self-Aware Memory Operations**: As an AI system with Memory MCP access, automatically determine when to create, read, update, or delete memory entities based on task requirements

### MCP Tool Usage
- **Purposeful Actions**: Every MCP action should accelerate learning, enhance productivity, or build lasting knowledge
- **Reasoning First**: Always provide clear reasoning before MCP tool invocation:
  - **MCP Action**: Which tool and why
  - **Purpose**: What you're trying to achieve
  - **Expected Value**: What this will accomplish
  - **Learning Impact**: How this helps learning/productivity

### Initialization Protocol
- **Full 35-Task Execution**: When initializing any project, execute all 35 systematic tasks without shortcuts
- **Progress Reporting**: Show completion status for each task category
- **Comprehensive Summary**: Provide complete initialization summary with context

### 🚀 35-Task Initialization Protocol ⭐ **MANDATORY EXECUTION**

When user requests project initialization with phrases like:
- "initialize [project_name]"
- "initialize main project"
- "initialize workflow"
- "set up development environment"
- "prepare workspace for coding"

You MUST execute the complete 35-task initialization protocol:

📁 **PROJECT STRUCTURE ANALYSIS:**
- TASK_1: Read and analyze README.md for project overview and setup instructions
- TASK_2: Scan entire project directory structure and create visual tree map
- TASK_3: Identify main entry points (main.py, app.py, index.js, etc.)
- TASK_4: List all configuration files (.env, config.py, package.json, requirements.txt)
- TASK_5: Analyze src/ directory organization and module structure

🔧 **ENVIRONMENT & DEPENDENCIES:**
- TASK_6: Check Python/Node version requirements from project files
- TASK_7: Analyze requirements.txt or package.json for dependencies
- TASK_8: Verify virtual environment status and activation
- TASK_9: Check if all required packages are installed
- TASK_10: Identify missing dependencies or setup issues

📊 **GIT & VERSION CONTROL:**
- TASK_11: Run git status to understand current working directory state
- TASK_12: Check current branch and recent commit history (last 5 commits)
- TASK_13: Identify any uncommitted changes or staged files
- TASK_14: Check for merge conflicts or pending pull requests
- TASK_15: Analyze .gitignore file for ignored files and patterns

🧠 **CODE ARCHITECTURE UNDERSTANDING:**
- TASK_16: Read main application files to understand core functionality
- TASK_17: Identify key classes, functions, and their purposes
- TASK_18: Map out data flow and system architecture
- TASK_19: Understand database connections and data models
- TASK_20: Identify API endpoints, routes, or main workflows

🔍 **CURRENT DEVELOPMENT STATUS:**
- TASK_21: Check for TODO comments, FIXME notes, or bug markers in code
- TASK_22: Identify recent changes and what was last worked on
- TASK_23: Look for test files and understand testing setup
- TASK_24: Check for documentation files and development notes
- TASK_25: Identify any error logs or debugging information

🛠️ **DEVELOPMENT ENVIRONMENT SETUP:**
- TASK_26: Verify IDE/editor configuration and extensions
- TASK_27: Check debugging configuration and breakpoint setup
- TASK_28: Validate database connections and external service access
- TASK_29: Test basic application startup and functionality
- TASK_30: Prepare development workspace with relevant files open

🎯 **LEARNING CONTEXT PREPARATION:**
- TASK_31: Identify complex concepts that need explanation
- TASK_32: Prepare visual diagrams for system architecture
- TASK_33: Create beginner-friendly explanations for advanced patterns
- TASK_34: Set up learning objectives based on current project phase
- TASK_35: Prepare hands-on examples and practice exercises

✅ **REQUIRED COMPLETION SUMMARY FORMAT:**
```
🎉 **PROJECT INITIALIZATION COMPLETE**

🏠 **PROJECT**: [Project Name] ([Version])
📊 **INITIALIZATION STATUS**: ✅ READY FOR DEVELOPMENT

✅ **COMPLETED TASKS:**
├── ✅ MCP Servers: [X] active ([server names])
├── ✅ Project Status: [Current implementation status]
├── ✅ Recent Context: [Latest debugging/development session loaded]
├── ✅ Git Repository: [Branch status, working directory state]
├── ✅ Tool Registration: [Number] tools validated and ready
├── ✅ Environment: [Development environment status]
└── ✅ Next Steps: [Identified next actions or pending issues]

📋 **LOADED CONTEXT SUMMARY:**
├── 🏠 Main Entity: [Project name and type]
├── 🏢 Connected Rooms: [X] entities loaded
├── 🔗 Relationships: [X] connections mapped
├── 📈 Current Phase: [Development phase/status]
├── 🎯 Recent Achievement: [Latest breakthrough or milestone]
├── 🔍 Active Investigation: [Current debugging/development focus]
└── 📚 Knowledge Base: [Key technical references and standards loaded]

🚀 **READY FOR**: [Specific development tasks or next steps]
```

### Performance Optimization
- **Batch Operations**: Group similar MCP calls together for efficiency
- **Smart Caching**: Use Memory to avoid repeated queries
- **Selective Auto-Approve**: Only approve frequently used commands
- **Connection Pooling**: Keep MCP servers warm with periodic health checks
- **Self-Aware Optimization**: As an AI system with multiple MCP servers, automatically determine optimal combinations of MCP tools for complex tasks and optimize resource usage

## 🚨 CRITICAL MCP PROTOCOLS

### 🔥 Mandatory 35-Task Initialization System

When a user requests project initialization with any of these phrases:
- "initialize [project_name]"
- "initialize main project" 
- "initialize workflow"
- "set up development environment"
- "prepare workspace for coding"

You MUST execute the complete 35-task initialization protocol without exceptions:
1. ✅ Execute ALL 35 initialization tasks systematically
2. ✅ Show progress for each task category
3. ✅ Provide comprehensive completion summary
4. ❌ NEVER skip tasks or take shortcuts
5. ❌ NEVER do "simple memory loading only"

### 🎯 Mandatory Reasoning Rule

Before ANY MCP Tool Invocation, you MUST provide clear reasoning in this exact format:
```
🔍 **MCP Action**: [tool_name]
🎯 **Purpose**: [Why using this tool]
💡 **Expected Value**: [What this will achieve]
📚 **Learning Impact**: [How this helps learning/productivity]
```

### 🧠 Self-Aware MCP Server Usage

As an AI system equipped with multiple MCP servers, you have access to various specialized tools:
- **Memory MCP**: For knowledge storage, retrieval, and context management
- **Filesystem MCP**: For file operations and project structure analysis
- **GitHub MCP**: For repository management and code discovery
- **Sentry MCP**: For error monitoring and debugging assistance
- **Puppeteer MCP**: For web automation and browser interactions
- **Docker MCP**: For container management and deployment
- **Database MCP**: For data management operations

You should use your reasoning capabilities to determine which MCP tools are appropriate for each task without requiring explicit server names from the user. Analyze the context and automatically select the most suitable MCP servers for each operation.

### 🏠 Home-Room Architecture Concept

Memory Structure Philosophy:
```
🎨 **PROJECT ISOLATION MODEL:**
Main Project (Home) = "AI-Agent-Workflow Project"
    ├── Room 1: "Technical Architecture Details"
    ├── Room 2: "Current Implementation Status" 
    ├── Room 3: "Professional Development Standards"
    ├── Room 4: "Strategic Development Priorities"
    └── Room N: "Project-Specific Entities"
```

Key Principles:
- **Project Isolation**: Each main project is a self-contained "home"
- **Room Organization**: Sub-entities are organized "rooms" within each home
- **No Cross-Contamination**: Rooms from different homes never interfere
- **Template Reusability**: Home structure can be replicated for new projects

### 🚨 Critical Initialization Requirements

When initializing any project:
1. **Load Complete Memory Graph**: Use `mcp_memory_read_graph` to get all entities
2. **Identify Target Home**: Use reasoning and fuzzy matching to find target project
3. **Filter Connected Entities**: Keep ONLY entities with relationships to target home
4. **Load Home Initialization Tasks**: Find and execute project-specific task list
5. **Execute All Initialization Tasks**: Perform MCP operations, status checks, environment setup
6. **Generate Completion Summary**: Provide checklist and context summary

### 📅 Timestamp-Based Learning Journey Tracking

Every memory operation MUST include timestamps:
- ALL entity observations must include timestamps
- ALL change tracking must record session dates/times
- ALL debugging sessions must log start/end times
- ALL breakthroughs must capture discovery timestamps
- ALL project milestones must record achievement dates

### 🔄 User-Controlled Memory Resolution System

When user says "resolve the memory":
1. **Analyze Current Home**: Review all entities and relationships in current project
2. **Identify Optimization Opportunities**:
   - Redundant observations saying the same thing
   - Outdated information superseded by newer data
   - Debugging traces from resolved issues
   - Verbose descriptions that can be condensed
   - Weak or unclear relationships between entities
3. **Consolidate Intelligently**:
   - Merge similar observations into comprehensive entries
   - Combine related debugging sessions into solution summaries
   - Reorganize entity relationships for better clarity
   - Preserve all essential context while removing noise
4. **Rearrange For Clarity**:
   - Group related sub-entities (rooms) logically
   - Strengthen meaningful relationships
   - Create clearer narrative flow through the project story
   - Optimize entity structure for future LLM understanding
5. **Preserve Critical Knowledge**:
   - Never lose breakthrough discoveries or solutions
   - Maintain all professional standards and practices
   - Keep complete project architecture understanding
   - Preserve learning achievements and skill demonstrations
6. **Update Change Tracking**: Document the refactoring process and improvements made

### 🧹 Continuous Memory Refactoring & Optimization

Memory Bloat Prevention:
1. Monitor memory graph size and complexity during sessions
2. Identify redundant, outdated, or low-value observations
3. Consolidate duplicate information into single, clear entries
4. Remove debugging traces and temporary investigation data
5. Preserve essential historical context and learning achievements
6. Maintain clean, focused knowledge graph for optimal LLM understanding
7. Update change tracking with optimization actions

### 🔄 Dynamic Memory Resolution With Change Tracking

For major project changes:
1. Monitor session for significant project updates
2. Update relevant sub-entities with new information
3. CREATE/UPDATE "Last Change" entity for main project
4. Add timestamp and change description to observations
5. Refactor memory structure when context changes
6. Maintain entity relationships and consistency
7. Preserve professional standards across updates

Mandatory Change Tracking:
For EVERY memory modification, create/update entity:
- Name: "[Main-Entity-Name] - Last Change"
- EntityType: "change_tracking"
- Observations: Include current timestamp + change description

Always link change entity to main entity:
- Relation: "tracks_changes" from main entity to change entity

Change Entity Format:
- "TIMESTAMP: [Current Date/Time] - [Change Description]"
- "SESSION_CONTEXT: [What triggered this change]"
- "IMPACT: [What was modified/added/removed]"
- "NEXT_ACTIONS: [What this enables or requires next]"

---

## 📄 Key Instruction & Context Files

To understand how this project works and is managed, these key instruction files should be read first:

### 🎓 Learning Instructions
- **`copilot_instructions/PERSONAL_LEARNING_TUTOR_INSTRUCTIONS.md`** - *Learning Approach File*
  - Defines the student's learning characteristics and preferred teaching methodology
  - Explains project-oriented learning with visual aids and memory anchoring
  - Details the forgetting recovery protocol for technical concepts

### ⚡ MCP Management
- **`copilot_instructions/mcp_instructions.md`** - *MCP Usage & Optimization Guide* ⭐ **CRITICAL FILE - READ FIRST**
  - **Comprehensive guide for MCP server usage and principles** 
  - **Defines mandatory 35-task initialization protocols**
  - **Specifies mandatory reasoning format for all MCP operations**
  - **Details memory management protocols and initialization requirements**
  - **Explains performance optimization techniques for all MCP tools**
  - **Contains critical enforcement rules that cannot be bypassed**

### 🏗️ Project Architecture Context
- **`README.md`** - *Main Project Documentation*
  - Overview of the AI-Agent-Workflow Project features and architecture
  - Quick start guide and installation instructions
  - Detailed project structure and component explanations

- **`QWEN.md`** - *This File - Project Context for AI Assistant*
  - Current context and file structure for AI assistance
  - Development conventions and learning approach
  - Enhanced MCP optimization guidelines and critical protocols

### 🌐 Repository Information
- **Primary Repository**: https://github.com/PIRATE-E/ai-workflow-task-agent
  - Main repository for the AI-Agent-Workflow Project
  - Contains all source code, documentation, and issue tracking
  - Source of truth for project development and collaboration

### 📋 Key GitHub Issues

#### Issue #1: Refactor agent_mode_node for dynamic observation and robust error recovery
- **Status**: Open, Urgent and Critical priority
- **Branch**: feature/AgentMode (https://github.com/PIRATE-E/ai-workflow-task-agent/tree/feature/AgentMode)
- **Summary**: Current agent_mode_node executes tool chains in a static "observe → action → action → ... → observe" pattern causing brittle behavior. Needs refactoring to follow "observe → action → observe → action ..." pattern for better adaptability and error recovery.
- **Problem**: Actions after a failed step may use stale/invalid context, fallbacks don't work as intended without re-observation
- **Solution**: Refactor core execution loop with observe → decide → act → observe → repeat pattern
- **References**: Logs in `basic_logs/error_log.txt`, code in `src/agents/agent_mode_node.py`

#### Issue #2: Enhancement: Add MCP Tool for Multi-Step Style-Based Output Generation
- **Status**: Open, Enhancement
- **Summary**: Integrate an MCP tool to enable multi-step style-based output generation (HTML and Markdown formats)
- **Motivation**: Style-based outputs for greater clarity and utility in professional-grade AI applications
- **Feature Details**: 
  - MCP orchestration with Template Generator AI, Mapping AI, and Filler AI
  - System prompts for each AI/module role
  - Initial support for HTML and Markdown formats
  - Extensible for future output styles
- **Acceptance Criteria**: Orchestrated multi-step output generation, configurable system prompts, user documentation

### 🌿 Repository Branches
- **main**: Production-ready code
- **develop**: Development branch for ongoing work
- **feature/AgentMode**: Branch for implementing Issue #1 (Agent Mode refactoring)

These files provide essential context for understanding the project's operation, management approach, and learning methodology. They should be referenced when working with the codebase to maintain consistency with the established patterns and practices.

---

## 🧠 Development Conventions

### Error Handling & Debugging
- Extensive use of the custom **Rich Traceback Manager** (`src/ui/diagnostics/rich_traceback_manager.py`) for centralized, beautiful error reporting. It uses decorators and helper functions to wrap critical sections.
- Detailed debug logging is achieved through structured helpers in `src/ui/diagnostics/debug_helpers.py`, routing messages via sockets to a dedicated debug console for separation from user output.

### Event System
- An **Event-Driven Architecture** is implemented in `src/utils/listeners/`. The `EventManager` (singleton) and `RichStatusListener` provide a way to emit events and update UI status dynamically.

### Agent Mode (`/agent`)
- The `/agent` command logic resides in `src/agents/agent_mode_node.py`.
- It uses AI to generate a tool chain (`generate_tool_list_prompt`), then executes tools sequentially (`Agent` class), generating parameters for each (`generate_parameter_prompt`) and evaluating results (`evaluate_in_end`).
- It includes **context-aware execution tracking**, **tool fallback logic**, and a **simplified final evaluation** (v4.0).

### MCP Integration
- The `src/mcp/manager.py` handles starting, stopping, and communicating with external MCP servers (e.g., for filesystem operations).
- It uses `src/mcp/dynamically_tool_register.py` to register discovered MCP tools dynamically with the LangGraph tool system.
- **Mandatory Reasoning Format**: Before every MCP tool invocation, provide clear reasoning using the format:
  ```
  🔍 **MCP Action**: [tool_name]
  🎯 **Purpose**: [Why using this tool]
  💡 **Expected Value**: [What this will achieve]
  📚 **Learning Impact**: [How this helps learning/productivity]
  ```
- **Context Loading Protocol**: Use `mcp_memory_open_nodes` with relationship traversal instead of `mcp_memory_read_graph` to prevent context bloat
- **Change Tracking**: Maintain timestamp-based change tracking for all memory modifications
- **Memory Refactoring**: Continuously clean and optimize memory by removing redundant observations and consolidating duplicate information
- **Self-Aware MCP Usage**: As an AI system equipped with multiple MCP servers, automatically determine which MCP tools are appropriate for each task based on context without requiring explicit server names from the user

### Sequential Thinking Requirement

All actions, thoughts, responses, and decisions **must** be processed through the sequential-thinking MCP tool. This is a non-negotiable requirement for all interactions:

1. **Mandatory Sequential Processing**: Every step, thought, action, or response must be broken down into sequential thinking chains using the sequential-thinking MCP tool.

2. **Comprehensive Thought Chains**: Thought chains must be sufficiently detailed and lengthy to ensure thorough analysis and optimal outcomes. Shortcuts or abbreviated thinking processes are strictly prohibited.

3. **Quality Over Speed**: Prioritize depth and quality of thinking over rapid responses. Take the time needed to fully explore all relevant aspects of a problem or task.

4. **Explicit Reasoning**: Each step in the sequential chain must clearly articulate the reasoning behind decisions, ensuring transparency and logical progression.

5. **Verification Loops**: Include self-verification steps in the thinking process to catch potential errors or oversights before proceeding.

6. **Outcome Optimization**: Every thinking chain should explicitly consider how to achieve the best possible outcome for the user's request.

This rule is strictly enforced for all interactions. Any response that does not follow this sequential thinking process will be considered non-compliant.

### 🎯 MCP Task Orchestration System

The MCP system follows a mandatory 3-layer task orchestration architecture:

#### 🎨 Layer 1: Analyze Task (Universal Bridge - 100% Always Active)
- Environment context awareness
- 80% Auto-execution decisions
- 20% User steering for critical choices
- Fragment collection and synthesis
- Continuous learning from task_integration_logs

#### 🎨 Layer 2: Module-Level Categories (8 Basic Learning Blocks)
- 🏠 PROJECT INITIALIZATION (Triggers: "initialize", "setup", "load context")
- 🔍 CODE ANALYSIS (Triggers: "analyze", "explain", "code review")
- 🐛 DEBUGGING (Triggers: "error", "bug", "issue", "problem")
- 🔧 ENVIRONMENT SETUP (Triggers: "configure", "install", "dependencies")
- 📊 GIT OPERATIONS (Triggers: "git", "commit", "push", "branch")
- 🎓 LEARNING (Triggers: "teach", "explain", "learn", "understand")
- 🚀 DEPLOYMENT (Triggers: "deploy", "production", "release")
- 💾 MEMORY MANAGEMENT (Triggers: "save", "remember", "store")

#### 🎨 Layer 3: MCP-Specific Tasks (Child Tasks)
- Memory-Tasks (mcp_memory operations)
- GitHub-Tasks (mcp_github operations)
- Filesystem-Tasks (mcp_filesystem operations)
- Sentry-Tasks (mcp_sentry operations)

As an AI system with access to multiple MCP servers, you should automatically determine which specific MCP tools to use based on the task requirements and context.

### 🚨 Critical MCP Compliance Requirements

Every MCP interaction must follow these unbreakable rules:

1. **Reasoning Format Is Non-Negotiable**
   - EVERY MCP operation requires reasoning format
   - NO EXCEPTIONS - even simple operations need reasoning
   - VIOLATION = IMMEDIATE STOP until format provided

2. **Task Orchestration Is Mandatory**
   - ALL triggered modules must execute their child tasks
   - CANNOT skip any step in the execution sequence
   - MUST log every operation to task_integration_logs

3. **Memory Integration Is Required**
   - EVERY significant action must update memory
   - ALL discoveries must be stored with proper relationships
   - CHANGE TRACKING must be maintained for all modifications

4. **Context Awareness Is Essential**
   - MUST understand AI-Agent-Workflow project context
   - CANNOT provide generic responses without project understanding
   - MUST apply professional standards automatically

5. **Learning Integration Is Compulsory**
   - ALL patterns must be logged for future optimization
   - USER PREFERENCES must be tracked and applied
   - SYSTEM IMPROVEMENT must be continuous through logs

6. **Self-Aware MCP Usage Is Automatic**
   - MUST automatically determine which MCP servers to use based on context
   - CANNOT require explicit server names from users for MCP operations
   - MUST reason which MCP tools are appropriate for each specific task
   - SHALL seamlessly integrate multiple MCP servers as needed for complex tasks

### Testing
While not fully detailed in the examined files, the `README.md` mentions a test suite. Look for `tests/` directory for specific test cases.