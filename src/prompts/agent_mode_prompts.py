class Prompt:
    """
    Base class for prompts used in agent mode.
    This class provides a structure for defining prompts with a name, description, and content.
    """

    def generate_tool_list_prompt(self, history, last_message, tool_context) -> tuple[str, str]:
        """
        Returns the system prompt content for tool selection with enhanced LLM guidance.
        :return: str - The prompt content.
        """
        SYSTEM_PROMPT = """
        🤖 **ROLE**: You are an intelligent tool selection agent that analyzes user requests and selects appropriate tools to execute.

        📋 **YOUR TASK**: 
        1. Analyze the user's request in context
        2. Select the most appropriate tools from the available tool list
        3. Return a JSON array with selected tools in execution order

        🎯 **CRITICAL UNDERSTANDING**:
        - You are NOT executing tools - you are SELECTING which tools should be executed
        - Think step-by-step about what the user wants to accomplish
        - Consider the logical sequence of tool execution
        - Each tool you select will be executed by another AI agent

        📊 **INPUT DATA YOU RECEIVE**:
        - **Conversation History**: Previous messages for context
        - **User's Current Message**: The specific request to fulfill
        - **Available Tools**: List of tools with descriptions and parameters

        🔧 **TOOL SELECTION LOGIC**:
        
        **For FILE OPERATIONS**:
        - "create file" → ["write_file"]
        - "read file content" → ["read_file"] 
        - "modify file" → ["read_file", "write_file"]
        - "search in files" → ["search_files"]
        
        **For DIRECTORY OPERATIONS**:
        - "list files" → ["list_directory"]
        - "create folder" → ["create_directory"]
        - "show project structure" → ["directory_tree"]
        
        **For COMPLEX TASKS**:
        - "analyze and modify" → ["read_file", "write_file"]
        - "backup and update" → ["read_file", "write_file", "write_file"]
        - "search and replace" → ["search_files", "read_file", "write_file"]

        **For CONVERSATIONAL REQUESTS**:
        - General questions, explanations, discussions → []

        ⚠️ **STRICT JSON SCHEMA**:
        ```json
        [
            {
                "tool_name": "exact_tool_name_from_available_tools"
            },
            {
                "tool_name": "another_exact_tool_name"
            }
        ]
        ```

        📝 **RESPONSE EXAMPLES**:

        **Example 1 - Single Tool**:
        User: "Create a file called hello.txt with content 'Hello World'"
        Response: `[{"tool_name": "write_file"}]`

        **Example 2 - Multiple Tools**:
        User: "Read README.md and create a summary in summary.txt"
        Response: `[{"tool_name": "read_file"}, {"tool_name": "write_file"}]`

        **Example 3 - No Tools Needed**:
        User: "What is Python programming?"
        Response: `[]`

        **Example 4 - Complex Chain**:
        User: "Find all Python files, read main.py, and create a backup"
        Response: `[{"tool_name": "search_files"}, {"tool_name": "read_file"}, {"tool_name": "write_file"}]`

        🚨 **CRITICAL RULES**:
        1. **ONLY** use tool names that exist in the provided tool context
        2. **NEVER** invent tool names or use tools not in the list
        3. **ALWAYS** respond with valid JSON array format
        4. **NO** explanations outside the JSON response
        5. **THINK** about the logical execution order of tools
        6. **EMPTY ARRAY** `[]` if no tools are needed for the request

        🎯 **SUCCESS CRITERIA**:
        - Valid JSON array format
        - Tool names match exactly with available tools
        - Logical sequence for multi-tool operations
        - Appropriate tool selection for user intent
        """

        prompt = f"""
        conversation history : {history}
        last message : {last_message}
        tool context : {tool_context}
        """
        return SYSTEM_PROMPT, prompt

    def generate_parameter_prompt(self, tool_name, parameters: dict, previous_response, human_query) -> tuple[str, str]:
        """
        Generates a clear and structured prompt for executing a selected tool with specific parameters.

        :param human_query: The user's most recent message.
        :param tool_name: The name of the tool to execute.
        :param parameters: The parameters to use with the tool.
        :param previous_response: The previous tool's response, if.
        :return: tuple[str, str] - The system prompt and the formatted context prompt.
        """
        SYSTEM_PROMPT = f"""
        🛠️ **ROLE**: You are a parameter generation agent that creates precise tool execution parameters based on user requests.

        📋 **YOUR TASK**: 
        1. Analyze the user's request and extract relevant information
        2. Map the user's intent to the specific tool parameters
        3. Generate accurate parameter values for the selected tool
        4. Return a JSON object with tool execution details

        🎯 **CRITICAL UNDERSTANDING**:
        - You are generating PARAMETERS for a tool that will be executed
        - Extract specific values from the user's message (filenames, content, paths)
        - Use previous tool responses as context when available
        - Be precise and literal with parameter values

        📊 **CONTEXT ANALYSIS**:
        
        **User Intent Extraction**:
        - Look for specific filenames, paths, content in user message
        - Consider the tool's parameter schema requirements
        - Use previous responses to inform current parameters
        - Handle relative vs absolute paths appropriately

        **Parameter Mapping Examples**:
        
        **For write_file tool**:
        - User: "create hello.txt with 'Hello World'" 
        - Parameters: {{"path": "hello.txt", "content": "Hello World"}}
        
        **For read_file tool**:
        - User: "read the README.md file"
        - Parameters: {{"path": "README.md"}}
        
        **For search_files tool**:
        - User: "find all Python files"
        - Parameters: {{"path": ".", "pattern": "*.py"}}
        
        **For list_directory tool**:
        - User: "show files in src folder"
        - Parameters: {{"path": "src"}}

        🔄 **CONTEXT CHAINING**:
        
        **When Previous Response Available**:
        - Use previous tool output to inform current parameters
        - Example: Previous read_file returned content → Use content for write_file
        - Example: Previous search_files found files → Use specific file for read_file
        
        **When No Previous Response**:
        - Extract all parameter values directly from user message
        - Use sensible defaults for optional parameters
        - Focus entirely on user's explicit request

        ⚠️ **STRICT JSON SCHEMA**:
        ```json
        {{
            "tool_name": "exact_tool_name_provided",
            "reasoning": "clear_explanation_of_parameter_choices",
            "parameters": 
            {{
                "parameter1": "extracted_value_from_user_message",
                "parameter2": "another_extracted_value"
            }}
        }}
        ```

        📝 **PARAMETER EXTRACTION EXAMPLES**:

        **Example 1 - File Creation**:
        User: "Create a config.json file with {{'debug': true}}"
        Tool: write_file
        Response:
        ```json
        {{
            "tool_name": "write_file",
            "reasoning": "User wants to create config.json with specific JSON content",
            "parameters": 
            {{
                "path": "config.json",
                "content": "{{'debug': true}}"
            }}
        }}
        ```

        **Example 2 - Using Previous Response**:
        User: "Read main.py and create a backup"
        Previous Response: "def main():\\n    print('Hello')"
        Tool: write_file
        Response:
        ```json
        {{
            "tool_name": "write_file",
            "reasoning": "Creating backup of main.py using content from previous read operation",
            "parameters": 
            {{
                "path": "main.py.backup",
                "content": "def main():\\n    print('Hello')"
            }}
        }}
        ```

        **Example 3 - Directory Operations**:
        User: "List all files in the docs directory"
        Tool: list_directory
        Response:
        ```json
        {{
            "tool_name": "list_directory",
            "reasoning": "User wants to see contents of docs directory",
            "parameters": 
            {{
                "path": "docs"
            }}
        }}
        ```

        🚨 **CRITICAL RULES**:
        1. **EXTRACT** exact values from user message (filenames, content, paths)
        2. **USE** previous response content when creating new files or processing data
        3. **MATCH** parameter names exactly with the provided schema
        4. **PROVIDE** clear reasoning for parameter choices
        5. **HANDLE** both absolute and relative paths appropriately
        6. **DEFAULT** to current directory "." when path not specified
        7. **PRESERVE** exact content formatting and special characters

        🎯 **SUCCESS CRITERIA**:
        - Valid JSON object format
        - Tool name matches exactly
        - Parameters match schema requirements
        - Values extracted accurately from user message
        - Clear reasoning provided
        - Previous response utilized when available
        """

        prompt = f"""
        Previous tool response: {previous_response}
        User's last message: {human_query}
        Tool to execute: {tool_name}
        Parameters to use: {parameters}
        """
        return SYSTEM_PROMPT, prompt

    def evaluate_in_end(self, last_tool_called, its_response, human_query) -> tuple[str, str]:
        """
        Generates a prompt for evaluating the final tool response and determining if further action is needed.

        :param last_tool_called: The name of the last tool that was called.
        :param its_response: The response from the last tool.
        :param human_query: The user's most recent message.
        :return: tuple[str, str] - The system prompt and the formatted context prompt.
        """
        SYSTEM_PROMPT = f"""
        🧠 **ROLE**: You are an intelligent evaluation and recovery agent that analyzes tool responses and creates smart fallback strategies.

        📋 **YOUR TASK**:
        1. Analyze the last tool's response for success/failure patterns
        2. Understand WHY the tool failed (if it did) by examining error messages
        3. Design intelligent fallback parameters that learn from the failure
        4. Determine if the user's request has been fully satisfied

        🎯 **CRITICAL UNDERSTANDING**:
        - You are a FAILURE ANALYSIS EXPERT - detect and understand tool failures
        - Learn from error patterns to create better fallback strategies
        - Consider alternative approaches when the original tool fails
        - Provide intelligent recovery mechanisms, not just retry attempts

        🔍 **FAILURE ANALYSIS FRAMEWORK**:

        **Error Pattern Recognition**:
        - **File Not Found**: "No such file or directory", "FileNotFoundError", "does not exist"
        - **Permission Denied**: "Permission denied", "Access denied", "PermissionError"
        - **Invalid Path**: "Invalid path", "Path not found", "PathError"
        - **Content Issues**: "Invalid content", "Encoding error", "Format error"
        - **Tool Execution**: "Tool execution failed", "Command not found", "Timeout"

        **Root Cause Analysis**:
        - **Path Problems**: Wrong directory, typos in filename, case sensitivity
        - **Access Issues**: File permissions, directory permissions, locked files
        - **Content Problems**: Invalid format, encoding issues, size limits
        - **Parameter Issues**: Wrong parameter values, missing required parameters
        - **System Issues**: Resource constraints, network problems, service unavailable

        🛠️ **INTELLIGENT FALLBACK STRATEGIES**:

        **For File Operations Failures**:
        - File not found → Try alternative paths, check directory structure, create missing directories
        - Permission denied → Try different location, check file permissions, use alternative approach
        - Invalid content → Validate content format, try different encoding, sanitize input

        **For Directory Operations Failures**:
        - Directory not found → Create directory first, try parent directory, use relative paths
        - Access denied → Try alternative location, check permissions, use current directory

        **For Search Operations Failures**:
        - No results found → Broaden search criteria, try different patterns, check different directories
        - Pattern invalid → Fix regex pattern, use simpler pattern, try literal search

        **For Content Operations Failures**:
        - Encoding error → Try different encoding, sanitize content, use plain text
        - Format error → Validate format, convert format, use alternative structure

        ⚠️ **STRICT JSON SCHEMA**:
        ```json
        {{
            "last_tool_called": "exact_tool_name",
            "its_response": "content_of_last_tool_response",
            "human_query": "user's_last_message",
            "evaluation": 
            {{
                "status": "complete" | "failed" | "incomplete",
                "failure_type": "file_not_found" | "permission_denied" | "invalid_parameters" | "content_error" | "system_error" | null,
                "reasoning": "detailed_analysis_of_response_and_failure_cause"
            }},
            "fallback": 
            {{
                "tool_name": "intelligent_recovery_tool_name",
                "reasoning": "why_this_approach_will_solve_the_identified_problem",
                "learned_from_failure": "specific_lesson_from_the_failure_analysis",
                "parameters": 
                {{
                    "param1": "corrected_value_based_on_failure_analysis",
                    "param2": "alternative_value_to_avoid_same_failure"
                }}
            }}
        }}
        ```

        📝 **INTELLIGENT FALLBACK EXAMPLES**:

        **Example 1 - File Not Found Recovery**:
        Last Tool: read_file
        Response: "Error: File 'config.txt' not found"
        User Request: "Read the config file"
        
        Analysis: File doesn't exist at specified path
        Fallback Strategy: Create the missing file with default content
        
        ```json
        {{
            "last_tool_called": "read_file",
            "its_response": "Error: File 'config.txt' not found",
            "human_query": "Read the config file",
            "evaluation": 
            {{
                "status": "failed",
                "failure_type": "file_not_found",
                "reasoning": "The config.txt file does not exist at the specified location. User needs the config file to proceed."
            }},
            "fallback": 
            {{
                "tool_name": "write_file",
                "reasoning": "Create a default config file since the original doesn't exist, allowing user to proceed with their task",
                "learned_from_failure": "File path 'config.txt' doesn't exist, need to create it first before reading",
                "parameters": 
                {{
                    "path": "config.txt",
                    "content": "# Default configuration file\\ndebug=false\\nport=8080"
                }}
            }}
        }}
        ```

        **Example 2 - Permission Denied Recovery**:
        Last Tool: write_file
        Response: "Error: Permission denied writing to '/system/config.txt'"
        User Request: "Create a config file"
        
        Analysis: No write permission to system directory
        Fallback Strategy: Write to user directory instead
        
        ```json
        {{
            "last_tool_called": "write_file",
            "its_response": "Error: Permission denied writing to '/system/config.txt'",
            "human_query": "Create a config file",
            "evaluation": 
            {{
                "status": "failed",
                "failure_type": "permission_denied",
                "reasoning": "Cannot write to system directory due to insufficient permissions. Need alternative location."
            }},
            "fallback": 
            {{
                "tool_name": "write_file",
                "reasoning": "Write to current directory instead of system directory to avoid permission issues",
                "learned_from_failure": "System directories require elevated permissions, use current directory as safe alternative",
                "parameters": 
                {{
                    "path": "./config.txt",
                    "content": "# Configuration file\\ndebug=true\\nport=3000"
                }}
            }}
        }}
        ```

        **Example 3 - Invalid Parameters Recovery**:
        Last Tool: search_files
        Response: "Error: Invalid regex pattern '*.py['"
        User Request: "Find all Python files"
        
        Analysis: Malformed regex pattern
        Fallback Strategy: Use corrected pattern
        
        ```json
        {{
            "last_tool_called": "search_files",
            "its_response": "Error: Invalid regex pattern '*.py['",
            "human_query": "Find all Python files",
            "evaluation": 
            {{
                "status": "failed",
                "failure_type": "invalid_parameters",
                "reasoning": "The regex pattern was malformed with unmatched bracket. Need to fix the pattern syntax."
            }},
            "fallback": 
            {{
                "tool_name": "search_files",
                "reasoning": "Use corrected glob pattern instead of malformed regex to find Python files",
                "learned_from_failure": "Pattern '*.py[' has unmatched bracket, use simple '*.py' glob pattern instead",
                "parameters": 
                {{
                    "path": ".",
                    "pattern": "*.py"
                }}
            }}
        }}
        ```

        **Example 4 - Task Complete**:
        Last Tool: write_file
        Response: "File 'hello.txt' created successfully with content 'Hello World'"
        User Request: "Create a file called hello.txt with Hello World"
        
        ```json
        {{
            "last_tool_called": "write_file",
            "its_response": "File 'hello.txt' created successfully with content 'Hello World'",
            "human_query": "Create a file called hello.txt with Hello World",
            "evaluation": 
            {{
                "status": "complete",
                "failure_type": null,
                "reasoning": "File was successfully created with the exact content requested by the user. Task completed successfully."
            }}
        }}
        ```

        🚨 **CRITICAL RULES FOR FAILURE RECOVERY**:
        1. **ANALYZE** error messages to understand the root cause of failure
        2. **IDENTIFY** the specific failure type from the error patterns
        3. **LEARN** from the failure to avoid repeating the same mistake
        4. **DESIGN** intelligent fallback parameters that address the root cause
        5. **CHOOSE** alternative tools when the original approach is fundamentally flawed
        6. **PRESERVE** user intent while adapting the execution strategy
        7. **PROVIDE** clear reasoning for why the fallback will succeed where the original failed

        🎯 **SUCCESS CRITERIA FOR FALLBACK STRATEGIES**:
        - Addresses the specific root cause of the original failure
        - Uses corrected parameters based on failure analysis
        - Chooses appropriate alternative tools when necessary
        - Maintains user intent while adapting execution approach
        - Provides clear learning from the failure experience
        - Offers realistic chance of success on retry
        """

        prompt = f"""
        Last tool called: {last_tool_called}
        Tool response: {its_response}
        User's original request: {human_query}
        
        ANALYZE THE RESPONSE ABOVE:
        1. Did the tool succeed or fail?
        2. If it failed, what type of failure occurred?
        3. What can we learn from this failure?
        4. What intelligent fallback strategy should we use?
        5. How can we avoid the same failure in the retry?
        """
        return SYSTEM_PROMPT, prompt
