import json
import re
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from ...tools.lggraph_tools.tool_assign import ToolAssign
from ...utils.argument_schema_util import get_tool_argument_schema
from ...utils.model_manager import ModelManager
from .hierarchical_agent_prompts import (
    HierarchicalAgentPrompt,
)
from ...tools.lggraph_tools.tool_response_manager import ToolResponseManager
from .pydantic_models import (
    TASK,
    REQUIRED_CONTEXT,
    WorkflowStateModel,
)


class AgentCoreHelpers:
    """
    HELPER FUNCTION FOR AGENT AND SUB-AGENT CLASSES
    Common utility functions for agent and sub-agent classes.
    todo : the all function those are not nodes should be moved here
    """

    synthesis_tool_description = "• perform_synthesis: A virtual tool to review the results of previous tasks and synthesize them into a single, comprehensive summary or answer. Use this when you need to combine information from multiple sources before taking a final action, like writing a file. Parameters: {'instructions': 'A clear, natural language instruction on what to synthesize and how to format it.'}"

    @classmethod
    def get_tool_schema(cls, tool_name: str) -> dict:
        """Get schema for a specific tool."""
        try:
            tools = AgentCoreHelpers.get_safe_tools_list()
            target_tool = next(
                (tool for tool in tools if tool.name.lower() == tool_name.lower()), None
            )

            if target_tool:
                schema_str = get_tool_argument_schema(target_tool)
                return json.loads(schema_str)
            return {}
        except Exception as e:
            # print_log_message(f"Failed to get schema for {tool_name}: {e}", "Tool Schema")
            ContextRegistry.get().get_logger().debug_error(
                "Tool Schema",
                f"Failed to get schema for {tool_name}: {e}",
                metadata={"function name": "__get_tool_schema", "tool_name": tool_name},
            )
            return {}

    @classmethod
    def perform_internal_synthesis(
        cls, current_task: TASK, full_history: list[TASK]
    ) -> tuple[bool, str]:
        """
        Executes the virtual 'perform_synthesis' tool by calling an LLM.
        """
        ContextRegistry.get().get_logger().debug_error(
            "Internal Synthesis",
            f"Performing synthesis for task: {current_task.description}",
            metadata={
                "function_name": "_perform_internal_synthesis",
                "task_id": current_task.task_id,
            },
        )

        # Extract the raw results from the history
        context_from_history = "\n\n".join(
            [
                f"Result from Task {t.task_id} ({t.tool_name}):\n{t.execution_context.result}"
                for t in full_history
                if t.execution_context and t.execution_context.result
            ]
        )

        if not context_from_history:
            return False, "Synthesis failed: No previous results found to synthesize."

        # Get the specific instructions from the current task's parameters
        synthesis_instructions = current_task.execution_context.parameters.get(
            "instructions", "Summarize the provided context."
        )

        # This prompt needs to be added to hierarchical_agent_prompts.py
        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = (
            prompt_generator.generate_synthesis_execution_prompt(
                synthesis_instructions, context_from_history
            )
        )

        try:
            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )
            synthesis_result = response.content
            return True, synthesis_result
        except Exception as e:
            error_msg = f"Internal synthesis LLM call failed: {e}"
            ContextRegistry.get().get_logger().debug_error(
                "Internal Synthesis", error_msg, metadata={"exception": str(e)}
            )
            return False, error_msg

    # ----------- these are tool list helpers -----------
    @classmethod
    def get_safe_tools_list(cls):
        """Get a safe list of tools, raising an error if no tools are available."""
        # todo virtual tools could add up here
        tools = ToolAssign.get_tools_list()
        if not tools:
            raise RuntimeError("No tools available - system cannot function")
        return tools

    @classmethod
    def get_detailed_tool_context(cls, recommended_tools: list[str]) -> str:
        """Get detailed context (name, description, schema) for only the recommended tools.
        Uses the same approach as main_orchestrator.py
        """
        try:
            all_tools = AgentCoreHelpers.get_safe_tools_list()
            tool_context = []

            # --- INJECT VIRTUAL TOOL ---
            if "perform_synthesis" in recommended_tools:
                tool_context.append(cls.synthesis_tool_description)
            # --- END INJECTION ---

            for tool in all_tools:
                if tool.name in recommended_tools:
                    # Get name and description
                    name = getattr(tool, "name", "N/A")
                    desc = getattr(tool, "description", "No description available")

                    # Get arguments using the same function as main_orchestrator.py
                    args_schema = get_tool_argument_schema(tool)

                    tool_context.append(
                        f"• {name}: {desc}\n  Parameters: {args_schema}"
                    )

            return "\n\n".join(tool_context)

        except Exception as e:
            # print_log_message(f"Failed to get detailed tool context: {e}", "Tool Context")
            ContextRegistry.get().get_logger().debug_warning(
                "Tool Context",
                f"Failed to get detailed tool context: {e}",
                metadata={
                    "function_name": "get_detailed_tool_context",
                    "exception": str(e),
                },
            )
            return "Tool context unavailable"

    @classmethod
    def recommend_tools_for_task(
        cls,
        task_description: str,
        max_tools: int = 10,
        parent_context: str | None = None,
    ) -> list[str]:
        """Use LLM to recommend 5-10 most relevant tools for a specific task.
        This is the pre-filtering step that makes the system much more efficient.
        """
        try:
            # Get all available tool names
            all_tools = AgentCoreHelpers.get_safe_tools_list()
            all_tool_names = [tool.name for tool in all_tools]

            # Create a concise tool list for the recommender, including the virtual tool
            tool_list_for_prompt = [f"• {tool.name}" for tool in all_tools]
            tool_list_for_prompt.append(
                "perform_synthesis"
            )  # Make the virtual tool visible
            tool_list = "\n".join(tool_list_for_prompt)

            recommend_prompt = f"""
                TOOL RECOMMENDATION SYSTEM

                Task: "{task_description}"

                Available Tools:
                {tool_list}
                
                parent_context:
                {parent_context if parent_context else "No additional context provided"}

                Select up to {max_tools} tools from the list above that are most relevant for this task.
                Consider broad categories such as: file operations (e.g., list/read/write), web research, analysis, shell/OS commands, and memory/graph operations and others.
                Do not invent tool names — return only names that appear in the Available Tools section and match them exactly.

                Respond with ONLY a JSON array of tool names, for example:
                ["tool1", "tool2", "tool3"]
                """

            model = ModelManager()
            response = model.invoke(
                [
                    {
                        "role": "system",
                        "content": "You are a tool recommendation expert. Select the most relevant tools for the given task.",
                    },
                    {"role": "user", "content": recommend_prompt},
                ]
            )

            recommended_tools = ModelManager.convert_to_json(response.content)

            # Validate and filter
            if isinstance(recommended_tools, list):
                # Also consider the virtual tool as valid
                valid_tools = [
                    tool
                    for tool in recommended_tools
                    if tool in all_tool_names or tool == "perform_synthesis"
                ]
                return valid_tools[:max_tools]
            # Fallback to common tools
            return ["list_directory", "google_search", "write_file"]

        except Exception as e:
            # Use module-level ContextRegistry.get().get_logger().debug_warning (fallback defined earlier) instead of re-importing
            ContextRegistry.get().get_logger().debug_warning(
                "Tool Recommender",
                f"Tool recommendation failed: {e}",
                metadata={
                    "function name": "recommend_tools_for_task",
                    "task_description": task_description,
                    "max_tools": max_tools,
                },
            )
            # Safe fallback
            return [
                "list_directory",
                "google_search",
                "write_file",
                "perform_synthesis",
            ]

    # ^^^^^^^^^^^^^^ these are tool list helpers ^^^^^^^^^^^^^^^^^^
    @staticmethod
    def evaluate_skip_cascade(
        current_task: TASK, skipped_tasks: list[TASK]
    ) -> tuple[bool, str]:
        """
        Evaluate if the current task should be skipped based on previous skips.

        Uses RULE-BASED dependency detection (NO AI calls needed):
        1. PARENT-CHILD: Sub-tasks depend on parent tasks (via float IDs)
        2. SEQUENTIAL: Task N depends on Task N-1 if it references N-1's output
        3. RESOURCE: Task B depends on Task A if it needs A's file/data

        Returns:
            tuple[bool, str]: (should_skip, reason)
        """
        # Early exit: no skipped tasks means no cascade possible
        if len(skipped_tasks) == 0:
            return False, "No skipped tasks to evaluate for cascade skip."

        # Extract current task info for analysis
        current_id = current_task.task_id
        current_desc = (
            current_task.description.lower() if current_task.description else ""
        )
        current_params = (
            current_task.execution_context.parameters
            if current_task.execution_context
            else {}
        )

        # DEPENDENCY TYPE 1: PARENT-CHILD RELATIONSHIP (via float IDs)
        # Example: Task 1.1, 1.2 are children of Task 1
        # If parent (1) is skipped, children (1.1, 1.2) should also skip
        if isinstance(current_id, str) and "." in current_id:
            # Extract parent ID from current task (e.g., "1" from "1.1" or "1.1" from "1.1.2")
            parent_id = current_id.rsplit(".", 1)[
                0
            ]  # Get parent by removing last segment

            # Check if parent task is in skipped list
            for skipped in skipped_tasks:
                skipped_id_str = str(skipped.task_id)
                if skipped_id_str == parent_id:
                    return (
                        True,
                        f"Parent task {parent_id} was skipped. This sub-task cannot proceed without parent.",
                    )

        # DEPENDENCY TYPE 2: SEQUENTIAL DEPENDENCY
        # If current task's description mentions a previous skipped task's tool or references "previous task"
        # Example: Task 2 says "Use search results from previous task" → depends on Task 1
        for skipped in skipped_tasks:
            skipped_tool = skipped.tool_name.lower() if skipped.tool_name else ""

            # Check if current task description explicitly mentions the skipped task's tool
            # e.g., "write the search results" when google_search was skipped
            if skipped_tool and skipped_tool in current_desc:
                return (
                    True,
                    f"Task references '{skipped_tool}' which was skipped (Task {skipped.task_id}).",
                )

            # Check for explicit sequential references like "previous task", "from earlier", etc.
            sequential_keywords = [
                "previous task",
                "earlier task",
                "from task",
                "using the",
            ]
            if any(keyword in current_desc for keyword in sequential_keywords):
                # Conservative: only skip if the skipped task was IMMEDIATELY before current task
                try:
                    current_id_num = (
                        float(str(current_id).split("-")[0])
                        if isinstance(current_id, str)
                        else float(current_id)
                    )
                    skipped_id_num = (
                        float(str(skipped.task_id).split("-")[0])
                        if isinstance(skipped.task_id, str)
                        else float(skipped.task_id)
                    )

                    # If skipped task is right before current (e.g., Task 1 skipped, Task 2 current)
                    if abs(current_id_num - skipped_id_num) <= 1.0:
                        return (
                            True,
                            f"Task has sequential dependency on skipped Task {skipped.task_id} (detected via context keywords).",
                        )
                except (ValueError, TypeError):
                    pass  # Skip numeric comparison if IDs aren't numeric

        # DEPENDENCY TYPE 3: RESOURCE DEPENDENCY
        # If current task's parameters reference a file/resource that should have been created by skipped task
        # Example: Task A creates "report.txt", Task B needs "report.txt" → B depends on A
        if isinstance(current_params, dict):
            # Check if current task parameters contain file paths
            param_values = [str(v).lower() for v in current_params.values() if v]

            for skipped in skipped_tasks:
                # Check if skipped task was supposed to create/modify a file
                skipped_params = (
                    skipped.execution_context.parameters
                    if skipped.execution_context
                    else {}
                )
                if isinstance(skipped_params, dict):
                    skipped_values = [
                        str(v).lower() for v in skipped_params.values() if v
                    ]

                    # Look for common file references between current and skipped task parameters
                    for current_val in param_values:
                        for skipped_val in skipped_values:
                            # If both tasks reference the same file path
                            if (
                                len(current_val) > 5 and len(skipped_val) > 5
                            ):  # Ignore short strings
                                if (
                                    current_val in skipped_val
                                    or skipped_val in current_val
                                ):
                                    # Check if skipped task was a write operation (likely creates the file)
                                    if skipped.tool_name in [
                                        "mcp_filesystem_write_file",
                                        "write_file",
                                        "create_file",
                                    ]:
                                        return (
                                            True,
                                            f"Task requires file resource from skipped Task {skipped.task_id} (file: {skipped_val[:50]}).",
                                        )

        # DEFAULT: No clear dependency detected - DO NOT skip (conservative approach)
        # Better to attempt execution and fail explicitly than skip incorrectly
        return False, "No clear dependency on skipped tasks detected."

    class ErrorFallbackHelpers:
        """Enhanced helper functions for error fallback node with LLM-driven decision making."""

        @staticmethod
        def attempt_parameter_repair(
            task: TASK, state: WorkflowStateModel
        ) -> tuple[bool, dict]:
            """Use LLM to intelligently repair the parameters of a failed task."""
            # Check if we have enough context to attempt repair
            if not task.failure_context or not task.failure_context.failed_parameters:
                ContextRegistry.get().get_logger().debug_warning(
                    "Parameter Repair",
                    f"Task {task.task_id} has no failure context or failed parameters. Cannot attempt repair.",
                    metadata={
                        "function_name": "attempt_parameter_repair",
                        "task_id": task.task_id,
                    },
                )
                return False, {}

            # Get additional context that's now available
            tool_schema = AgentCoreHelpers.get_tool_schema(task.tool_name)
            error_message = task.failure_context.error_message
            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            failed_params = task.failure_context.failed_parameters

            # Get context from goal validator if available
            validator_feedback = None
            if error_type == "GoalValidationFailure":
                validator_feedback = error_message

            ContextRegistry.get().get_logger().debug_info(
                "Parameter Repair",
                f"Attempting parameter repair for task {task.task_id} with {fail_count} failures",
                metadata={
                    "function_name": "attempt_parameter_repair",
                    "task_id": task.task_id,
                    "error_type": error_type,
                    "fail_count": fail_count,
                },
            )

            # Use LLM to analyze the failure and suggest parameter repairs
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_enhanced_parameter_repair_prompt(
                    task, state, tool_schema
                )
            )

            try:
                model = ModelManager()
                response = model.invoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": human_prompt},
                    ]
                )
                repair_result = ModelManager.convert_to_json(response.content)

                # Extract repaired parameters from LLM response
                repaired_params = repair_result.get("repaired_parameters", {})

                # Validate that the repaired parameters meet the schema
                is_valid, error_msg = (
                    AgentCoreHelpers.ParameterGeneratorHelpers.validate_params(
                        task.tool_name, repaired_params
                    )
                )

                if is_valid:
                    ContextRegistry.get().get_logger().debug_info(
                        "Parameter Repair",
                        f"Successfully repaired parameters for task {task.task_id}",
                        metadata={
                            "function_name": "attempt_parameter_repair",
                            "task_id": task.task_id,
                            "repaired_params": repaired_params,
                        },
                    )
                    return True, repaired_params
                else:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Parameter Repair",
                        f"LLM-suggested parameters failed validation: {error_msg}",
                        metadata={
                            "function_name": "attempt_parameter_repair",
                            "task_id": task.task_id,
                            "validation_error": error_msg,
                        },
                    )
                    return False, {}

            except Exception as e:
                ContextRegistry.get().get_logger().debug_error(
                    "Parameter Repair",
                    f"Failed to repair parameters with LLM: {e}",
                    metadata={
                        "function_name": "attempt_parameter_repair",
                        "task_id": task.task_id,
                        "exception": str(e),
                    },
                )
                # Fallback to basic repair
                required_keys = tool_schema.get("required", [])
                missing_keys = [
                    key for key in required_keys if key not in failed_params
                ]

                if missing_keys:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Parameter Repair",
                        f"Task {task.task_id} is missing required parameters: {missing_keys}. Attempting to add default values.",
                        metadata={
                            "function_name": "attempt_parameter_repair",
                            "task_id": task.task_id,
                        },
                    )
                    # Simple repair: Add empty strings for missing keys
                    repaired_params = failed_params.copy()
                    for key in missing_keys:
                        repaired_params[key] = ""
                    return True, repaired_params

                return False, {}

        @staticmethod
        def convert_decision_task(
            whole_context: list[str], available_tools_str: str, parent_task: TASK
        ) -> list[TASK] | None:
            """
            this convert that whole decision, error recovery strategy, parent failure context, original goal and create return lists of tasks
            :return: list of tasks
            """

            hierarchy_prompt = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                hierarchy_prompt.generate_plan_to_tasks_prompt(
                    whole_context, available_tools_str
                )
            )
            try:
                model = ModelManager()
                response = model.invoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": human_prompt},
                    ]
                )
                task_list = ModelManager.convert_to_json(response.content)
                if isinstance(task_list, list):
                    tasks = []
                    for idx, task_dict in enumerate(task_list):
                        tasks.append(
                            TASK(
                                task_id=str(f"{parent_task.task_id}_{idx}"),
                                description=task_dict.get(
                                    "description", "No description provided"
                                ),
                                tool_name=task_dict.get("tool_name", "unknown_tool"),
                                status="pending",
                                required_context=REQUIRED_CONTEXT(
                                    source_node="error_fallback",
                                    triggering_task_id=parent_task.task_id,
                                ),
                            )
                        )
                    return tasks if tasks else None
                else:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Task Conversion",
                        "LLM response is not a list of tasks.",
                        metadata={
                            "function_name": "convert_decision_task",
                            "response_content": response.content,
                        },
                    )
                    return None
            except Exception as e:
                ContextRegistry.get().get_logger().debug_error(
                    "Task Conversion",
                    f"Failed to convert decision to tasks with LLM: {e}",
                    metadata={
                        "function_name": "convert_decision_task",
                        "exception": str(e),
                    },
                )
                return None

        @staticmethod
        def find_alternative_tool(task: TASK, state: WorkflowStateModel) -> str | None:
            """Use LLM to intelligently find a safer, alternative tool to accomplish the task's goal."""
            # Check if we have enough context to attempt alternative tool selection
            if not task.failure_context or not task.failure_context.error_message:
                ContextRegistry.get().get_logger().debug_warning(
                    "Alternative Tool",
                    f"Task {task.task_id} has no failure context or error message. Cannot find alternative tool.",
                    metadata={
                        "function_name": "find_alternative_tool",
                        "task_id": task.task_id,
                    },
                )
                return None

            # Get error details
            error_message = task.failure_context.error_message
            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            failed_params = task.failure_context.failed_parameters or {}

            # Get context from goal validator if available
            validator_feedback = None
            if error_type == "GoalValidationFailure":
                validator_feedback = error_message

            ContextRegistry.get().get_logger().debug_info(
                "Alternative Tool",
                f"Finding alternative tool for task {task.task_id} with {fail_count} failures",
                metadata={
                    "function_name": "find_alternative_tool",
                    "task_id": task.task_id,
                    "error_type": error_type,
                    "current_tool": task.tool_name,
                },
            )

            # Get all available tools for more intelligent selection
            all_tools = AgentCoreHelpers.get_safe_tools_list()
            available_tools_info = "\n".join(
                [f"• {tool.name}: {tool.description}" for tool in all_tools]
            )

            # Use LLM to analyze the failure and suggest an alternative tool
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_enhanced_alternative_tool_prompt(
                    task, state, all_tools
                )
            )

            try:
                model = ModelManager()
                response = model.invoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": human_prompt},
                    ]
                )
                alternative_result = ModelManager.convert_to_json(response.content)

                # Extract alternative tool from LLM response
                alternative_tool = alternative_result.get("alternative_tool")

                # Validate that the alternative tool exists
                if alternative_tool and alternative_tool in [
                    tool.name for tool in all_tools
                ]:
                    ContextRegistry.get().get_logger().debug_info(
                        "Alternative Tool",
                        f"Selected alternative tool '{alternative_tool}' for task {task.task_id}",
                        metadata={
                            "function name": "find_alternative_tool",
                            "task_id": task.task_id,
                            "alternative_tool": alternative_tool,
                            "reasoning": alternative_result.get(
                                "reasoning", "No reasoning provided"
                            ),
                        },
                    )
                    return alternative_tool
                else:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Alternative Tool",
                        f"LLM-suggested tool '{alternative_tool}' not found in available tools",
                        metadata={
                            "function name": "find_alternative_tool",
                            "task_id": task.task_id,
                            "suggested_tool": alternative_tool,
                        },
                    )
                    return None

            except Exception as e:
                ContextRegistry.get().get_logger().debug_error(
                    "Alternative Tool",
                    f"Failed to find alternative tool with LLM: {e}",
                    metadata={
                        "function name": "find_alternative_tool",
                        "task_id": task.task_id,
                        "exception": str(e),
                    },
                )
                # Fallback to basic pattern matching
                error_message_lower = error_message.lower()
                if (
                    "command not found" in error_message_lower
                    and task.tool_name == "run_shell_command"
                ):
                    ContextRegistry.get().get_logger().debug_info(
                        "Alternative Tool Finder",
                        f"Suggesting google_search for 'command not found' error.",
                        metadata={
                            "function name": "find_alternative_tool",
                            "task_id": task.task_id,
                        },
                    )
                    return "google_search"

                if (
                    "summarize" in task.description.lower()
                    and task.tool_name != "perform_synthesis"
                ):
                    return "perform_synthesis"

                return None

    class EnhancedErrorFallbackHelpers:
        """Enhanced error fallback helpers with LLM-driven strategy selection."""

        @staticmethod
        def decide_recovery_strategy(task: TASK, state: WorkflowStateModel) -> dict:
            """Use LLM to intelligently decide the best recovery strategy based on comprehensive context analysis."""

            # Validate we have enough context to make a decision
            if not task.failure_context:
                ContextRegistry.get().get_logger().debug_warning(
                    "Strategy Decision",
                    f"Task {getattr(task, 'task_id', 'N/A')} has no failure context. Cannot decide strategy.",
                    metadata={
                        "function name": "decide_recovery_strategy",
                        "task_id": getattr(task, "task_id", "N/A"),
                    },
                )
                # Return a safe default strategy
                return {
                    "recovery_strategy": "PARAMETER_REPAIR",
                    "reasoning": "No failure context available, starting with parameter repair as safest option.",
                    "confidence_level": "LOW",
                    "estimated_success_probability": 30,
                    "next_steps": "Attempt to repair parameters with basic logic.",
                }

            # Get all relevant context
            error_message = task.failure_context.error_message
            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            failed_parameters = task.failure_context.failed_parameters or {}

            ContextRegistry.get().get_logger().debug_info(
                "Strategy Decision",
                f"Deciding recovery strategy for task {getattr(task, 'task_id', 'N/A')} with {fail_count} failures",
                metadata={
                    "function name": "decide_recovery_strategy",
                    "task_id": getattr(task, "task_id", "N/A"),
                    "error_type": error_type,
                    "fail_count": fail_count,
                },
            )

            # Get tool schema
            tool_schema = AgentCoreHelpers.get_tool_schema(task.tool_name)

            # Get completed task history for context
            completed_tasks = [
                t
                for t in state.tasks
                if t.status == "completed"
                and hasattr(t, "execution_context")
                and t.execution_context
            ]
            recent_completed_tasks_info = (
                "\n".join(
                    [
                        f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} ({getattr(t, 'tool_name', 'N/A')}) -> {getattr(t.execution_context, 'analysis', 'No analysis') or 'No analysis'}"
                        for t in completed_tasks[-3:]  # Last 3 completed tasks
                    ]
                )
                or "No recent completed tasks"
            )

            # Get failed tasks with validator feedback
            failed_tasks_with_feedback = [
                t
                for t in state.tasks
                if getattr(t, "status", "") == "failed"
                and hasattr(t, "failure_context")
                and t.failure_context
                and getattr(t.failure_context, "error_type", "")
                == "GoalValidationFailure"
            ]

            failed_tasks_info = (
                "\n".join(
                    [
                        f"• Task {getattr(t, 'task_id', 'N/A')}: {getattr(t, 'description', 'N/A')} -> Validator Feedback: {getattr(t.failure_context, 'error_message', 'N/A')}"
                        for t in failed_tasks_with_feedback  # Last 2 failed tasks with feedback
                    ]
                )
                or "No recent failed tasks with validator feedback"
            )

            # Get all available tools
            all_tools = (
                AgentCoreHelpers.get_safe_tools_list()
                if hasattr(AgentCoreHelpers, "get_safe_tools_list")
                else []
            )
            available_tools_info = "\n".join(
                [
                    f"• {getattr(tool, 'name', 'N/A')}: {getattr(tool, 'description', 'N/A')}"
                    for tool in all_tools
                ]
            )
            strategy_history = (
                "\n".join(
                    [
                        f"• Attempt {i + 1}: {s.recovery_strategy} - reasoning: {s.reasoning} - outcome: {s.outcome} \n\t "
                        for i, s in enumerate(task.failure_context.strategy_history)
                    ]
                )
                or "No previous recovery attempts."
            )

            # Use LLM to analyze the failure and suggest the best recovery strategy
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_recovery_strategy_prompt(
                    task_description=task.description,
                    tool_name=task.tool_name,
                    error_message=error_message,
                    error_type=error_type,
                    fail_count=fail_count,
                    failed_parameters=failed_parameters,
                    tool_schema=tool_schema,
                    original_goal=state.original_goal,
                    completed_tasks_context=recent_completed_tasks_info,
                    failed_tasks_context=failed_tasks_info,
                    available_tools=available_tools_info,
                    strategy_hist=strategy_history,
                )
            )

            try:
                model = ModelManager()
                response = model.invoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": human_prompt},
                    ]
                )
                strategy_result = ModelManager.convert_to_json(response.content)

                # Validate that we got a valid strategy
                valid_strategies = [
                    "PARAMETER_REPAIR",
                    "ALTERNATIVE_TOOL",
                    "TASK_DECOMPOSITION",
                    "LLM_RECOVERY",
                    "SKIP",
                ]
                recovery_strategy = (
                    strategy_result.get("recovery_strategy", "PARAMETER_REPAIR")
                    if isinstance(strategy_result, dict)
                    else "PARAMETER_REPAIR"
                )

                if not isinstance(strategy_result, dict):
                    # Ensure a mutable dict for downstream updates
                    strategy_result = {}

                if recovery_strategy not in valid_strategies:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Strategy Decision",
                        f"LLM suggested invalid strategy '{recovery_strategy}'. Falling back to PARAMETER_REPAIR.",
                        metadata={
                            "function name": "decide_recovery_strategy",
                            "task_id": getattr(task, "task_id", "N/A"),
                            "suggested_strategy": recovery_strategy,
                        },
                    )
                    recovery_strategy = "PARAMETER_REPAIR"

                # FIX 3: Enhanced discovery logic - if LLM suggests multiple tools or discovery steps, force TASK_DECOMPOSITION
                next_steps = strategy_result.get("next_steps", "")
                if next_steps and isinstance(next_steps, str):
                    # Count discovery-related tool mentions in next_steps
                    discovery_tool_mentions = 0
                    discovery_keywords = [
                        "list_allowed_directories",
                        "search_files",
                        "list_directory",
                        "find",
                        "discover",
                        "explore",
                        "search",
                        "investigate",
                        "verify",
                        "check",
                        "examine",
                        "analyze",
                    ]
                    for keyword in discovery_keywords:
                        if keyword.lower() in next_steps.lower():
                            discovery_tool_mentions += 1

                    # # this is causing un intentional issues If LLM mentions multiple discovery tools/steps, force decomposition
                    # if discovery_tool_mentions >= 5:
                    #     ContextRegistry.get().get_logger().debug_info("Strategy Decision",
                    #                f"LLM suggested multi-step discovery approach, forcing TASK_DECOMPOSITION for task {getattr(task, 'task_id', 'N/A')}",
                    #                metadata={"original_strategy": str(recovery_strategy), "next_steps": str(next_steps),
                    #                          "discovery_mentions": str(discovery_tool_mentions)})
                    #     recovery_strategy = "TASK_DECOMPOSITION"
                    #     strategy_result["recovery_strategy"] = "TASK_DECOMPOSITION"
                    #     strategy_result[
                    #         "reasoning"] = f"Original: {strategy_result.get('reasoning', '')} | ENHANCED: Multi-step discovery approach detected, forcing decomposition to implement: {next_steps}"

                ContextRegistry.get().get_logger().debug_info(
                    "Strategy Decision",
                    f"Selected strategy '{recovery_strategy}' for task {getattr(task, 'task_id', 'N/A')}",
                    metadata={
                        "function name": "decide_recovery_strategy",
                        "task_id": getattr(task, "task_id", "N/A"),
                        "recovery_strategy": recovery_strategy,
                        "confidence_level": strategy_result.get(
                            "confidence_level", "UNKNOWN"
                        ),
                        "estimated_success_probability": strategy_result.get(
                            "estimated_success_probability", 0
                        ),
                        "reasoning": strategy_result.get(
                            "reasoning", "No reasoning provided"
                        ),
                    },
                )

                return strategy_result

            except Exception as e:
                ContextRegistry.get().get_logger().debug_error(
                    "Strategy Decision",
                    f"Failed to decide recovery strategy with LLM: {e}",
                    metadata={
                        "function name": "decide_recovery_strategy",
                        "task_id": getattr(task, "task_id", "N/A"),
                        "exception": str(e),
                    },
                )
                # Fallback to rule-based decision making
                return AgentCoreHelpers.EnhancedErrorFallbackHelpers._fallback_strategy_selection(
                    task, state
                )

        @staticmethod
        def _fallback_strategy_selection(task: TASK, state: WorkflowStateModel) -> dict:
            """Fallback rule-based strategy selection when LLM fails."""

            if not task.failure_context:
                return {
                    "recovery_strategy": "PARAMETER_REPAIR",
                    "reasoning": "No failure context, starting with parameter repair.",
                    "confidence_level": "LOW",
                    "estimated_success_probability": 30,
                    "next_steps": "Attempt basic parameter repair.",
                }

            error_type = task.failure_context.error_type or ""
            fail_count = task.failure_context.fail_count
            error_message = task.failure_context.error_message.lower()

            # Rule-based decision-making
            if fail_count > 2:
                # High fail count, time for decomposition
                return {
                    "recovery_strategy": "TASK_DECOMPOSITION",
                    "reasoning": f"Task has failed {fail_count} times, suggesting inherent complexity. Decomposition recommended.",
                    "confidence_level": "HIGH",
                    "estimated_success_probability": 70,
                    "next_steps": "Spawn sub-agent to break task into smaller steps.",
                }
            elif (
                "command not found" in error_message
                or "file not found" in error_message
            ):
                # Common tool execution errors
                return {
                    "recovery_strategy": "ALTERNATIVE_TOOL",
                    "reasoning": "Tool execution error (command/file not found), suggesting alternative tool needed.",
                    "confidence_level": "MEDIUM",
                    "estimated_success_probability": 60,
                    "next_steps": "Find and switch to alternative tool.",
                }
            elif "parameter" in error_message or "missing" in error_message:
                # Parameter-related errors
                return {
                    "recovery_strategy": "PARAMETER_REPAIR",
                    "reasoning": "Parameter-related error, suggesting parameter repair needed.",
                    "confidence_level": "HIGH",
                    "estimated_success_probability": 65,
                    "next_steps": "Repair missing or invalid parameters.",
                }
            else:
                # Default to parameter repair for any other errors
                return {
                    "recovery_strategy": "PARAMETER_REPAIR",
                    "reasoning": "Default strategy for unspecified errors.",
                    "confidence_level": "LOW",
                    "estimated_success_probability": 40,
                    "next_steps": "Attempt parameter repair as starting point.",
                }

    class ParameterGeneratorHelpers:
        @staticmethod
        def validate_params(tool_name: str, parameters: dict) -> tuple[bool, str]:
            """Validate parameters against tool schema.
            - Checks required keys
            - Performs basic JSON Schema type validation for common types
            Returns (is_valid, error_message).
            """
            tool_schema = AgentCoreHelpers.get_tool_schema(tool_name)
            # Required keys check
            required_keys = tool_schema.get("required", [])
            missing = [k for k in required_keys if k not in parameters]
            if missing:
                return (
                    False,
                    f"Missing required parameters: {missing} of tool: {tool_name}",
                )

            # Basic type checks (no external dependency)
            properties = (
                tool_schema.get("properties", {})
                if isinstance(tool_schema, dict)
                else {}
            )
            if properties and isinstance(parameters, dict):
                type_map = {
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                type_errors: list[str] = []
                for key, value in parameters.items():
                    prop_schema = properties.get(key)
                    if not prop_schema or not isinstance(prop_schema, dict):
                        continue
                    expected_type = prop_schema.get("type")
                    if isinstance(expected_type, list):
                        expected_python_types = tuple(
                            type_map.get(t) for t in expected_type if t in type_map
                        )
                    else:
                        expected_python_types = type_map.get(expected_type)
                    if expected_python_types is None:
                        continue
                    # Special-cases for number/integer
                    if expected_type == "number" and isinstance(value, (int, float)):
                        pass
                    elif (
                        expected_type == "integer"
                        and isinstance(value, int)
                        and not isinstance(value, bool)
                    ):
                        pass
                    else:
                        try:
                            if not isinstance(value, expected_python_types):
                                type_errors.append(
                                    f"{key} expected {expected_type}, got {type(value).__name__}"
                                )
                        except TypeError:
                            # In case expected_python_types is not a proper type/tuple
                            continue
                if type_errors:
                    return False, f"Type validation failed: {type_errors[:5]}"

            return True, ""

    class ToolExecutionHelpers:
        @classmethod
        def _tool_executor(cls, tool_name: str, parameters: dict) -> tuple[bool, str]:
            """Execute tool and return (success, result)."""

            ContextRegistry.get().get_logger().debug_info(
                "Tool Executor",
                f"Executing tool: '{tool_name}' with parameters: {parameters}",
                metadata={
                    "function name": "__tool_executor",
                    "tool_name": tool_name,
                    "parameters": parameters,
                },
            )

            try:
                registered_tools = AgentCoreHelpers.get_safe_tools_list()
            except RuntimeError as e:
                return (False, str(e))

            tool_to_execute = next(
                (
                    tool
                    for tool in registered_tools
                    if tool.name.lower() == tool_name.lower()
                ),
                None,
            )
            if not tool_to_execute:
                return (False, f"Tool '{tool_name}' not found")

            try:
                invoke_params = parameters.copy()
                invoke_params["tool_name"] = tool_name
                tool_to_execute.invoke(invoke_params)

                responses = ToolResponseManager().get_response()
                if not responses:
                    return (False, f"No response received from tool {tool_name}")

                last_response = responses[-1]
                if not hasattr(last_response, "content"):
                    return (False, f"Invalid response format from tool {tool_name}")

                # Enhanced error detection for RunShellCommand and other tools
                # todo this needs to be more robust and handle more edge cases by llm reasoning about the output
                is_logical_success = True
                logical_failure_message = ""

                if tool_name == "run_shell_command":
                    content = last_response.content
                    is_logical_success = True  # Assume success unless proven otherwise
                    logical_failure_message = ""

                    # Priority 1: Check for a non-zero exit code. This is the most reliable indicator.
                    try:
                        exit_code_match = re.search(r"Exit Code:\s*(\d+)", content)
                        if exit_code_match:
                            exit_code = int(exit_code_match.group(1))
                            if exit_code != 0:
                                is_logical_success = False
                                logical_failure_message = f"Command failed with non-zero exit code {exit_code}. Full output: {content}"
                    except Exception:
                        pass  # Ignore parsing errors, will rely on string checks

                    # Priority 2: If exit code is 0 or absent, check for common error strings in output.
                    if is_logical_success:
                        error_indicators = [
                            "Error (code",
                            "Error:",
                            "Stderr:",  # Check if Stderr has content
                            "command not found",
                            "is not recognized as an internal or external command",
                            "The syntax of the command is incorrect",
                            "Access is denied",
                            "No such file or directory",
                            "Permission denied",
                            "was unexpected at this time",
                        ]
                        # Check for Stderr content specifically
                        stderr_match = re.search(r"Stderr:\s*(.+)", content, re.DOTALL)
                        if (
                            stderr_match
                            and stderr_match.group(1).strip()
                            and stderr_match.group(1).strip() != "(empty)"
                        ):
                            is_logical_success = False
                            logical_failure_message = f"Command produced output on Stderr. Full output: {content}"
                        else:
                            for error_indicator in error_indicators:
                                if error_indicator.lower() in content.lower():
                                    is_logical_success = False
                                    logical_failure_message = f"Command output contained error indicator '{error_indicator}'. Full output: {content}"
                                    break

                elif tool_name in ["read_file", "read_text_file", "write_file"]:
                    # Enhanced error detection for file operations
                    content = last_response.content.lower()
                    file_error_indicators = [
                        "file not found",
                        "no such file",
                        "permission denied",
                        "access denied",
                        "invalid path",
                        "directory not found",
                        "cannot read",
                        "cannot write",
                    ]
                    for error_indicator in file_error_indicators:
                        if error_indicator in content:
                            is_logical_success = False
                            logical_failure_message = last_response.content
                            break

                if is_logical_success:
                    ContextRegistry.get().get_logger().debug_info(
                        "Tool Executor",
                        f"Tool '{tool_name}' executed successfully.",
                        metadata={
                            "function name": "__tool_executor",
                            "tool_name": tool_name,
                            "response_content": (
                                last_response.content[:200] + "..."
                                if len(last_response.content) > 200
                                else last_response.content
                            ),
                        },
                    )
                    return (True, last_response.content)
                else:
                    ContextRegistry.get().get_logger().debug_warning(
                        "Tool Executor",
                        f"Tool '{tool_name}' executed but detected logical failure.",
                        metadata={
                            "function name": "__tool_executor",
                            "tool_name": tool_name,
                            "response_content": (
                                last_response.content[:200] + "..."
                                if len(last_response.content) > 200
                                else last_response.content
                            ),
                            "logical_failure": True,
                        },
                    )
                    return (False, logical_failure_message)
            except Exception as e:
                ContextRegistry.get().get_logger().debug_error(
                    "Tool Executor",
                    f"Exception during tool execution: {str(e)}",
                    metadata={
                        "function name": "__tool_executor",
                        "tool_name": tool_name,
                        "exception": str(e),
                    },
                )
                return (False, f"Error executing tool {tool_name}: {e!s}")

        @staticmethod
        def exeCuteTool(
            parameters: dict, tool_name: str, timeout: int = 60
        ) -> tuple[bool, str]:
            """
            Execute a tool via a separate worker process and enforce a timeout.

            Intended behavior:
            - Run the internal `__tool_executor` in an isolated process or worker.
            - Terminate the worker if it exceeds a configured timeout to avoid hangs.
            - Return a tuple `(success: bool, result: str)` where `result` is the tool output or an error message.

            Return:
            - tuple[bool, str]

            Implementation notes:
            - Use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` to isolate execution.
            - Ensure proper cleanup of processes and robust exception handling to avoid resource leaks.
            """
            from concurrent.futures import ThreadPoolExecutor, TimeoutError

            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                AgentCoreHelpers.ToolExecutionHelpers._tool_executor,
                tool_name,
                parameters,
            )
            try:
                success, result = future.result(timeout=timeout)
                executor.shutdown(
                    wait=True
                )  # Wait for the future to complete if it finishes on time.
                return success, result
            except TimeoutError:
                # The future timed out. Don't wait for it to complete.
                # This will leave a zombie thread if the underlying tool call is stuck,
                # but it will prevent the main workflow from hanging.
                executor.shutdown(wait=False)
                ContextRegistry.get().get_logger().debug_error(
                    "Tool Executor",
                    f"Tool '{tool_name}' execution timed out after {timeout} seconds.",
                    metadata={
                        "function name": "exeCuteTool",
                        "tool_name": tool_name,
                        "timeout": timeout,
                    },
                )
                return False, f"Tool execution timed out after {timeout} seconds"
            except Exception as e:
                # Handle other exceptions during execution.
                executor.shutdown(wait=True)
                ContextRegistry.get().get_logger().debug_error(
                    "Tool Executor",
                    f"Exception during tool execution: {str(e)}",
                    metadata={
                        "function name": "exeCuteTool",
                        "tool_name": tool_name,
                        "exception": str(e),
                    },
                )
                return False, f"Error executing tool {tool_name}: {e!s}"

    class ComplexityAnalyzer:
        """Analyzes task complexity and determines decomposition requirements."""

        @staticmethod
        def analyze_task_complexity(
            task: TASK, spawn_reason: str | None = None
        ) -> dict:
            """Analyze if task is atomic or needs decomposition using tool schema awareness."""
            ContextRegistry.get().get_logger().debug_info(
                "Complexity Analyzer",
                f"Analyzing complexity for Task {task.task_id}: '{task.description}'",
                metadata={
                    "function name": "__analyze_task_complexity",
                    "task_id": task.task_id,
                    "task_description": task.description,
                    "tool_name": task.tool_name,
                },
            )

            tool_schema = AgentCoreHelpers.get_tool_schema(task.tool_name)

            prompt_generator = HierarchicalAgentPrompt()
            # Pass the spawn_reason to the prompt generator
            system_prompt, human_prompt = (
                prompt_generator.generate_tool_schema_complexity_prompt(
                    task.description,
                    task.tool_name,
                    tool_schema,
                    task.depth,
                    parent_context=spawn_reason,
                )
            )

            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )

            analysis_result = ModelManager.convert_to_json(response.content)

            if (
                not isinstance(analysis_result, dict)
                or "requires_decomposition" not in analysis_result
            ):
                simple_tools = [
                    "list_directory",
                    "read_text_file",
                    "write_file",
                    "create_directory",
                    "google_search",
                ]
                is_simple = task.tool_name in simple_tools

                return {
                    "requires_decomposition": not is_simple,
                    "reasoning": f"Fallback analysis - {task.tool_name} is {'simple' if is_simple else 'complex'} based on patterns.",
                    "atomic_tool_name": task.tool_name if is_simple else None,
                }

            ContextRegistry.get().get_logger().debug_info(
                "Complexity Analyzer",
                f"Complexity Analysis Result: {analysis_result}",
                metadata={
                    "function name": "__analyze_task_complexity",
                    "task_id": task.task_id,
                    "analysis_result": analysis_result,
                },
            )
            return analysis_result
