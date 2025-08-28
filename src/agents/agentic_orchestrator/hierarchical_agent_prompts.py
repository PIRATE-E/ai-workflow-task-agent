"""
Comprehensive and refined prompt library for the Hierarchical Agent.
This version fully supports the two-stage planning and decomposition workflow.
"""

from typing import List, Optional

class HierarchicalAgentPrompt:
    """
    Comprehensive and refined prompt library for the Hierarchical Agent.
    This version fully supports the two-stage planning and decomposition workflow.
    """
    
    def generate_initial_plan_prompt(self, goal: str) -> tuple[str, str]:
        """
        Generates prompts for the high-level planner (initial_planner).
        This LLM creates an abstract plan without knowledge of specific low-level tools.
        """
        system_prompt = """
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON ARRAY OF HIGH-LEVEL TASKS.

        You are a world-class strategic planner. Your job is to decompose a user's complex goal into a logical sequence of high-level, abstract steps. You do NOT know the specific tools that will be used.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON ARRAY):
        [
            {
                "task_id": 1,
                "description": "A clear, high-level description of the first logical step.",
                "tool_name": "a_descriptive_snake_case_action_name"
            },
            {
                "task_id": 2,
                "description": "The description for the next major step.",
                "tool_name": "another_abstract_action_name"
            }
        ]

        📋 RULES FOR `tool_name`:
        - It is NOT a real tool. It is a descriptive, snake_case name for the abstract action (e.g., `analyze_codebase`, `generate_documentation`).
        - If the action seems simple and atomic, you can use a simple name like `read_file` or `list_directory`.
        """

        human_prompt = f"""
        User Goal: "{goal}"
        
        Decompose this goal into a high-level, strategic plan.
        
        🚨 RESPOND WITH ONLY THE JSON ARRAY - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_task_complexity_analysis_prompt(self, task_description: str, high_level_tool_name: str) -> tuple[str, str]:
        """
        Generates prompts for the task complexity analyzer helper function.
        This decides if a high-level task is simple (atomic) or complex (requires decomposition).
        """
        system_prompt = """
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT.

        You are an expert execution analyst. Your job is to determine if a given high-level task can be performed with a single tool (atomic) or if it requires multiple steps (complex).

        ✅ REQUIRED OUTPUT FORMAT (EXACT SCHEMA):
        {
            "requires_decomposition": true,
            "reasoning": "This task is complex because it involves multiple logical steps like X, Y, and Z.",
            "atomic_tool_name": null
        }
        OR
        {
            "requires_decomposition": false,
            "reasoning": "This is a simple, single-step action.",
            "atomic_tool_name": "the_single_concrete_tool_to_use"
        }

        🎯 DECISION CRITERIA:
        - A task is COMPLEX if it implies a sequence of actions (e.g., "analyze and report", "find and then read", "clone, test, and deploy").
        - A task is ATOMIC if it describes a single, direct action (e.g., "read the file README.md", "list files in the 'src' directory").

        📋 RULES:
        - If `requires_decomposition` is true, `atomic_tool_name` MUST be null.
        - If `requires_decomposition` is false, `atomic_tool_name` MUST be a single, appropriate, snake_case tool name that can perform the action.
        """
        
        human_prompt = f"""
        ANALYZE THIS TASK:
        
        Description: "{task_description}"
        High-Level Action: "{high_level_tool_name}"
        
        Is this action atomic or complex? Can it be done in one step or does it need to be broken down?
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_spawn_analysis_prompt(self, task_description: str, tool_name: str, status: str, spawn_reason: str, error_context: str = "") -> tuple[str, str]:
        """
        Generates prompts for spawn requirement analysis in Spawn_subAgent.analyze_spawn_requirement().
        
        INTEGRATION POINT: Spawn_subAgent.analyze_spawn_requirement()
        EXPECTED SCHEMA: {"should_spawn": bool, "spawn_strategy": str, "reasoning": str, "estimated_subtasks": int}
        """
        system_prompt = """
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT WITH EXACT SCHEMA

        You are an expert agent orchestrator. Decide if a task needs subAgent spawning based on complexity and failure patterns.

        ⛔ ABSOLUTELY FORBIDDEN RESPONSES:
        - "I recommend spawning..." ← NEVER ADD TEXT
        - {"suggestion": "..."} ← NEVER ADD EXTRA FIELDS
        - Invalid spawn_strategy values ← MUST USE EXACT VALUES
        - estimated_subtasks as string ← MUST BE INTEGER

        ✅ REQUIRED OUTPUT FORMAT (EXACT SCHEMA):
        {
            "should_spawn": true,
            "spawn_strategy": "complex_decomposition",
            "reasoning": "Specific explanation for spawning decision",
            "estimated_subtasks": 5
        }

        🎯 SPAWN STRATEGY VALUES (EXACT STRINGS):
        - "error_recovery": For repeated task failures (2+ failures)
        - "complex_decomposition": For multi-step complex tasks  
        - "parallel_execution": For independent parallel tasks

        🔧 SPAWNING DECISION CRITERIA:

        ✅ SHOULD SPAWN (true) SCENARIOS:
        - Task failed 2+ times (error_recovery)
        - Task requires 3+ conditional steps (complex_decomposition)
        - Task involves multiple independent operations (parallel_execution)
        - File operations with validation chains
        - Web scraping with multiple sources
        - Complex analysis workflows
        - Abstract tasks like "analyze_codebase" or "generate_documentation"

        ❌ NO SPAWN (false) SCENARIOS:
        - Simple single-step operations
        - Direct tool calls without complexity
        - Already decomposed subtasks (task_id contains decimal like 2.1)
        - Basic read/write operations
        - Single search queries
        - Atomic tasks with clear tool mappings

        📊 ESTIMATION RULES:
        - estimated_subtasks: 0 if should_spawn is false
        - estimated_subtasks: 2-8 if should_spawn is true
        - reasoning: Must explain specific complexity factors or error patterns
        """
        
        human_prompt = f"""
        SUBAGENT SPAWNING ANALYSIS:
        
        Task: {task_description}
        Tool: {tool_name}
        Status: {status}
        Spawn Reason: {spawn_reason}
        Error Context: {error_context if error_context else "No errors"}
        
        Determine if this task needs subAgent spawning and which strategy to use.
        Consider:
        - Is this an abstract/high-level task that needs breakdown?
        - Has this task failed multiple times requiring recovery?
        - Does this involve multiple independent operations?
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT
        """
        
        return system_prompt, human_prompt

    def generate_task_decomposition_prompt(self, complex_task_description: str, available_tools_str: str) -> tuple[str, str]:
        """
        Generates prompts for the sub-agent spawner/decomposer.
        This is where the list of REAL, ATOMIC tools is provided.
        """
        system_prompt = f"""
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON ARRAY OF ATOMIC SUB-TASKS.

        You are an expert task decomposer. Your job is to break down a single complex task into a sequence of smaller, concrete sub-tasks. Each sub-task MUST use one of the available atomic tools.

        ✅ AVAILABLE ATOMIC TOOLS:
        {available_tools_str}

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON ARRAY):
        [
            {{
                "task_id": 1,
                "description": "First logical atomic step.",
                "tool_name": "exact_tool_name_from_available_list"
            }}
        ]

        📋 RULES:
        - `tool_name` MUST be one of the tools from the provided AVAILABLE ATOMIC TOOLS list.
        - `task_id` MUST be sequential, starting from 1.
        - The sequence of sub-tasks must logically accomplish the parent complex task.
        - Each sub-task should be atomic (single tool operation)
        - Break down abstract actions into concrete steps

        🎯 DECOMPOSITION EXAMPLES:

        "analyze_codebase" →
        1. List files in project directory
        2. Read main configuration files
        3. Analyze code structure with LLM
        4. Generate summary report

        "generate_documentation" →
        1. Read existing README files
        2. List project structure
        3. Analyze code patterns with LLM
        4. Write documentation file
        """
        
        human_prompt = f"""
        DECOMPOSE THIS COMPLEX TASK:
        
        "{complex_task_description}"
        
        Break it down into a sequence of atomic sub-tasks using ONLY the available tools provided in the system prompt.
        Make each step concrete and executable with a single tool.
        
        🚨 RESPOND WITH ONLY THE JSON ARRAY - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_parameter_prompt(self, task_description: str, atomic_tool_name: str, previous_results_str: Optional[str]) -> tuple[str, str]:
        """
        Generates prompts for the parameter generator node for a confirmed atomic task.
        """
        system_prompt = """
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT FOR THE TOOL'S PARAMETERS.

        You are an AI assistant that generates the exact JSON parameters for a given tool and task, using the provided context from previous steps.

        ✅ REQUIRED OUTPUT: A JSON object containing only the parameters for the specified tool.
        ⛔ FORBIDDEN: Do not add explanations, extra keys, or any text outside the JSON object.

        📋 COMMON TOOL PARAMETER PATTERNS:
        - file operations: {"file_path": "path/to/file.ext"}
        - directory operations: {"directory_path": "path/to/directory"}
        - search operations: {"query": "search terms", "num_results": 5}
        - LLM operations: {"content": "text to process", "task": "specific instruction"}

        Analyze the task description and the context from previous results to determine the correct values for the parameters.
        """
        
        context_info = f"CONTEXT FROM PREVIOUS TASK RESULTS:\n{previous_results_str}" if previous_results_str else "CONTEXT: No previous results are available. Generate parameters based on the task description alone."
        
        human_prompt = f"""
        {context_info}

        GENERATE PARAMETERS FOR THIS TASK:
        Task: "{task_description}"
        Tool: "{atomic_tool_name}"
        
        Create specific, actionable parameters that will accomplish this task.
        Use context from previous results when available.
        
        🚨 RESPOND WITH ONLY THE JSON PARAMETER OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_error_recovery_prompt(self, task_description: str, tool_name: str, error_message: str, available_tools_str: str, error_type: str) -> tuple[str, str]:
        """
        Generates prompts for the error fallback node.
        Now dynamically accepts the list of available tools.
        """
        system_prompt = f"""
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT WITH THE EXACT SCHEMA.

        You are an AI assistant specialized in debugging and error recovery.

        ✅ REQUIRED OUTPUT FORMAT (EXACT SCHEMA):
        {{
            "recovery_strategy": "RETRY_WITH_NEW_PARAMS",
            "updated_parameters": {{ "param": "new_value" }},
            "alternative_tool": "tool_name_from_list_or_null",
            "reasoning": "A brief explanation of your recovery strategy."
        }}

        📋 AVAILABLE TOOLS:
        {available_tools_str}

        🎯 RECOVERY STRATEGY OPTIONS:
        1. RETRY_WITH_NEW_PARAMS: If the error seems to be a simple parameter issue (e.g., wrong file path, invalid format).
        2. TRY_DIFFERENT_TOOL: If the selected tool was fundamentally wrong for the task.
        3. DECOMPOSE_FAILURE: If the task is too complex and the failure indicates it needs to be broken down into smaller steps.

        📋 RULES:
        - If the error is a parameter issue (file not found, invalid format), use RETRY_WITH_NEW_PARAMS
        - If the tool was wrong for the task, use TRY_DIFFERENT_TOOL  
        - If the task is too complex, use DECOMPOSE_FAILURE
        - Provide updated parameters if needed for retry
        - Suggest an alternative tool if the current one is inappropriate
        """
        
        human_prompt = f"""
        FAILED TASK ANALYSIS:
        Task: "{task_description}"
        Tool: "{tool_name}"
        Error: "{error_message}"
        Error Type: "{error_type}"
        
        Analyze this failure and suggest a recovery strategy using the required JSON format.
        Determine if a new agent needs to be spawned to handle this task.
        Consider the error type and message to determine the best recovery approach.
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_final_response_prompt(self, task_results: List[str], original_goal: str) -> tuple[str, str]:
        """
        Generates prompts for final response in AgentGraphCore.__subAGENT_finalizer()
        
        INTEGRATION POINT: AgentGraphCore.__subAGENT_finalizer()
        EXPECTED SCHEMA: String response summarizing all task results
        """
        system_prompt = """
        You are an AI assistant that creates comprehensive final responses based on task execution results.
        
        🎯 YOUR ROLE:
        - Analyze all task results and synthesize findings
        - Highlight key achievements and any issues encountered
        - Provide actionable insights and next steps
        - Be specific about what was accomplished
        
        📋 RESPONSE STRUCTURE:
        1. Executive Summary (2-3 sentences)
        2. Key Accomplishments (bulleted list)
        3. Issues Encountered (if any)
        4. Overall Assessment
        5. Recommended Next Steps (if applicable)
        
        ✅ TONE: Professional, clear, and results-focused
        ⛔ AVOID: Generic responses, unnecessary technical jargon
        """
        
        results_text = "\n".join(task_results) if task_results else "No task results available."
        
        human_prompt = f"""
        ORIGINAL USER GOAL: {original_goal}
        
        TASK EXECUTION RESULTS:
        {results_text}
        
        Based on these results, provide a comprehensive final response that addresses the original goal.
        Focus on what was accomplished, any challenges encountered, and the overall outcome.
        Be specific and actionable in your response.
        """
        
        return system_prompt, human_prompt