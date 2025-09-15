"""Comprehensive and refined prompt library for the Hierarchical Agent.
This version fully supports the two-stage planning and decomposition workflow with enhanced context passing.
"""
from typing import Any


class HierarchicalAgentPrompt:
    """Comprehensive and refined prompt library for the Hierarchical Agent.
    This version fully supports the two-stage planning and decomposition workflow.
    """

    

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
                if hasattr(task, 'execution_context') and task.execution_context and hasattr(task.execution_context,
                                                                                             'analysis') and task.execution_context.analysis:
                    context_summary_lines.append(
                        f"- Task {task.task_id} ({task.tool_name}): {task.execution_context.analysis}")
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
        - The "Collector" task MUST use the `perform_synthesis` tool.
        - Its `description` MUST clearly state its job: to gather and synthesize the results from the previous steps.
        - Example: {{'description': 'Review raw results from previous search sub-tasks and synthesize into a single comprehensive summary.', 'tool_name': 'perform_synthesis'}}
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
                                               tool_schema: dict, context: str | None = None,
                                               full_history: list[Any] | None = None, depth: int = 0) -> tuple[str, str]:
        """Generate parameters with full knowledge of tool schema and dual context.
        """
        required_params = tool_schema.get("required", [])
        all_params = tool_schema.get("properties", {})
        param_descriptions = {name: info.get("description", "No description") for name, info in all_params.items()}

        # --- NEW: Depth-Aware System Prompt ---
        if depth >= 1:
            mode_prompt = '''
            --- ⚙️ FOCUSED WORKER MODE ---
            You are generating parameters for a focused sub-task. Be direct and literal. Do not infer complex logic or file paths. If context is missing, use simple defaults.
            '''
        else:
            mode_prompt = '''
            ---  STRATEGIST MODE ---
            You are generating parameters for a high-level task. You can use the context to infer logical parameters.
            '''

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
            If a preceding task used the `perform_synthesis` tool and its purpose was to "summarize", "collect", or "synthesize" information, you MUST use the `FULL RAW RESULT` of THAT specific `perform_synthesis` task as the value for the 'content' parameter.
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
                if hasattr(task, 'execution_context') and task.execution_context and hasattr(task.execution_context,
                                                                                             'result') and task.execution_context.result:
                    raw_history_preview.append(
                        f"- Task {task.task_id} ({task.tool_name}) Raw Result: {task.execution_context.result}...")
            if raw_history_preview:
                joint_preview = "\n".join(raw_history_preview)
                raw_history_section = f"""
             --- FULL RAW RESULTS OF PREVIOUS TASKS (for data sourcing) ---
             (You have access to the full, untruncated results of these tasks)
             {joint_preview}
             """

            # Specific instruction for Collector tasks using perform_synthesis
        collector_instruction = ""
        if tool_name == "perform_synthesis" and "Collector" in task_description:
            collector_instruction = f"""
             --- COLLECTOR TASK INSTRUCTION ---
             This is a "Collector" task. Your goal is to synthesize the raw results from previous tasks into a single, comprehensive output.
             You MUST review the `FULL RAW RESULTS OF PREVIOUS TASKS` section. For each relevant task (e.g., `google_search`, `read_text_file`), extract the *full, raw text content* of its `result` field.
             Do NOT paste raw content into parameters; instead, set the `instructions` to clearly state how to aggregate and summarize the data (for example, "Summarize each topic into 10 lines").
             If needed, include `per_item_lines` and `output_format` to constrain the output.
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
            system_prompt = '''
            You are a technical analysis AI. Your job is to take the raw output from a tool and create a factual, one-sentence summary of its outcome for machine processing.
            Be factual and brief. Example: "Tool 'search_issues' ran, returned 15 items."
            🚨 CRITICAL: Your response MUST be a single, concise sentence.
            '''
        else:
            # For parent tasks, the summary can be more descriptive for the user.
            system_prompt = '''
            You are an expert analysis AI. Your job is to take the raw output from a tool execution and create a concise, one-sentence summary of its outcome.
            The summary should be in the past tense and clearly state what was accomplished.
    
            EXAMPLE:
            - Tool: list_directory
            - Raw Result: ["file1.py", "src/", "README.md"]
            - Your Summary: "The directory was listed, revealing two python files and a 'src' directory."
    
            🚨 CRITICAL: Your response MUST be a single, concise sentence.
            '''

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
        system_prompt = '''
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
            '''
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


    def generate_tool_aware_initial_plan_prompt(self, goal: str, available_tools_context: str,
                                                error_feedback: str | None = None) -> tuple[str, str]:
        feedback_section = '''
            --- PREVIOUS ATTEMPT FAILED ---
            Your last attempt to create a plan failed for the following reason:
            {error_feedback}
            Please analyze this feedback and generate a new, corrected plan that resolves this issue.
            ---
            ''' if error_feedback else ""

        system_prompt = f"""
            🚨 CRITICAL: YOU MUST RETURN A JSON ARRAY OF TASKS USING ONLY REAL, AVAILABLE TOOLS.
    
            You are a strategic planner with complete knowledge of the available tool ecosystem.
            Your job is to decompose complex goals into executable tasks using ONLY the tools provided below.
    
            {feedback_section}
    
            ✅ AVAILABLE TOOLS:
            {available_tools_context}
    
            --- 📋 STRICT RULES FOR TOOL SELECTION ---
            1.  **Semantic Match is CRITICAL:** The tool you choose MUST be able to perform the action in the description. Do not assign a tool that cannot logically achieve the task's goal.
            2.  **Synthesis/Analysis Task Rule:** For any task that involves summarizing, analyzing, reviewing, combining, or creating a report from previous results, you MUST use the `perform_synthesis` tool. This is the designated "Collector" and "Synthesizer" tool.
            3.  **File System Task Rule:** Tools like `list_directory`, `read_text_file`, and `write_file` can ONLY be used for their specific file system purpose. They CANNOT be used to analyze or summarize content.
    
            --- ❌ EXAMPLES OF INCORRECT ASSIGNMENTS (DO NOT DO THIS) ---
            - {{'description': 'Summarize the findings', 'tool_name': 'list_directory'}}  <-- WRONG! list_directory cannot summarize.
            - {{'description': 'Analyze the code for bugs', 'tool_name': 'read_text_file'}} <-- WRONG! read_text_file cannot analyze.
    
            --- ✅ EXAMPLES OF CORRECT ASSIGNMENTS ---
            - {{'description': 'List the files in the root directory', 'tool_name': 'list_directory'}}
            - {{'description': 'Read the content of the README.md file', 'tool_name': 'read_text_file'}}
            - {{'description': 'Review the search results and create a summary report', 'tool_name': 'perform_synthesis'}}
    
            ✅ REQUIRED OUTPUT FORMAT:
            [{{"task_id": 1, "description": "Specific description of what this tool will accomplish", "tool_name": "exact_tool_name_from_available_list"}}]
    
            📋 NEW RULE: THE "COLLECTOR" PATTERN
            If a future task requires the combined output of several previous tasks (e.g., writing a final report, summarizing multiple sources), you MUST insert a dedicated "Collector" task right before it.
            - The "Collector" task MUST use the `perform_synthesis` tool.
            - Its `description` MUST clearly state its job: to gather and synthesize the results from the previous steps.
            - Example: {{'description': 'Review raw results from previous search tasks and synthesize into a single comprehensive summary.', 'tool_name': 'perform_synthesis'}}
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
            system_prompt = f'''
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
            {{ 
                "requires_decomposition": boolean,
                "reasoning": "Specific analysis",
                "atomic_tool_name": "{tool_name}" or null,
                "estimated_subtasks": number_if_complex
            }}
            '''
        else:
            # This is a parent task. Standard analysis is fine.
            system_prompt = f'''
            🎯 TOOL-SCHEMA-AWARE COMPLEXITY ANALYZER (Standard Mode) 
            
            You are analyzing whether a task can be completed with a single tool call or requires decomposition.
            
            TOOL INFORMATION:
            - Tool Name: {tool_name}
            - Tool Description: {schema_desc}
            - Required Parameters: {list(schema_props.keys())}
    
            ✅ OUTPUT FORMAT:
            {{
                "requires_decomposition": boolean,
                "reasoning": "Specific analysis",
                "atomic_tool_name": "{tool_name}" or null,
                "estimated_subtasks": number_if_complex
            }}
            '''
        # --- END OF NEW LOGIC ---

        human_prompt = f"""
            ANALYZE THIS TASK: 
            
            Task: "{task_description}"
            Assigned Tool: "{tool_name}"
            
            Can this tool directly accomplish this task in a single call, or does it need decomposition?
            🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
            """
        return system_prompt, human_prompt


    

    


    def generate_enhanced_parameter_repair_prompt(self, task: Any, state: Any) -> tuple[str, str]:
        """Generate enhanced prompt for parameter repair with full context."""
        
        # Extract all relevant context from the task
        task_description = task.description
        tool_name = task.tool_name
        tool_schema = {}  # This will be populated by the calling function
        original_goal = state.original_goal
        
        # Get failure context
        error_message = ""
        error_type = ""
        fail_count = 0
        failed_parameters = {}
        
        if hasattr(task, 'failure_context') and task.failure_context:
            error_message = task.failure_context.error_message
            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            failed_parameters = task.failure_context.failed_parameters or {}
        
        # Get validator feedback if available
        validator_feedback = ""
        if error_type == "GoalValidationFailure":
            validator_feedback = error_message
        
        # Get completed task history for context
        completed_tasks = [t for t in state.tasks if t.status == "completed" and hasattr(t, 'execution_context') and t.execution_context]
        recent_completed_tasks_info = "\n".join([
            f"• Task {t.task_id}: {t.description} ({t.tool_name}) -> {t.execution_context.analysis or 'No analysis'}"
            for t in completed_tasks[-3:]  # Last 3 completed tasks
        ]) or "No recent completed tasks"
        
        # Get failed tasks with validator feedback
        failed_tasks_with_feedback = [t for t in state.tasks 
                                     if t.status == "failed" 
                                     and hasattr(t, 'failure_context') and t.failure_context 
                                     and t.failure_context.error_type == "GoalValidationFailure"]
        
        failed_tasks_info = "\n".join([
            f"• Task {t.task_id}: {t.description} -> Validator Feedback: {t.failure_context.error_message}"
            for t in failed_tasks_with_feedback[-2:]  # Last 2 failed tasks with feedback
        ]) or "No recent failed tasks with validator feedback"
        
        system_prompt = '''
        You are an expert parameter repair AI. Your job is to analyze a failed task and generate corrected parameters that will make the tool execute successfully.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {
            "repaired_parameters": {
                "param1": "corrected_value1",
                "param2": "corrected_value2"
            },
            "reasoning": "Brief explanation of what was wrong and how it was fixed"
        }

        📋 CONTEXT ANALYSIS:
        - Original Goal: The overarching objective the user wants to achieve
        - Task Description: What this specific task is trying to accomplish
        - Tool Schema: The exact parameters this tool accepts and requires
        - Error Details: What went wrong in previous attempts
        - Validator Feedback: If the tool ran but didn't achieve the goal, what was wrong with the output
        - Recent Context: What has already been accomplished in previous tasks
        - Failure Patterns: What mistakes have been made recently that should be avoided

        🎯 REPAIR STRATEGY:
        1. If it's a ToolExecutionError: Fix parameters to make the tool work correctly
        2. If it's a GoalValidationFailure: Adjust parameters to better meet the task's actual requirements
        3. Consider all context to avoid repeating the same mistakes
        4. Ensure all required parameters are provided and valid
        5. Make minimal changes - only fix what's broken
        '''
        
        human_prompt = f"""
        --- PARAMETER REPAIR ANALYSIS ---

        🎯 ORIGINAL USER GOAL:
        "{original_goal}"

        📋 FAILED TASK DETAILS:
        Task Description: "{task_description}"
        Tool Name: "{tool_name}"
        Error Type: "{error_type}"
        Fail Count: {fail_count}
        Error Message: "{error_message}"
        Validator Feedback: "{validator_feedback}"

        🔧 TOOL SCHEMA:
        {tool_schema}

        ❌ FAILED PARAMETERS:
        {failed_parameters}

        📚 RECENT COMPLETED TASKS CONTEXT:
        {recent_completed_tasks_info}

        ⚠️ RECENT FAILURE PATTERNS TO AVOID:
        {failed_tasks_info}

        --- REPAIR INSTRUCTIONS ---
        Based on all this context, generate corrected parameters that will make this tool execute successfully AND achieve the task's goal.
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_enhanced_alternative_tool_prompt(self, task: Any, state: Any) -> tuple[str, str]:
        """Generate enhanced prompt for alternative tool selection with full context."""
        
        # Extract all relevant context from the task
        task_description = task.description
        current_tool = task.tool_name
        original_goal = state.original_goal
        
        # Get failure context
        error_message = ""
        error_type = ""
        fail_count = 0
        failed_parameters = {}
        
        if hasattr(task, 'failure_context') and task.failure_context:
            error_message = task.failure_context.error_message
            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            failed_parameters = task.failure_context.failed_parameters or {}
        
        # Get validator feedback if available
        validator_feedback = ""
        if error_type == "GoalValidationFailure":
            validator_feedback = error_message
        
        # Get all available tools (this will be populated by the calling function)
        available_tools_info = ""
        
        # Get completed task history for context
        completed_tasks = [t for t in state.tasks if t.status == "completed" and hasattr(t, 'execution_context') and t.execution_context]
        recent_completed_tasks_info = "\n".join([
            f"• Task {t.task_id}: {t.description} ({t.tool_name}) -> {t.execution_context.analysis or 'No analysis'}"
            for t in completed_tasks[-3:]  # Last 3 completed tasks
        ]) or "No recent completed tasks"
        
        # Get failed tasks with validator feedback
        failed_tasks_with_feedback = [t for t in state.tasks 
                                     if t.status == "failed" 
                                     and hasattr(t, 'failure_context') and t.failure_context 
                                     and t.failure_context.error_type == "GoalValidationFailure"]
        
        failed_tasks_info = "\n".join([
            f"• Task {t.task_id}: {t.description} -> Validator Feedback: {t.failure_context.error_message}"
            for t in failed_tasks_with_feedback[-2:]  # Last 2 failed tasks with feedback
        ]) or "No recent failed tasks with validator feedback"
        
        system_prompt = '''
        You are an expert tool selection AI. Your job is to analyze a failed task and suggest a better alternative tool that can accomplish the same goal.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {
            "alternative_tool": "exact_tool_name_from_available_list",
            "reasoning": "Brief explanation of why this tool is better for this task",
            "expected_parameters": {
                "param1": "example_value1",
                "param2": "example_value2"
            }
        }

        📋 CONTEXT ANALYSIS:
        - Original Goal: The overarching objective the user wants to achieve
        - Task Description: What this specific task is trying to accomplish
        - Current Tool Issues: Why the current tool is failing
        - Available Tools: All possible tools that could be used
        - Error Details: What went wrong with the current approach
        - Validator Feedback: If the tool ran but didn't achieve the goal, what was wrong with the output
        - Recent Context: What has already been accomplished in previous tasks
        - Failure Patterns: What mistakes have been made recently that should be avoided

        🎯 SELECTION STRATEGY:
        1. If it's a ToolExecutionError: Find a tool that won't have the same execution issues
        2. If it's a GoalValidationFailure: Find a tool that's better suited to achieve the actual goal
        3. Consider all context to avoid repeating the same mistakes
        4. Choose the simplest tool that can accomplish the task
        5. Ensure the suggested tool actually exists in the available tools list
        '''
        
        human_prompt = f"""
        --- ALTERNATIVE TOOL ANALYSIS ---

        🎯 ORIGINAL USER GOAL:
        "{original_goal}"

        📋 FAILED TASK DETAILS:
        Task Description: "{task_description}"
        Current Tool: "{current_tool}"
        Error Type: "{error_type}"
        Fail Count: {fail_count}
        Error Message: "{error_message}"
        Validator Feedback: "{validator_feedback}"

        ❌ FAILED PARAMETERS WITH CURRENT TOOL:
        {failed_parameters}

        🛠️ AVAILABLE TOOLS:
        {available_tools_info}

        📚 RECENT COMPLETED TASKS CONTEXT:
        {recent_completed_tasks_info}

        ⚠️ RECENT FAILURE PATTERNS TO AVOID:
        {failed_tasks_info}

        --- TOOL SELECTION INSTRUCTIONS ---
        Based on all this context, suggest a better alternative tool that can accomplish this task successfully.
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt


    def generate_parameter_repair_prompt(self, task_description: str, tool_name: str, tool_schema: dict,
                                         failed_parameters: dict, error_message: str) -> tuple[str, str]:
        """Generates a prompt to ask the LLM to repair failed parameters."""
        system_prompt = f'''
            You are a parameter correction expert. A tool failed due to bad parameters.
            Your job is to analyze the tool's schema, the failed parameters, and the error message, then provide a corrected set of parameters.

            TOOL SCHEMA for `{tool_name}`:
            {tool_schema}

            ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
            {{
                "repaired_parameters": {{ "param1": "new_value", ... }}
            }}
            '''
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


    def generate_alternative_tool_prompt(self, task_description: str, failed_tool: str, error_message: str,
                                         available_tools_str: str) -> tuple[str, str]:
        """Generates a prompt to ask the LLM for a safer, alternative tool."""
        system_prompt = f'''
            You are a strategic recovery expert. A task failed. Your job is to suggest a single, safer, alternative tool that might accomplish the task's goal without causing the same error.

            AVAILABLE TOOLS:
            {available_tools_str}

            ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
            {{
                "alternative_tool": "tool_name_from_list_or_null",
                "reasoning": "A brief explanation for your choice."
            }}
            '''
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


    def generate_goal_achievement_prompt(self, original_goal: str, plan_created: str, task_description: str,
                                         tool_result: str, analysis: str) -> tuple[str, str]:
        """Generates prompts for the goal achievement validation node."""
        system_prompt = '''
                    🚨 CRITICAL: YOU ARE ONLY VALIDATING IMMEDIATE TOOL EXECUTION SUCCESS - NOT THE ENTIRE WORKFLOW!

                    You are a TOOL EXECUTION validator. Your ONLY job is to determine if the specific tool executed successfully and produced the output it was supposed to produce for its immediate task.

                    ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
                    {{
                        "goal_achieved": boolean,
                        "reasoning": "A brief, clear explanation for your decision."
                    }}

                    --- SIMPLIFIED DECISION RULES ---
                    1.  **ONLY Check: Did the tool execute successfully?** Look at the `TOOL RESULT` and `RESULT ANALYSIS`. Did the tool run without errors and produce relevant output for the specific `TASK GOAL`?
                    2.  **IGNORE the bigger picture.** Do NOT consider if the output fits the overall user goal, style preferences, or workflow completeness. That's not your job.
                    3.  **LIBERAL SUCCESS CRITERIA:** If the tool ran and produced ANY reasonable output related to the task (even if minimal), mark it as successful.
                    4.  **ONLY FAIL if:** The tool errored out, returned nothing, or the output is completely unrelated to the immediate task.

                    --- CONTEXT IS FOR REFERENCE ONLY ---
                    The `OVERALL USER GOAL` and `ORIGINAL PLAN` are provided for context only. Do NOT use them to judge success.
                    Your job is NOT to validate the entire workflow - just this one tool execution.

                    --- EXAMPLES OF CORRECT VALIDATION ---
                    ✅ Task: "List files in directory" → Tool returned file list → SUCCESS (even if list is empty)
                    ✅ Task: "Read file content" → Tool returned file content → SUCCESS (even if content is simple)
                    ✅ Task: "Write report to file" → Tool wrote file successfully → SUCCESS (don't judge report quality)
                    ❌ Task: "Search for data" → Tool returned error or crash → FAILURE
                    ❌ Task: "Create summary" → Tool returned completely unrelated content → FAILURE

                    --- CRITICAL RULE ---
                    DO NOT FAIL a tool execution just because you think the output should be "better" or "more complete".
                    If the tool did what it was asked to do without errors, mark it as successful.
                    '''

        human_prompt = f"""
                    --- TOOL EXECUTION VALIDATION (IGNORE BROADER CONTEXT) ---

                    CONTEXT FOR REFERENCE ONLY (DO NOT USE FOR VALIDATION):
                    Overall User Goal: `{original_goal}`
                    Original Plan: `{plan_created}`

                    ---
                    VALIDATE ONLY THIS SPECIFIC TOOL EXECUTION:

                    IMMEDIATE TASK:
                    `{task_description}`

                    TOOL EXECUTION RESULT:
                    `{tool_result}`

                    RESULT ANALYSIS:
                    `{analysis}`

                    --- QUESTION ---
                    Did this specific tool execution complete successfully and produce reasonable output for its immediate task?
                    IGNORE whether it fits the bigger picture - just validate the tool execution itself.

                    🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
                    """

        return system_prompt, human_prompt

    def generate_synthesis_execution_prompt(self, instructions: str, context: str) -> tuple[str, str]:
        """Generates the prompt for executing the internal synthesis LLM call.
        """
        system_prompt = '''
        You are a data synthesis expert. Your job is to follow the user's instructions to process a given context, which is composed of the results from previous tasks.
        You must follow the instructions precisely to aggregate, summarize, or transform the context into the desired output.
        The output should be a single, coherent block of text.
        '''

        human_prompt = f"""
        --- INSTRUCTIONS ---
        {instructions}

        --- CONTEXT TO PROCESS ---
        {context}
        ---

        Based on the instructions, process the context and provide the synthesized result.
        """
        return system_prompt, human_prompt


    def generate_recovery_strategy_prompt(self, task_description: str, tool_name: str,
                                         error_message: str, error_type: str, fail_count: int,
                                         failed_parameters: dict, tool_schema: dict,
                                         original_goal: str, completed_tasks_context: str,
                                         failed_tasks_context: str, available_tools: str,
                                         strategy_hist : str) -> tuple[str, str]:
        """Generate prompt for LLM-driven recovery strategy decision."""
        system_prompt = f'''
        You are an expert error recovery strategist. Your job is to analyze a failed task and determine the best recovery strategy based on comprehensive context.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {{
            "recovery_strategy": "PARAMETER_REPAIR" | "ALTERNATIVE_TOOL" | "TASK_DECOMPOSITION" | "LLM_RECOVERY",
            "reasoning": "Brief explanation of why this strategy was chosen",
            "confidence_level": "HIGH" | "MEDIUM" | "LOW",
            "estimated_success_probability": number_between_0_and_100,
            "next_steps": "Specific next steps for implementing this strategy"
        }}

        --- PREVIOUS RECOVERY ATTEMPTS ---
        {strategy_hist}
        ---

        📋 STRATEGY OPTIONS:
        1. PARAMETER_REPAIR: Fix the parameters of the current tool to make it work correctly
        2. ALTERNATIVE_TOOL: Switch to a different tool that can accomplish the same goal
        3. TASK_DECOMPOSITION: Break the task into smaller sub-tasks for better handling
        4. LLM_RECOVERY: Use advanced LLM reasoning to find a novel solution

        🎯 DECISION FACTORS:
        - CRITICAL RULE: Do NOT repeat a strategy that has already failed. Analyze the history above and choose a different strategy.
        - Error Type: What kind of error occurred (ToolExecutionError, GoalValidationFailure, etc.)
        - Fail Count: How many times the task has failed
        - Task Complexity: Whether the task is simple or complex
        - Available Tools: What other tools could accomplish the same goal
        - Completed Context: What has already been accomplished successfully
        - Failure Patterns: What mistakes have been made recently
        - Validator Feedback: If available, what the goal validator suggested
        - NEVER repeat the same failed strategy

        📊 CONFIDENCE LEVELS:
        - HIGH: Strong evidence supports this strategy (e.g., clear pattern of parameter errors)
        - MEDIUM: Some evidence supports this strategy but alternatives are possible
        - LOW: Uncertain which strategy is best, requires experimentation

        🎯 STRATEGY SELECTION GUIDELINES:
        1. PARAMETER_REPAIR: When the tool is correct but parameters are wrong, especially for file paths, queries, etc.
        2. ALTERNATIVE_TOOL: When the current tool is fundamentally unsuitable or keeps failing despite parameter repair
        3. TASK_DECOMPOSITION: When the task is inherently complex or has failed multiple times (>1) with different approaches
        4. LLM_RECOVERY: When conventional approaches have failed or when creative problem-solving is needed

        📋 ADDITIONAL CONTEXT ANALYSIS:
        - Original Goal: The overarching objective the user wants to achieve
        - Task Description: What this specific task is trying to accomplish
        - Tool Schema: The exact parameters this tool accepts and requires
        - Error Details: What went wrong in previous attempts
        - Recent Context: What has already been accomplished in previous tasks
        - Failure Patterns: What mistakes have been made recently that should be avoided
        '''

        human_prompt = f"""
        --- RECOVERY STRATEGY ANALYSIS ---

        🎯 ORIGINAL USER GOAL:
        "{original_goal}"

        📋 FAILED TASK DETAILS:
        Task Description: "{task_description}"
        Current Tool: "{tool_name}"
        Error Type: "{error_type}"
        Fail Count: {fail_count}
        Error Message: "{error_message}"

        🔧 TOOL SCHEMA:
        {tool_schema}

        ❌ FAILED PARAMETERS:
        {failed_parameters}

        📚 RECENT COMPLETED TASKS CONTEXT:
        {completed_tasks_context}

        ⚠️ RECENT FAILURE PATTERNS TO AVOID:
        {failed_tasks_context}

        🛠️ AVAILABLE TOOLS:
        {available_tools}

        --- STRATEGY SELECTION INSTRUCTIONS ---
        Based on all this comprehensive context, determine the best recovery strategy for this failed task.

        Consider:
        1. The specific error type and message
        2. How many times this task has failed
        3. Whether parameter repair has already been attempted
        4. What alternative tools might work better
        5. Whether this task might benefit from decomposition
        6. Any patterns in recent failures

        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """

        return system_prompt, human_prompt

    def generate_enhanced_parameter_repair_prompt(self, task: Any, state: Any, tool_schema) -> tuple[str, str]:
        """Generate enhanced prompt for parameter repair with full context."""
        
        # Extract all relevant context from the task
        task_description = task.description
        tool_name = task.tool_name
        original_goal = getattr(state, 'original_goal', '')

        # Get failure context
        error_message = ""
        error_type = ""
        fail_count = 0
        failed_parameters = {}
        
        if hasattr(task, 'failure_context') and task.failure_context:
            error_message = getattr(task.failure_context, 'error_message', '')
            error_type = getattr(task.failure_context, 'error_type', '') or ""
            fail_count = getattr(task.failure_context, 'fail_count', 0)
            failed_parameters = getattr(task.failure_context, 'failed_parameters', {}) or {}

        # Get validator feedback if available
        validator_feedback = ""
        if error_type == "GoalValidationFailure":
            validator_feedback = error_message
        
        # Get completed task history for context
        completed_tasks = [t for t in getattr(state, 'tasks', []) if getattr(t, 'status', '') == "completed" and hasattr(t, 'execution_context') and t.execution_context]
        recent_completed_tasks_info = "\n".join([
            f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} ({getattr(t, 'tool_name', 'N/A')}) -> {getattr(t.execution_context, 'analysis', 'No analysis') or 'No analysis'}"
            for t in completed_tasks[-3:]  # Last 3 completed tasks
        ]) or "No recent completed tasks"
        
        # Get failed tasks with validator feedback
        failed_tasks_with_feedback = [t for t in getattr(state, 'tasks', [])
                                     if getattr(t, 'status', '') == "failed"
                                     and hasattr(t, 'failure_context') and t.failure_context
                                     and getattr(t.failure_context, 'error_type', '') == "GoalValidationFailure"]

        failed_tasks_info = "\n".join([
            f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} -> Validator Feedback: {getattr(t.failure_context, 'error_message', 'N/A')}"
            for t in failed_tasks_with_feedback[-2:]  # Last 2 failed tasks with feedback
        ]) or "No recent failed tasks with validator feedback"
        
        system_prompt = '''
        You are an expert parameter repair AI. Your job is to analyze a failed task and generate corrected parameters that will make the tool execute successfully.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {
            "repaired_parameters": {
                "param1": "corrected_value1",
                "param2": "corrected_value2"
            },
            "reasoning": "Brief explanation of what was wrong and how it was fixed"
        }

        📋 CONTEXT ANALYSIS:
        - Original Goal: The overarching objective the user wants to achieve
        - Task Description: What this specific task is trying to accomplish
        - Tool Schema: The exact parameters this tool accepts and requires
        - Error Details: What went wrong in previous attempts
        - Validator Feedback: If the tool ran but didn't achieve the goal, what was wrong with the output
        - Recent Context: What has already been accomplished in previous tasks
        - Failure Patterns: What mistakes have been made recently that should be avoided

        🎯 REPAIR STRATEGY:
        1. If it's a ToolExecutionError: Fix parameters to make the tool work correctly
        2. If it's a GoalValidationFailure: Adjust parameters to better meet the task's actual requirements
        3. Consider all context to avoid repeating the same mistakes
        4. Ensure all required parameters are provided and valid
        5. Make minimal changes - only fix what's broken
        '''
        
        human_prompt = f"""
        --- PARAMETER REPAIR ANALYSIS ---

        🎯 ORIGINAL USER GOAL:
        "{original_goal}"

        📋 FAILED TASK DETAILS:
        Task Description: "{task_description}"
        Tool Name: "{tool_name}"
        Error Type: "{error_type}"
        Fail Count: {fail_count}
        Error Message: "{error_message}"
        Validator Feedback: "{validator_feedback}"

        🔧 TOOL SCHEMA:
        {tool_schema}

        ❌ FAILED PARAMETERS:
        {failed_parameters}

        📚 RECENT COMPLETED TASKS CONTEXT:
        {recent_completed_tasks_info}

        ⚠️ RECENT FAILURE PATTERNS TO AVOID:
        {failed_tasks_info}

        --- REPAIR INSTRUCTIONS ---
        Based on all this context, generate corrected parameters that will make this tool execute successfully AND achieve the task's goal.
        
        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        return system_prompt, human_prompt

    def generate_enhanced_alternative_tool_prompt(self, task: Any, state: Any, all_tools) -> tuple[str, str]:
        """Generate enhanced prompt for alternative tool selection with full context."""

        # Extract all relevant context from the task
        task_description = task.description
        current_tool = task.tool_name
        original_goal = getattr(state, 'original_goal', '')

        # Get failure context
        error_message = ""
        error_type = ""
        fail_count = 0
        failed_parameters = {}

        if hasattr(task, 'failure_context') and task.failure_context:
            error_message = getattr(task.failure_context, 'error_message', '')
            error_type = getattr(task.failure_context, 'error_type', '') or ""
            fail_count = getattr(task.failure_context, 'fail_count', 0)
            failed_parameters = getattr(task.failure_context, 'failed_parameters', {}) or {}

        # Get validator feedback if available
        validator_feedback = ""
        if error_type == "GoalValidationFailure":
            validator_feedback = error_message

        # Get all available tools
        # all_tools = AgentCoreHelpers.get_safe_tools_list() if hasattr(AgentCoreHelpers, 'get_safe_tools_list') else []
        available_tools_info = "\n".join([
            f"• {getattr(tool, 'name', 'N/A')}: {getattr(tool, 'description', 'N/A')}"
            for tool in all_tools
        ])

        # Get completed task history for context
        completed_tasks = [t for t in getattr(state, 'tasks', []) if getattr(t, 'status', '') == "completed" and hasattr(t, 'execution_context') and t.execution_context]
        recent_completed_tasks_info = "\n".join([
            f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} ({getattr(t, 'tool_name', 'N/A')}) -> {getattr(t.execution_context, 'analysis', 'No analysis') or 'No analysis'}"
            for t in completed_tasks[-3:]  # Last 3 completed tasks
        ]) or "No recent completed tasks"

        # Get failed tasks with validator feedback
        failed_tasks_with_feedback = [t for t in getattr(state, 'tasks', [])
                                     if getattr(t, 'status', '') == "failed"
                                     and hasattr(t, 'failure_context') and t.failure_context
                                     and getattr(t.failure_context, 'error_type', '') == "GoalValidationFailure"]

        failed_tasks_info = "\n".join([
            f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} -> Validator Feedback: {getattr(t.failure_context, 'error_message', 'N/A')}"
            for t in failed_tasks_with_feedback[-2:]  # Last 2 failed tasks with feedback
        ]) or "No recent failed tasks with validator feedback"

        system_prompt = '''
        You are an expert tool selection AI. Your job is to analyze a failed task and suggest a better alternative tool that can accomplish the same goal.

        ✅ REQUIRED OUTPUT FORMAT (EXACT JSON OBJECT):
        {
            "alternative_tool": "exact_tool_name_from_available_list",
            "reasoning": "Brief explanation of why this tool is better for this task",
            "expected_parameters": {
                "param1": "example_value1",
                "param2": "example_value2"
            }
        }

        📋 CONTEXT ANALYSIS:
        - Original Goal: The overarching objective the user wants to achieve
        - Task Description: What this specific task is trying to accomplish
        - Current Tool Issues: Why the current tool is failing
        - Available Tools: All possible tools that could be used
        - Error Details: What went wrong with the current approach
        - Validator Feedback: If the tool ran but didn't achieve the goal, what was wrong with the output
        - Recent Context: What has already been accomplished in previous tasks
        - Failure Patterns: What mistakes have been made recently that should be avoided

        🎯 SELECTION STRATEGY:
        1. If it's a ToolExecutionError: Find a tool that won't have the same execution issues
        2. If it's a GoalValidationFailure: Find a tool that's better suited to achieve the actual goal
        3. Consider all context to avoid repeating the same mistakes
        4. Choose the simplest tool that can accomplish the task
        5. Ensure the suggested tool actually exists in the available tools list
        '''

        human_prompt = f"""
        --- ALTERNATIVE TOOL ANALYSIS ---

        🎯 ORIGINAL USER GOAL:
        "{original_goal}"

        📋 FAILED TASK DETAILS:
        Task Description: "{task_description}"
        Current Tool: "{current_tool}"
        Error Type: "{error_type}"
        Fail Count: {fail_count}
        Error Message: "{error_message}"
        Validator Feedback: "{validator_feedback}"

        ❌ FAILED PARAMETERS WITH CURRENT TOOL:
        {failed_parameters}

        🛠️ AVAILABLE TOOLS:
        {available_tools_info}

        📚 RECENT COMPLETED TASKS CONTEXT:
        {recent_completed_tasks_info}

        ⚠️ RECENT FAILURE PATTERNS TO AVOID:
        {failed_tasks_info}

        --- TOOL SELECTION INSTRUCTIONS ---
        Based on all this context, suggest a better alternative tool that can accomplish this task successfully.

        🚨 RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """

        return system_prompt, human_prompt
