"""Comprehensive and refined prompt library for the Hierarchical Agent.
This version fully supports the two-stage planning and decomposition workflow with enhanced context passing.
"""
from typing import Any


class HierarchicalAgentPrompt:
    """Comprehensive and refined prompt library for the Hierarchical Agent.
    This version fully supports the two-stage planning and decomposition workflow.
    """

    def generate_initial_plan_prompt(self, goal: str) -> tuple[str, str]:
        """Generates prompts for the high-level planner (initial_planner)."""
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

    def generate_task_decomposition_prompt(self, original_goal: str, complex_task_description: str, 
                                         available_tools_str: str, parent_context: dict | None, 
                                         depth: int = 0) -> tuple[str, str]:
        """
        Generates prompts for the sub-agent spawner/decomposer.
        This is where the list of REAL, ATOMIC tools is provided.
        **NEW**: Includes rich context from parent tasks and is depth-aware.
        """
        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            mode_prompt = '''
        --- ⚙️ FOCUSED WORKER DECOMPOSITION MODE (Strict) ---
        You are decomposing a sub-task. Your primary goal is to create a final, atomic, non-recursive plan.
        You have been given the **full list of available tools**. Use them to their maximum potential.
        Each sub-task YOU create MUST be accomplishable in a single tool call. Be extremely specific in the description.
        **CRITICAL:** This is the final level of decomposition. The plan you create will NOT be broken down further. Ensure it is fully executable as-is.
        '''
        else:
            mode_prompt = ""

        if parent_context and parent_context.get("completed_tasks_history"):
            context_summary_lines = []
            for task in parent_context["completed_tasks_history"]:
                if hasattr(task, 'execution_context') and task.execution_context and hasattr(task.execution_context, 'analysis') and task.execution_context.analysis:
                    context_summary_lines.append(f"- Task {task.task_id} ({task.tool_name}): {task.execution_context.analysis}")
            context_summary = "\n".join(context_summary_lines)
            context_section = f"""
        CONTEXT FROM PREVIOUSLY COMPLETED TASKS:
        {context_summary}

        --- CRITICAL INSTRUCTION ---
        Assume all information provided in the "CONTEXT FROM PREVIOUSLY COMPLETED TASKS" is accurate and represents fully achieved objectives.
        Your sole responsibility is to plan the *next* logical steps to accomplish the complex task, building directly upon this context.
        Do NOT re-evaluate or attempt to "fix" past steps. Trust that previous tools have completed their work correctly.
        ---------------------------

        Based on this, plan the *next* logical steps to accomplish the complex task. Do NOT repeat actions that are already completed.
        """
        else:
            context_section = "CONTEXT: This is the first step. Plan the initial actions to accomplish the complex task."

        system_prompt = f"""
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON ARRAY OF ATOMIC SUB-TASKS.

        You are an expert task decomposer. Your job is to break down a single complex task into a sequence of smaller, concrete sub-tasks. Each sub-task MUST use one of the available atomic tools.

        {mode_prompt}

        The user's high-level objective is: "{original_goal}".
        The complex task to decompose is: "{complex_task_description}"

        {context_section}

        ✅ AVAILABLE ATOMIC TOOLS:
        {available_tools_str}

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON ARRAY):
        [
            {{
                "description": "First logical atomic step.",
                "tool_name": "exact_tool_name_from_available_list"
            }}
        ]

        📋 RULES:
        - `tool_name` MUST be one of the tools from the provided AVAILABLE ATOMIC TOOLS list.
        - The sequence of sub-tasks must logically accomplish the parent complex task.
        - Each sub-task should be atomic (single tool operation).
        - **Do not create sub-tasks for work that is already done according to the context.**
        - Do not include a `task_id` in the output.
        
        📋 NEW RULE: THE "COLLECTOR" PATTERN
        If a future sub-task requires the combined output of several previous sub-tasks, you MUST insert a dedicated "Collector" task right before it.
        - The "Collector" task MUST use the `sequentialthinking` tool.
        - Its `description` MUST clearly state its job: to gather and synthesize the results from the previous steps.
        - Example: {{'description': 'Review raw results from previous search sub-tasks and synthesize into a single comprehensive summary.', 'tool_name': 'sequentialthinking'}}
        """

        human_prompt = f"""
        DECOMPOSE THIS COMPLEX TASK:
        
        "{complex_task_description}"
        
        Break it down into a sequence of atomic sub-tasks using ONLY the available tools provided in the system prompt.
        Make each step concrete and executable with a single tool.
        
        🚨 RESPOND WITH ONLY THE JSON ARRAY - NO OTHER TEXT.
        """

        return system_prompt, human_prompt

    def generate_schema_aware_parameter_prompt(self, task_description: str, tool_name: str,
                                             tool_schema: dict, context: str | None = None, full_history: list[Any] | None = None, depth: int = 0) -> tuple[str, str]:
        """Generate parameters with full knowledge of tool schema and dual context.
        """
        required_params = tool_schema.get("required", [])
        all_params = tool_schema.get("properties", {})
        param_descriptions = {name: info.get("description", "No description") for name, info in all_params.items()}

        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            mode_prompt = """
        --- ⚙️ FOCUSED WORKER MODE ---
        You are generating parameters for a focused sub-task. Be direct and literal. Do not infer complex logic or file paths. If context is missing, use simple defaults.
        """
        else:
            mode_prompt = """
        ---  STRATEGIST MODE ---
        You are generating parameters for a high-level task. You can use the context to infer logical parameters.
        """

        system_prompt = f"""
        😎 DUAL CONTEXT & SCHEMA-AWARE PARAMETER GENERATOR
        {mode_prompt}
        You have two sources of context: a concise summary of past actions and the full, raw results.

        --- YOUR TASK ---
        1.  **Understand History:** Use the `CONTEXT FROM PREVIOUS STEP SUMMARIES` to understand what has already been accomplished.
        2.  **Avoid Repetition:** Your primary goal is to NOT repeat work.
        3.  **Source Data Correctly:** When a tool needs data from a previous step (e.g., `write_file` needs content), you MUST source that data from the `FULL RAW RESULTS OF PREVIOUS TASKS`.
        4.  **Generate Parameters:** Create a valid JSON object for the tool `{tool_name}` based on its schema.

        --- TOOL SCHEMA for `{tool_name}` ---
        - Required Parameters: {required_params}
        - Parameter Details: {param_descriptions}

        --- ✍️ RULE FOR CONTENT-BASED PARAMETERS ---
        If you are generating parameters for a tool that requires a large block of text content (e.g., the 'content' parameter for the `write_file` tool), you MUST check the `CONTEXT FROM PREVIOUS STEP SUMMARIES`.
        If a preceding task used the `sequentialthinking` tool and its purpose was to "summarize", "collect", or "synthesize" information, you MUST use the `FULL RAW RESULT` of THAT specific `sequentialthinking` task as the value for the 'content' parameter.
        Do not try to re-summarize or use the results of other, earlier tasks. Use the output of the dedicated Collector task.

        😡 CRITICAL RULE: For parameters like `content`, `text`, or `data`, you must reference the full, raw result of a previous task, NOT the summary. For parameters like `file_path` or `query`, you can infer them from the task description and the context summaries.
        """

        context_summary_section = f"""
        --- CONTEXT FROM PREVIOUS STEP SUMMARIES ---
        {context}
        """ if context else "--- CONTEXT: No previous results available. Generate parameters based on the task description alone. ---"

        raw_history_section = ""
        if full_history:
            raw_history_preview = []
            for task in full_history:
                if hasattr(task, 'execution_context') and task.execution_context and hasattr(task.execution_context, 'result') and task.execution_context.result:
                    raw_history_preview.append(f"- Task {task.task_id} ({task.tool_name}) Raw Result (Truncated): {task.execution_context.result[:200]}...")
            if raw_history_preview:
                raw_history_section = f"""
        --- FULL RAW RESULTS OF PREVIOUS TASKS (for data sourcing) ---
        (You have access to the full, untruncated results of these tasks)
        {"\n".join(raw_history_preview)}
        """

        # Specific instruction for Collector tasks using sequentialthinking
        collector_instruction = ""
        if tool_name == "sequentialthinking" and "Collector" in task_description:
            collector_instruction = f"""
        --- COLLECTOR TASK INSTRUCTION ---
        This is a "Collector" task. Your goal is to synthesize the raw results from previous tasks into a single, comprehensive output.
        You MUST review the `FULL RAW RESULTS OF PREVIOUS TASKS` section. For each relevant task (e.g., `GoogleSearch`, `read_text_file`), extract the *full, raw text content* of its `result` field.
        Concatenate ALL extracted raw text content into the `thought` parameter.
        Do NOT summarize or extract only specific fields (like 'summary') unless explicitly instructed by the task description.
        Ensure the `thought` parameter contains the complete, aggregated raw data from all relevant previous tasks.
        """

        human_prompt = f"""
        {context_summary_section}
        {raw_history_section}
        {collector_instruction}

        --- CURRENT TASK ---
        Task: "{task_description}"
        Tool: "{tool_name}"
        
        Generate the precise JSON parameters for this tool.
        
        😡 RESPOND WITH ONLY THE JSON PARAMETER OBJECT - NO OTHER TEXT.
        """

        return system_prompt, human_prompt

    def generate_context_synthesis_prompt(self, tool_name: str, raw_result: str, depth: int = 0) -> tuple[str, str]:
        """Generates prompts for the context synthesizer node."""
        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            # For sub-tasks, the summary is for the machine, so be technical.
            system_prompt = """
        You are a technical analysis AI. Your job is to take the raw output from a tool and create a factual, one-sentence summary of its outcome for machine processing.
        Be factual and brief. Example: "Tool 'search_issues' ran, returned 15 items."
        🚨 CRITICAL: Your response MUST be a single, concise sentence.
        """
        else:
            # For parent tasks, the summary can be more descriptive for the user.
            system_prompt = """
        You are an expert analysis AI. Your job is to take the raw output from a tool execution and create a concise, one-sentence summary of its outcome.
        The summary should be in the past tense and clearly state what was accomplished.

        EXAMPLE:
        - Tool: list_directory
        - Raw Result: ["file1.py", "src/", "README.md"]
        - Your Summary: "The directory was listed, revealing two python files and a 'src' directory."

        🚨 CRITICAL: Your response MUST be a single, concise sentence.
        """

        human_prompt = f"""
        TOOL EXECUTED: {tool_name}

        RAW RESULT:
        ---
        {raw_result}
        ---
        (Note: Result may be truncated for brevity)

        Based on the tool and its raw result, generate a one-sentence summary of what was accomplished.
        🚨 RESPOND WITH ONLY THE SUMMARY SENTENCE - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_final_response_prompt(self, task_results: list[str], original_goal: str) -> tuple[str, str]:
        system_prompt = """
        🚨 CRITICAL: YOU MUST RETURN EXACTLY ONE JSON OBJECT MATCHING THE SCHEMA BELOW.

        You are an AI assistant that creates a comprehensive final response based on the provided task execution results.
        Your output MUST be a single JSON object that conforms exactly to the schema described in the OUTPUT FORMAT section.

        OUTPUT FORMAT (EXACT SCHEMA):
        {{
          "user_response": {{
            "message": "string (1-4000 chars) - human-friendly summary of what was accomplished",
            "next_steps": "string (0-1000 chars) - 1-2 concrete next steps or an empty string"
          }},
          "analysis": {{
            "issues": "string (describe up to 2 issues found, or an empty string)",
            "reason": "string (why the issues occurred and suggested mitigation, or empty string)"
          }}
        }}

        STRICT RULES:
        - Return ONLY the JSON object and NOTHING ELSE (no commentary, no code fences).
        - All keys in the schema MUST be present. Use empty strings for optional/empty values.
        - All values MUST be strings.
        - Keep the response concise and user-facing in `user_response.message`.

        PURPOSE:
        - This structured response will be rendered directly to the user. Follow the schema precisely so the caller
          can extract `user_response.message` for display and `user_response.next_steps` for guidance.
        """
        results_text = "\n".join(task_results) if task_results else "No task results available."
        human_prompt = f"""
        ORIGINAL USER GOAL: {original_goal}

        TASK EXECUTION RESULTS:
        {results_text}

        Using the provided results, generate the final response that conforms exactly to the JSON schema specified in the system prompt.
        Make `user_response.message` a clear, human-friendly summary and `user_response.next_steps` 1-2 actionable steps (or empty string).

        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_tool_aware_initial_plan_prompt(self, goal: str, available_tools_context: str, error_feedback: str | None = None) -> tuple[str, str]:
        feedback_section = """
        --- PREVIOUS ATTEMPT FAILED ---
        Your last attempt to create a plan failed for the following reason:
        {error_feedback}
        Please analyze this feedback and generate a new, corrected plan that resolves this issue.
        ---
        """ if error_feedback else ""

        system_prompt = f"""
        🚨 CRITICAL: YOU MUST RETURN A JSON ARRAY OF TASKS USING ONLY REAL, AVAILABLE TOOLS.

        You are a strategic planner with complete knowledge of the available tool ecosystem.
        Your job is to decompose complex goals into executable tasks using ONLY the tools provided below.

        {feedback_section}

        ✅ AVAILABLE TOOLS:
        {available_tools_context}

        --- 📋 STRICT RULES FOR TOOL SELECTION ---
        1.  **Semantic Match is CRITICAL:** The tool you choose MUST be able to perform the action in the description. Do not assign a tool that cannot logically achieve the task's goal.
        2.  **Synthesis/Analysis Task Rule:** For any task that involves summarizing, analyzing, reviewing, combining, or creating a report from previous results, you MUST use the `sequentialthinking` tool. This is the designated "Collector" and "Synthesizer" tool.
        3.  **File System Task Rule:** Tools like `list_directory`, `read_text_file`, and `write_file` can ONLY be used for their specific file system purpose. They CANNOT be used to analyze or summarize content.

        --- ❌ EXAMPLES OF INCORRECT ASSIGNMENTS (DO NOT DO THIS) ---
        - {{'description': 'Summarize the findings', 'tool_name': 'list_directory'}}  <-- WRONG! list_directory cannot summarize.
        - {{'description': 'Analyze the code for bugs', 'tool_name': 'read_text_file'}} <-- WRONG! read_text_file cannot analyze.

        --- ✅ EXAMPLES OF CORRECT ASSIGNMENTS ---
        - {{'description': 'List the files in the root directory', 'tool_name': 'list_directory'}}
        - {{'description': 'Read the content of the README.md file', 'tool_name': 'read_text_file'}}
        - {{'description': 'Review the search results and create a summary report', 'tool_name': 'sequentialthinking'}}

        ✅ REQUIRED OUTPUT FORMAT:
        [{{"task_id": 1, "description": "Specific description of what this tool will accomplish", "tool_name": "exact_tool_name_from_available_list"}}]

        📋 NEW RULE: THE "COLLECTOR" PATTERN
        If a future task requires the combined output of several previous tasks (e.g., writing a final report, summarizing multiple sources), you MUST insert a dedicated "Collector" task right before it.
        - The "Collector" task MUST use the `sequentialthinking` tool.
        - Its `description` MUST clearly state its job: to gather and synthesize the results from the previous steps.
        - Example: {{'description': 'Review raw results from previous search tasks and synthesize into a single comprehensive summary.', 'tool_name': 'sequentialthinking'}}
        """
        human_prompt = f"""
        USER GOAL: "{goal}" 
        
        Create a step-by-step plan using ONLY the available tools listed in the system prompt.
        🚨 RESPOND WITH ONLY THE JSON ARRAY - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_tool_schema_complexity_prompt(self, task_description: str, tool_name: str,
                                             tool_schema: dict, depth: int) -> tuple[str, str]:
        schema_desc = tool_schema.get('description', 'No description')
        schema_props = tool_schema.get('properties', {})

        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            # This is a sub-task. Be strict and avoid further recursion.
            system_prompt = f"""
        🎯 FOCUSED SUB-TASK ANALYZER (Strict Mode)

        You are analyzing a SUB-TASK that was already created to solve a more complex parent task.
        Your primary goal is to PREVENT infinite recursion.

        --- CRITICAL RULE ---
        Your bias MUST be heavily towards `requires_decomposition: false`.
        Only return `true` if it is ABSOLUTELY IMPOSSIBLE to execute the task with a single call to the assigned tool.
        Simple tasks like formulating a query or reviewing text should ALWAYS be considered atomic (`false`).

        TOOL INFORMATION:
        - Tool Name: {tool_name}
        - Tool Description: {schema_desc}
        - Required Parameters: {list(schema_props.keys())}
        
        ✅ OUTPUT FORMAT:
        {{"requires_decomposition": boolean, "reasoning": "Specific analysis", "atomic_tool_name": "{tool_name}" or null, "estimated_subtasks": number_if_complex}}
        """
        else:
            # This is a parent task. Standard analysis is fine.
            system_prompt = f"""
        🎯 TOOL-SCHEMA-AWARE COMPLEXITY ANALYZER (Standard Mode)
        
        You are analyzing whether a task can be completed with a single tool call or requires decomposition.
        
        TOOL INFORMATION:
        - Tool Name: {tool_name}
        - Tool Description: {schema_desc}
        - Required Parameters: {list(schema_props.keys())}

        ✅ OUTPUT FORMAT:
        {{"requires_decomposition": boolean, "reasoning": "Specific analysis", "atomic_tool_name": "{tool_name}" or null, "estimated_subtasks": number_if_complex}}
        """
        # --- END OF NEW LOGIC ---

        human_prompt = f"""
        ANALYZE THIS TASK:
        
        Task: "{task_description}"
        Assigned Tool: "{tool_name}"
        
        Can this tool directly accomplish this task in a single call, or does it need decomposition?
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_parameter_prompt(self, task_description: str, atomic_tool_name: str, previous_results_str: str | None) -> tuple[str, str]:
        """Generates prompts for the parameter generator node for a confirmed atomic task.
        """
        system_prompt = """
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT FOR THE TOOL'S PARAMETERS.

        You are an AI assistant that generates the exact JSON parameters for a given tool and task, using the provided context from previous steps.

        ✅ REQUIRED OUTPUT: A JSON object containing only the parameters for the specified tool.
        ⛔ FORBIDDEN: Do not add explanations, extra keys, or any text outside the JSON object.

        📋 COMMON TOOL PARAMETER PATTERNS:
        - file operations: {{"file_path": "path/to/file.ext"}}
        - directory operations: {{"directory_path": "path/to/directory"}}
        - search operations: {{"query": "search terms", "num_results": 5}}
        - LLM operations: {{"content": "text to process", "task": "specific instruction"}}

        Analyze the task description and the context from previous results to determine the correct values for the parameters.
        """

        context_info = f"CONTEXT FROM PREVIOUS TASK RESULTS:\n{previous_results_str}" if previous_results_str else "CONTEXT: No previous results are available. Generate parameters based on the task description alone."

        human_prompt = f"""
        {context_info}

        GENERATE PARAMETERS FOR THIS TASK:
        Task: \"{task_description}\"\nTool: \"{atomic_tool_name}\"\n        
        Create specific, actionable parameters that will accomplish this task.
        Use context from previous results when available.
        
        🚨 RESPOND WITH ONLY THE JSON PARAMETER OBJECT - NO OTHER TEXT.
        """

        return system_prompt, human_prompt

    def generate_error_recovery_prompt(self, original_goal: str, task_description: str, tool_name: str,
                                       error_message: str, failed_parameters: dict, available_tools_str: str,
                                       error_type: str, operating_system: str, depth: int = 0) -> tuple[str, str]:
        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            # For sub-tasks, strongly discourage further decomposition.
            strategy_prompt = """
        --- ⚙️ FOCUSED WORKER RECOVERY MODE ---
        This is a sub-task failure. Your primary goal is to recover with a simple, alternative tool or by retrying with corrected parameters.
        You should strongly AVOID decomposing the task further (`DECOMPOSE_FAILURE`) unless it is the only possible option.
        """
        else:
            strategy_prompt = ""

        system_prompt = f"""
        🚨 CRITICAL ALERT: YOU MUST RETURN EXACTLY ONE JSON OBJECT WITH THE EXACT SCHEMA.

        You are an expert troubleshooter. A task has failed. Suggest a concrete recovery plan.
        {strategy_prompt}
        ✅ REQUIRED OUTPUT FORMAT (EXACT SCHEMA):
        {{"recovery_strategy": "RETRY_WITH_NEW_PARAMS", "updated_parameters": {{ "param": "new_value" }}, "alternative_tool": "tool_name_from_list_or_null", "reasoning": "A brief explanation."}}
        📋 AVAILABLE TOOLS FOR RECOVERY:
        {available_tools_str}
        """
        human_prompt = f"""
        --- FAILURE ANALYSIS ---
        Original Goal: "{original_goal}"
        Failed Task: "{task_description}"
        Tool Used: "{tool_name}"
        Error: "{error_message}"
        Parameters Used: {failed_parameters}
        ---
        Suggest a recovery strategy using the required JSON format.
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_parameter_repair_prompt(self, task_description: str, tool_name: str, tool_schema: dict, failed_parameters: dict, error_message: str) -> tuple[str, str]:
        """Generates a prompt to ask the LLM to repair failed parameters."""
        system_prompt = f"""
        You are a parameter correction expert. A tool failed due to bad parameters.
        Your job is to analyze the tool's schema, the failed parameters, and the error message, then provide a corrected set of parameters.

        TOOL SCHEMA for `{tool_name}`:
        {tool_schema}

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {{
            "repaired_parameters": {{ "param1": "new_value", ... }}
        }}
        """
        human_prompt = f"""
        --- FAILURE ANALYSIS ---
        Task: "{task_description}"
        Tool: "{tool_name}"
        Failed Parameters: {failed_parameters}
        Error Message: "{error_message}"
        ---
        Based on the schema and the error, correct the parameters.
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_alternative_tool_prompt(self, task_description: str, failed_tool: str, error_message: str, available_tools_str: str) -> tuple[str, str]:
        """Generates a prompt to ask the LLM for a safer, alternative tool."""
        system_prompt = f"""
        You are a strategic recovery expert. A task failed. Your job is to suggest a single, safer, alternative tool that might accomplish the task's goal without causing the same error.

        AVAILABLE TOOLS:
        {available_tools_str}

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {{
            "alternative_tool": "tool_name_from_list_or_null",
            "reasoning": "A brief explanation for your choice."
        }}
        """
        human_prompt = f"""
        --- FAILURE ANALYSIS ---
        Task: "{task_description}"
        Failed Tool: "{failed_tool}"
        Error Message: "{error_message}"
        ---
        Suggest a single, simpler, or safer alternative tool from the available list that could achieve the task's original intent.
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        return system_prompt, human_prompt

    def generate_goal_achievement_prompt(self, original_goal :str, plan_created: str, task_description: str, tool_result: str, analysis: str) -> tuple[str, str]:
        """Generates prompts for the goal achievement validation node."""
        system_prompt = """
                You are a pragmatic validation expert. Your job is to determine if a task's goal was reasonably achieved based on two independent signals: the adequacy of the plan used and the success of the tool execution.
        
                ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
                {{
                    "goal_achieved": boolean,
                    "reasoning": "A brief, clear explanation for your decision."
                }}
        
                --- DECISION RULES (PREVENT PREMATURE VERIFICATION) ---
                - Evaluate TWO dimensions separately:
                  1. Plan adequacy: Was the plan or chosen approach appropriate and sufficient to accomplish the task goal?
                  2. Tool execution: Did the tool run successfully (no errors) and produce results consistent with the task's intent?
                - Set `goal_achieved` to `true` **ONLY IF BOTH**:
                  - the plan is appropriate for the goal, and
                  - the tool executed successfully and produced reasonable, relevant output.
                - Set `goal_achieved` to `false` if **EITHER**:
                  - the plan is clearly unsuitable or wrong for achieving the goal (even if the tool ran), or
                  - the tool execution failed, returned an error, or returned no usable data (even if the plan was appropriate).
                - Do NOT mark `true` based on assumptions, partial outputs, or formatting fixes. Require explicit evidence for both plan correctness and execution success.
                - In `reasoning`, briefly state which dimension(s) passed or failed (e.g., "plan failed: wrong approach" or "execution failed: tool error 'X' "), then one-line justification.
                """

        human_prompt = f"""
                --- TASK VALIDATION ---
                
                USER GOAL:
                `{original_goal}`
        
                ORIGINAL PLAN:
                `{plan_created}`
        
                TASK GOAL:
                `{task_description}`
        
                TOOL RESULT:
                `{tool_result}`
        
                RESULT ANALYSIS:
                `{analysis}`
        
                --- QUESTION ---
                Considering both the ORIGINAL PLAN and the TOOL RESULT above, did the tool execute successfully in order to accomplish the user final goal and was the chosen plan adequate so the task goal was achieved?
        
                🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
                """

        return system_prompt, human_prompt
