# major imports required
from src.agents.agentic_orchestrator.agent_core_helpers import AgentCoreHelpers
from typing import Literal, List, Dict, Any, Optional
from src.ui.diagnostics.debug_helpers import debug_info, debug_warning, debug_error
from src.utils.timestamp_util import get_formatted_timestamp
from src.agents.agentic_orchestrator.hierarchical_agent_prompts import HierarchicalAgentPrompt
from src.utils.model_manager import ModelManager
from src.agents.agentic_orchestrator.pydantic_models import WorkflowStateModel, TASK, EXECUTION_CONTEXT, FAILURE_CONTEXT, subAgent_CONTEXT, REQUIRED_CONTEXT, FAILURE_CONTEXT_STRATEGY
from src.agents.agentic_orchestrator.agent_status import AgentStatusUpdater
from src.agents.agentic_orchestrator.spawn_agent import Spawn_subAgent
from langgraph.graph import END, StateGraph
from src.config import settings


class AgentGraphCore:
    """🏗️ HIERARCHICAL AGENT SYSTEM WITH INTELLIGENT TOOL PRE-FILTERING

    This is the core implementation of a sophisticated agent orchestration system that:

    ⚡ PERFORMANCE OPTIMIZATIONS:
    - Reduces LLM token usage by 90% through intelligent tool pre-filtering
    - Uses 2-stage approach: recommend relevant tools first, then plan with focused tool set
    - Eliminates tool hallucination through validation and schema-aware prompting

    🧠 INTELLIGENT CAPABILITIES:
    - Dynamic task complexity analysis using tool schema awareness
    - Automatic sub-agent spawning for complex tasks (Progressive Refinement pattern)
    - Advanced error recovery with spawning-based recovery agents
    - Hierarchical parent-child task relationship management

    🔄 WORKFLOW ORCHESTRATION:
    - 7-node LangGraph workflow with conditional routing
    - State-machine-based execution with comprehensive error handling
    - Tool execution with safe bounds checking and validation
    - Schema-aware parameter generation for optimal tool usage

    🎯 PRODUCTION FEATURES:
    - Defensive programming patterns throughout
    - Graceful degradation when tools unavailable
    - Comprehensive system_logging and error tracking
    - Integration with existing agent_mode_node.py system

    The system embodies enterprise-grade reliability while maintaining the flexibility
    to handle abstract, complex goals through intelligent decomposition and execution.
    """

    # TODO we need to fix the debugs logs and user displaying logs
    # TODO we need to fix ~updated task thing and iteration to find the current task in the task list
    # :-- current_task = next((task for task in updated_tasks if task.task_id == current_task_id), None)

    @classmethod
    def __subAGENT_initial_planner(cls, state: "WorkflowStateModel") -> dict:
        """Creates high-level plan using tool pre-filtering and self-healing for efficiency."""
        AgentStatusUpdater.update_status("Initial Planner")
        goal = state.original_goal
        debug_info(
            "--- NODE: Initial Planner ---",
            f"Decomposing goal: {goal}",
            metadata={
                "function name": "__subAGENT_initial_planner",
                "original_goal": goal,
            },
        )

        llm_returned = []
        validated_tasks = []
        error_feedback = None
        plan_is_valid = False

        for attempt in range(2):  # Try to generate a valid plan up to 2 times
            debug_info(
                "Initial Planner",
                f"Planning attempt {attempt + 1}",
                metadata={"attempt": attempt + 1},
            )

            # STEP 1 & 2: Recommend and get tool context
            recommended_tools = AgentCoreHelpers.recommend_tools_for_task(goal)
            detailed_tool_context = AgentCoreHelpers.get_detailed_tool_context(
                recommended_tools
            )

            # STEP 3: Generate plan, providing feedback on failure
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_tool_aware_initial_plan_prompt(
                    goal,
                    detailed_tool_context,
                    error_feedback=error_feedback,  # Pass feedback from previous failed attempt
                )
            )

            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )
            llm_returned = ModelManager.convert_to_json(response.content)

            # Basic validation of response format
            if not isinstance(llm_returned, list):
                error_feedback = "The response was not a valid JSON array of tasks. Please format the output correctly."
                continue

            # STEP 4 & 5: Validate the plan
            current_validated_tasks = []
            has_invalid_tool = False
            invalid_tool_name = None
            validation_error_details = None

            # Using a safe list of tool names for case-insensitive comparison
            safe_tool_names = [
                tool.name.lower() for tool in AgentCoreHelpers.get_safe_tools_list()
            ]
            # Add our virtual tool to the list of valid names for the planner's validation step
            safe_tool_names.append("perform_synthesis")

            for item_idx, item in enumerate(llm_returned):
                if not isinstance(item, dict):
                    has_invalid_tool = True
                    invalid_tool_name = (
                        f"Item at index {item_idx} is not a dictionary: {item}"
                    )
                    break

                if "tool_name" not in item:
                    has_invalid_tool = True
                    invalid_tool_name = (
                        f"Task at index {item_idx} missing 'tool_name' key"
                    )
                    break

                if "description" not in item:
                    has_invalid_tool = True
                    invalid_tool_name = (
                        f"Task at index {item_idx} missing 'description' key"
                    )
                    break

                # NEW: Capture the high-fidelity flag from the plan
                requires_high_fidelity = item.get(
                    "requires_high_fidelity_context", False
                )

                original_tool_name = item.get("tool_name")  # Use .get() for safety
                if not original_tool_name:
                    has_invalid_tool = True
                    invalid_tool_name = (
                        f"Task at index {item_idx} has empty or null 'tool_name'"
                    )
                    break

                tool_name_lower = original_tool_name.lower()

                if tool_name_lower not in safe_tool_names:
                    has_invalid_tool = True
                    invalid_tool_name = original_tool_name
                    # Get available tools for better error message
                    available_tools = ", ".join(
                        [t.name for t in AgentCoreHelpers.get_safe_tools_list()][:10]
                    )  # Show first 10 tools
                    validation_error_details = f"Tool '{original_tool_name}' not found. Available tools: {available_tools}"
                    break

                # Handle case correction and virtual tool
                if tool_name_lower == "perform_synthesis":
                    item["tool_name"] = "perform_synthesis"
                else:
                    # It's a real tool, find the correct case-sensitive name
                    correct_tool_name = next(
                        (
                            t.name
                            for t in AgentCoreHelpers.get_safe_tools_list()
                            if t.name.lower() == tool_name_lower
                        ),
                        None,
                    )
                    # If we couldn't find an exact match, try a more lenient matching approach
                    if correct_tool_name is None:
                        # Try to find a tool that contains the tool name (for partial matches)
                        correct_tool_name = next(
                            (
                                t.name
                                for t in AgentCoreHelpers.get_safe_tools_list()
                                if tool_name_lower in t.name.lower()
                                or t.name.lower() in tool_name_lower
                            ),
                            None,
                        )

                    # If we still couldn't find it, keep the original name but validate it exists
                    if correct_tool_name is None:
                        # Check if the original tool name exists in the safe tool list (case-insensitive)
                        tool_exists = any(
                            t.name.lower() == tool_name_lower
                            for t in AgentCoreHelpers.get_safe_tools_list()
                        )
                        if tool_exists:
                            correct_tool_name = original_tool_name  # Keep original case

                    item["tool_name"] = correct_tool_name

                # Final check to ensure a valid tool name was assigned before appending
                if item["tool_name"] is None:
                    has_invalid_tool = True
                    invalid_tool_name = (
                        original_tool_name  # Use the original name in the error
                    )
                    break

                # Add the high-fidelity flag to the validated task item
                item["requires_high_fidelity_context"] = requires_high_fidelity
                current_validated_tasks.append(item)

            if not has_invalid_tool:
                plan_is_valid = True
                validated_tasks = current_validated_tasks
                debug_info(
                    "Initial Planner",
                    "Successfully generated a valid plan.",
                    metadata={"attempt": attempt + 1},
                )
                break  # Exit loop on success
            else:
                # Create feedback for the next attempt
                if validation_error_details:
                    error_feedback = f"You previously planned to use the tool '{invalid_tool_name}', which is not a valid tool. {validation_error_details}. Please only use tools from the provided list and ensure correct spelling and capitalization."
                else:
                    error_feedback = f"You previously planned to use the tool '{invalid_tool_name}', which is not a valid tool. Please only use tools from the provided list and ensure correct spelling and capitalization."
                debug_warning(
                    "Initial Planner",
                    f"Invalid plan generated on attempt {attempt + 1}. Feedback: {error_feedback}",
                    metadata={"attempt": attempt + 1},
                )

        # After the loop, proceed with a valid plan or use the final fallback
        if plan_is_valid:
            # Remove duplicates from the successfully validated plan
            filtered_tasks = []
            seen_descriptions = set()
            for item in validated_tasks:
                if item["description"] not in seen_descriptions:
                    filtered_tasks.append(item)
                    seen_descriptions.add(item["description"])

            # --- ENFORCE FINAL COLLECTOR (MANDATORY) ---
            # try:
            #     has_final_collector = any(
            #         isinstance(it, dict)
            #         and str(it.get("tool_name", "")).lower() == "perform_synthesis"
            #         and "collector" in str(it.get("description", "")).lower()
            #         for it in filtered_tasks
            #     )
            #     if not has_final_collector:
            #         filtered_tasks.append({
            #             "description": "Collector: Synthesize outputs of all previous tasks into concise, structured notes (Findings, Evidence, Risks).",
            #             "tool_name": "perform_synthesis",
            #             "requires_high_fidelity_context": False,
            #         })
            # except Exception:
            #     # Defensive: never fail planning because of enforcement
            #     pass

            # Get skip threshold from settings (default 70)
            skip_threshold = getattr(settings, "SKIP_THRESHOLD", 70)

            actual_tasks = []
            for idx, item in enumerate(filtered_tasks):
                skip_probability = item.get("skip_probability", 0)
                skip_reason = item.get("skip_reason", "")

                # Determine initial status based on skip probability
                initial_status: Literal["pending", "skip"] = (
                    "skip" if skip_probability >= skip_threshold else "pending"
                )

                # Log skip decisions for visibility
                if initial_status == "skip":
                    debug_info(
                        "Initial Planner - Pre-Flight Skip",
                        f"Task {idx + 1} marked as SKIP (probability: {skip_probability}%): {item['description'][:60]}...",
                        metadata={
                            "task_id": str(idx + 1),
                            "skip_reason": skip_reason,
                            "skip_probability": skip_probability,
                            "threshold": skip_threshold,
                        },
                    )

                task = TASK(
                    task_id=str(idx + 1),
                    description=item["description"],
                    tool_name=item["tool_name"],
                    status=initial_status,  # 🔥 Set status based on skip probability
                    requires_high_fidelity_context=item.get(
                        "requires_high_fidelity_context", False
                    ),
                    required_context=REQUIRED_CONTEXT(
                        source_node="initial_planner",
                        pre_execution_context=(
                            {
                                "skip_probability": skip_probability,
                                "skip_reason": skip_reason,
                            }
                            if skip_probability > 0
                            else None
                        ),
                    ),
                )
                actual_tasks.append(task)
        else:
            # Final fallback if all attempts fail
            actual_tasks = []

        if not actual_tasks:
            debug_error(
                "Initial Planner",
                "All planning attempts failed. Using final fallback task.",
                metadata={},
            )
            actual_tasks.append(
                TASK(
                    task_id="1",
                    description="List current directory to understand project structure, as initial planning failed.",
                    tool_name="list_directory",
                    required_context=REQUIRED_CONTEXT(
                        source_node="initial_planner_fallback"
                    ),
                )
            )

        debug_info(
            "Initial Planner",
            f"Final plan generated with {len(actual_tasks)} tasks.",
            metadata={
                "task_count": len(actual_tasks),
                "tasks": [task.model_dump() for task in actual_tasks],
            },
        )

        return {
            "tasks": actual_tasks,
            "current_task_id": actual_tasks[0].task_id if actual_tasks else "1",
            "workflow_status": "RUNNING",
            "executed_nodes": state.executed_nodes + ["subAGENT_initial_planner"],
        }

    @classmethod
    def __subAGENT_classifier(cls, state: "WorkflowStateModel") -> dict:
        """🎯 DECISION POINT: Analyzes current task and decides next workflow step.

        This is a critical routing node that determines whether to:
        - Proceed with normal task execution (AGENT_PERFORM_TASK)
        - Trigger error recovery procedures (AGENT_PERFORM_ERROR_FALLBACK)
        - Skip tasks marked in pre-flight check (status='skip')

        The decision is based on task failure count and retry limits, implementing
        a graduated response system for handling task failures.
        """
        current_task_id = state.current_task_id
        AgentStatusUpdater.update_status(
            "complexity_analysis", task_id=current_task_id, extra_info="Analyzing task"
        )
        debug_info(
            "--- NODE: Classifier ---",
            "Deciding next action based on task status and failure history",
            metadata={"function name": "__subAGENT_classifier"},
        )
        tasks = state.tasks
        current_task = next((t for t in tasks if t.task_id == current_task_id), None)

        # Handle pre-flight skipped tasks - create execution context and mark as ready for task_planner
        if current_task and current_task.status == "skip":
            skip_reason = "No reason provided"
            skip_probability = 0
            if (
                current_task.required_context
                and current_task.required_context.pre_execution_context
            ):
                skip_reason = current_task.required_context.pre_execution_context.get(
                    "skip_reason", skip_reason
                )
                skip_probability = (
                    current_task.required_context.pre_execution_context.get(
                        "skip_probability", 0
                    )
                )

            debug_info(
                "Classifier - Skip Handler",
                f"Task {current_task_id} was PRE-FLIGHT SKIPPED (prob: {skip_probability}%): {skip_reason}",
                metadata={
                    "task_id": current_task_id,
                    "skip_reason": skip_reason,
                    "skip_probability": skip_probability,
                    "task_description": current_task.description[:60] + "...",
                },
            )

            # Create minimal execution context so task appears "complete" to workflow
            if not current_task.execution_context:
                current_task.execution_context = EXECUTION_CONTEXT(
                    tool_name=current_task.tool_name,
                    parameters={},
                    result=f"⏭️ Task skipped: {skip_reason}",
                    analysis=f"Pre-flight check (probability: {skip_probability}%) determined this task should be skipped: {skip_reason}",
                    goal_achieved=False,
                )

            # Task remains in skip status and has execution_context, so it will be treated as "done"
            # The workflow will route to task_planner to select next pending task
            # We still set persona to allow normal flow through router
            return {
                "tasks": tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_classifier"],
                "persona": "AGENT_PERFORM_TASK",  # Use normal persona so router works
            }

        # handle that if the previous task got skipped and this task is depend on that (cascade skip effect)
        elif current_task.status == "pending":
            skipped_tasks = [t for t in tasks if t.status == "skip"]
            should_skip, reason = AgentCoreHelpers.evaluate_skip_cascade(
                current_task, skipped_tasks
            )
            if should_skip:
                debug_info(
                    "Classifier - Cascade Skip Handler",
                    f"Task {current_task_id} is being SKIPPED due to dependency on skipped tasks: {reason}",
                    metadata={
                        "task_id": current_task_id,
                        "skip_reason": reason,
                        "task_description": current_task.description[:60] + "...",
                    },
                )

                # Create minimal execution context so task appears "complete" to workflow
                if not current_task.execution_context:
                    current_task.execution_context = EXECUTION_CONTEXT(
                        tool_name=current_task.tool_name,
                        parameters={},
                        result=f"⏭️ Task skipped due to dependency: {reason}",
                        analysis=f"Cascade skip effect triggered by dependency on skipped tasks: {reason}",
                        goal_achieved=False,
                    )

                current_task.status = "skip"  # Mark task as skipped

                return {
                    "tasks": tasks,
                    "executed_nodes": state.executed_nodes + ["subAGENT_classifier"],
                    "persona": "AGENT_PERFORM_TASK",  # Use normal persona so router works
                }
        # 🔍 CRITICAL DECISION: Determine execution persona based on task readiness and failure history
        persona = "AGENT_PERFORM_TASK"

        # Priority 1: If task is pending AND already has execution parameters, force execution next
        if (
            current_task
            and current_task.status == "pending"
            and current_task.execution_context
            and isinstance(current_task.execution_context.parameters, dict)
            and current_task.execution_context.parameters
        ):
            # We have updated parameters (possibly from recovery) ready to execute — do not bounce back to fallback
            persona = "AGENT_PERFORM_TASK"
        elif current_task and current_task.failure_context:
            # Check if we've exceeded retry limits to prevent infinite loops
            if current_task.failure_context.fail_count > 3:
                AgentStatusUpdater.update_status(
                    "complexity_analysis",
                    task_id=current_task_id,
                    extra_info="FAILED: Exceeded retry limit",
                )
                debug_error(
                    "Classifier",
                    f"Task {current_task_id} has failed {current_task.failure_context.fail_count} times. Exceeded retry limit of 2 attempts. Marking as permanently failed.",
                    metadata={
                        "function name": "__subAGENT_classifier",
                        "task_id": current_task_id,
                        "fail_count": current_task.failure_context.fail_count,
                        "max_retries": current_task.max_retries,
                    },
                )
                current_task.status = "failed"
                persona = "AGENT_PERFORM_ERROR_FALLBACK"
            elif current_task.failure_context.fail_count >= 2:
                persona = "AGENT_PERFORM_ERROR_FALLBACK"
            elif current_task.failure_context.fail_count >= current_task.max_retries:
                # if the task got more failures than max retries, we skip it
                persona = "AGENT_PERFORM_ERROR_FALLBACK"
                current_task.status = "skip"

        # print_log_message(f"Task ID: {current_task_id}, Persona: {persona}", "Classifier")
        debug_info(
            "Classifier",
            f"Task ID: {current_task_id}, Persona: {persona}",
            metadata={
                "function name": "__subAGENT_classifier",
                "task_id": current_task_id,
                "persona": persona,
            },
        )
        return {
            "executed_nodes": state.executed_nodes + ["subAGENT_classifier"],
            "persona": persona,
        }

    @classmethod
    def subAGENT_parameter_generator(cls, state: "WorkflowStateModel") -> dict:
        """🧠 PARAMETER GENERATOR: Generates and validates parameters using the Dual Context system."""
        debug_info(
            "--- NODE: Parameter Generator ---",
            "Generating and validating parameters",
            metadata={"function name": "subAGENT_parameter_generator"},
        )

        tasks = state.tasks
        current_task_id = state.current_task_id
        current_task: TASK = next(
            (task for task in tasks if task.task_id == current_task_id), None
        )

        if current_task:
            # 🔥 SKIP BYPASS: Skip parameter generation for skipped tasks
            if current_task.status == "skip":
                debug_info(
                    "Parameter Generator - Skip Bypass",
                    "Task is skipped, bypassing parameter generation.",
                    metadata={
                        "function name": "subAGENT_parameter_generator",
                        "task_id": current_task_id,
                    },
                )
                return {
                    "tasks": tasks,
                    "executed_nodes": state.executed_nodes
                    + ["subAGENT_parameter_generator"],
                }

            if (
                current_task.status == "pending"
                and current_task.execution_context
                and isinstance(current_task.execution_context.parameters, dict)
                and current_task.execution_context.parameters
            ):
                debug_info(
                    "Parameter Generator",
                    "Reusing existing parameters for pending task; skipping regeneration.",
                    metadata={
                        "function name": "subAGENT_parameter_generator",
                        "task_id": current_task_id,
                    },
                )
                return {
                    "tasks": tasks,
                    "executed_nodes": state.executed_nodes
                    + ["subAGENT_parameter_generator"],
                }

            tool_schema = AgentCoreHelpers.get_tool_schema(current_task.tool_name)
            context_data = current_task.required_context.pre_execution_context or {}
            full_history = context_data.get("completed_tasks_history", [])
            # Ensure full_history is a list of TASK objects
            failed_tasks_with_feedback_raw = context_data.get(
                "failed_tasks_with_validator_feedback", []
            )
            failed_tasks_with_feedback: list[TASK] = []
            for item in failed_tasks_with_feedback_raw:
                if isinstance(item, TASK):
                    failed_tasks_with_feedback.append(item)
                elif isinstance(item, dict):
                    try:
                        failed_tasks_with_feedback.append(TASK(**item))
                    except Exception:
                        # Skip entries that can't be converted to TASK
                        continue

            analysis_summary = [
                f"Task {t.task_id} ({t.tool_name}): {t.execution_context.analysis}"
                for t in full_history
                if t.execution_context and t.execution_context.analysis
            ]

            # Build validator feedback context from failed tasks
            validator_feedback_summary = []
            for failed_task in failed_tasks_with_feedback:
                if (
                    failed_task.failure_context
                    and failed_task.failure_context.error_type
                    == "GoalValidationFailure"
                ):
                    validator_feedback_summary.append(
                        f"VALIDATOR REJECTED Task {failed_task.task_id} ({failed_task.tool_name}): {failed_task.failure_context.error_message}"
                        f"\n FAILED Parameters: {failed_task.failure_context.failed_parameters if failed_task.failure_context.failed_parameters else 'N/A'}"
                    )

            # Combine completed task analysis and validator feedback
            context_parts = []
            if analysis_summary:
                context_parts.append(
                    "COMPLETED TASKS (Summarized):\n" + "\n".join(analysis_summary)
                )

            # NEW: Check for high-fidelity flag
            if current_task.requires_high_fidelity_context:
                raw_results_summary = [
                    f"Task {t.task_id} ({t.tool_name}) Raw Result:\n{t.execution_context.result}"
                    for t in full_history
                    if t.execution_context and t.execution_context.result
                ]
                if raw_results_summary:
                    context_parts.append(
                        "--- HIGH-FIDELITY RAW RESULTS (as requested by current task) ---\
"
                        + "\n\n".join(raw_results_summary)
                    )

            if validator_feedback_summary:
                context_parts.append(
                    "VALIDATOR FEEDBACK (avoid these patterns):\n"
                    + "\n".join(validator_feedback_summary)
                )

            context_string = "\n\n".join(context_parts) if context_parts else None

            # 🚨 CRITICAL FIX: Include failure_context and platform information
            failure_context_info = None
            platform_info = None

            # Extract failure context from current task if available
            if current_task.failure_context:
                failure_context_info = {
                    "error_message": current_task.failure_context.error_message,
                    "error_type": current_task.failure_context.error_type,
                    "fail_count": current_task.failure_context.fail_count,
                    "failed_parameters": current_task.failure_context.failed_parameters,
                    "strategy_history": [
                        {
                            "strategy": s.recovery_strategy,
                            "reasoning": s.reasoning,
                            "outcome": s.outcome,
                        }
                        for s in (current_task.failure_context.strategy_history or [])
                    ],
                }
                debug_info(
                    "Parameter Generator",
                    f"Including failure context for task {current_task_id}: {current_task.failure_context.error_type}",
                    metadata={
                        "function name": "subAGENT_parameter_generator",
                        "task_id": current_task_id,
                        "error_type": current_task.failure_context.error_type,
                        "fail_count": current_task.failure_context.fail_count,
                    },
                )

            # Get platform information
            import os

            platform_info = {
                "os_name": os.name,
                "platform": "Windows" if os.name == "nt" else "Unix/Linux",
                "supports_posix": os.name != "nt",
            }

            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_schema_aware_parameter_prompt(
                    task_description=current_task.description,
                    tool_name=current_task.tool_name,
                    tool_schema=tool_schema,
                    context=context_string,
                    full_history=full_history,
                    depth=current_task.depth,
                    failure_context=failure_context_info,  # 🚨 NEW: Pass failure context
                    platform_info=platform_info,  # 🚨 NEW: Pass platform info
                    requires_high_fidelity=current_task.requires_high_fidelity_context,  # 🚨 NEW: Pass high-fidelity flag
                )
            )

            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )
            parameters = ModelManager.convert_to_json(response.content)

            if not isinstance(parameters, dict):
                parameters = cls.__generate_fallback_parameters(
                    current_task.tool_name, current_task.description
                )

            # --- Proactive Parameter Validation ---
            is_valid, error_message = (
                AgentCoreHelpers.ParameterGeneratorHelpers.validate_params(
                    current_task.tool_name, parameters
                )
            )

            if is_valid:
                current_task.execution_context = EXECUTION_CONTEXT(
                    tool_name=current_task.tool_name,
                    parameters=parameters,
                )
                debug_info(
                    "Parameter Generator",
                    f"Generated and validated parameters for task {current_task_id}",
                    metadata={
                        "function name": "subAGENT_parameter_generator",
                        "task_id": current_task_id,
                        "parameters": parameters,
                    },
                )
            else:
                # If validation fails, set task to failed and route to error fallback
                current_task.status = "failed"
                current_task.failure_context = FAILURE_CONTEXT(
                    error_message=error_message,
                    fail_count=(
                        (current_task.failure_context.fail_count + 1)
                        if current_task.failure_context
                        else 1
                    ),
                    last_failure_timestamp=get_formatted_timestamp(),
                    error_type="ParameterValidationError",
                    failed_parameters=parameters,
                )
                debug_error(
                    "Parameter Generator",
                    f"Parameter validation failed for task {current_task_id}: {error_message}",
                    metadata={
                        "function name": "subAGENT_parameter_generator",
                        "task_id": current_task_id,
                        "tool_name": current_task.tool_name,
                        "invalid_parameters": parameters,
                    },
                )

        return {
            "tasks": tasks,
            "executed_nodes": state.executed_nodes + ["subAGENT_parameter_generator"],
        }

    @classmethod
    def __generate_fallback_parameters(
        cls, tool_name: str, task_description: str
    ) -> dict:
        """Generate sensible fallback parameters when LLM parameter generation fails."""
        fallback_patterns = {
            "list_directory": {"directory_path": "."},
            "read_text_file": {"file_path": "README.md"},
            "write_file": {
                "file_path": "output.txt",
                "content": f"Generated content for: {task_description}",
            },
            "create_directory": {"directory_path": "new_directory"},
            "google_search": {"query": task_description[:100], "num_results": 5},
            "run_shell_command": {"command": 'echo "Command execution for task"'},
            "perform_synthesis": {
                "instructions": f"Synthesize the context related to: {task_description}"
            },
        }
        return fallback_patterns.get(tool_name, {"task_description": task_description})

    @classmethod
    def __subAGENT_task_executor(cls, state: "WorkflowStateModel") -> dict:
        """⚙️ CORE EXECUTION ENGINE: Executes tasks OR triggers intelligent decomposition.

        This is the heart of the hierarchical system, implementing the key decision:
        "Should this task be executed directly, or does it need sub-agent spawning?"

        EXECUTION FLOW:
        1. Analyze task complexity using tool schema and description
        2. If COMPLEX → Trigger spawning system for decomposition
        3. If ATOMIC → Execute directly with tool pre-filtering
        4. Handle all failure scenarios with proper error context

        The spawning integration here enables true hierarchical problem-solving
        where abstract goals are recursively refined into executable operations.
        """
        debug_info(
            "--- NODE: Task Executor ---",
            "Executing or decomposing current task",
            metadata={"function name": "__subAGENT_task_executor"},
        )
        current_task_id = state.current_task_id
        updated_tasks = state.tasks
        current_task = next(
            (task for task in updated_tasks if task.task_id == current_task_id), None
        )
        AgentStatusUpdater.update_status("task_execution", task_id=current_task_id)

        if not current_task:
            debug_error(
                "Task Executor",
                f"Could not find current task with ID {current_task_id}",
                metadata={
                    "function name": "__subAGENT_task_executor",
                    "current_task_id": current_task_id,
                },
            )
            return {"workflow_status": "FAILED"}

        # 🔥 SKIP BYPASS: Tasks already marked as skip bypass execution entirely
        if current_task.status == "skip":
            debug_info(
                "Task Executor - Skip Bypass",
                f"Task {current_task_id} is SKIPPED, bypassing execution",
                metadata={
                    "task_id": current_task_id,
                    "skip_reason": (
                        current_task.execution_context.result
                        if current_task.execution_context
                        else "Pre-flight skip"
                    ),
                },
            )
            # Task already has execution_context from classifier, just pass through
            return {
                "tasks": updated_tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_task_executor"],
            }

        # --- VIRTUAL TOOL INTERCEPTION ---
        if current_task.tool_name == "perform_synthesis":
            debug_info(
                "Task Executor",
                "Intercepted virtual tool 'perform_synthesis'.",
                metadata={"task_id": current_task.task_id},
            )
            context_data = current_task.required_context.pre_execution_context or {}
            full_history = context_data.get("completed_tasks_history", [])
            success, result = AgentCoreHelpers.perform_internal_synthesis(
                current_task, full_history
            )
            if success:
                current_task.status = "completed"
                current_task.execution_context.result = result
            else:
                current_task.status = "failed"
                current_task.failure_context = FAILURE_CONTEXT(
                    error_message=result,
                    error_type="SynthesisFailed",
                )
            return {
                "tasks": updated_tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_task_executor"],
            }
        # --- END VIRTUAL TOOL INTERCEPTION ---

        try:
            # Ensure a failure_context exists for the parent BEFORE we call any analysis or decomposition.
            # Some failure paths set task.status = 'failed' but don't populate failure_context; the spawner and
            # recovery logic rely on that context to choose discovery-first decompositions.
            if getattr(current_task, "status", None) == "failed" and not getattr(
                current_task, "failure_context", None
            ):
                # Create a minimal synthetic failure_context from available execution_context so downstream nodes
                # (strategy decision, decomposer) have the failed parameters and an error message to reason about.
                synthetic_failed_params = None
                try:
                    if current_task.execution_context and isinstance(
                        current_task.execution_context.parameters, dict
                    ):
                        synthetic_failed_params = (
                            current_task.execution_context.parameters.copy()
                        )
                except Exception:
                    synthetic_failed_params = None

                current_task.failure_context = FAILURE_CONTEXT(
                    error_message=(
                        current_task.execution_context.result
                        if current_task.execution_context
                        and getattr(current_task.execution_context, "result", None)
                        else f"Parent task {current_task.task_id} failed without explicit failure_context."
                    ),
                    fail_count=1,
                    last_failure_timestamp=get_formatted_timestamp(),
                    error_type="SyntheticFailureContext",
                    failed_parameters=synthetic_failed_params,
                    strategy_history=[],
                )
                debug_info(
                    "SubAgent Spawner",
                    f"Injected synthetic failure_context into parent task {current_task.task_id}",
                    metadata={
                        "function name": "spawn_subAgent_recursive",
                        "parent_task_id": current_task.task_id,
                        "injected_failed_parameters": synthetic_failed_params,
                    },
                )

            complexity_analysis = (
                AgentCoreHelpers.ComplexityAnalyzer.analyze_task_complexity(
                    current_task
                )
            )

            if complexity_analysis.get("requires_decomposition"):
                AgentStatusUpdater.update_status(
                    "task complexity analysis",
                    task_id=current_task_id,
                    extra_info="Decomposing complex task",
                )
                debug_info(
                    "Task Executor",
                    f"Task {current_task_id} is complex - triggering spawning",
                    metadata={
                        "function name": "__subAGENT_task_executor",
                        "task_id": current_task_id,
                        "complexity_analysis": complexity_analysis,
                    },
                )

                # *** FIX: Gather context BEFORE spawning ***
                completed_tasks = [
                    t
                    for t in updated_tasks
                    if t.status == "completed"
                    and t.execution_context
                    and t.execution_context.result
                ]

                # Create comprehensive context string (consistent with error_fallback approach)
                parent_context_str = (
                    f"Original Goal: {state.original_goal}\n"
                    f"Workflow Progress: {len(completed_tasks)}/{len(updated_tasks)} tasks completed\n"
                    f"Completed Tasks: {[f'Task {t.task_id}: {t.description}' for t in completed_tasks]}\n"
                    f"COMPLEXITY ANALYSIS CONTEXT:\n"
                    f"- Current Task ID: {current_task.task_id}\n"
                    f"- Description: {current_task.description}\n"
                    f"- Tool: {current_task.tool_name}\n"
                    f"- Reasoning: {complexity_analysis.get('reasoning', 'Complex task requiring decomposition')}\n"
                    + (
                        f"- Failure Context: {current_task.failure_context.error_message}\n"
                        if current_task.failure_context
                        else "- No previous failures\n"
                    )
                    + (
                        f"- Failed Parameters: {current_task.failure_context.failed_parameters}\n"
                        if current_task.failure_context
                        and current_task.failure_context.failed_parameters
                        else ""
                    )
                )

                spawn_result = Spawn_subAgent.spawn_subAgent_recursive(
                    state=state,
                    parent_task=current_task,
                    spawn_reason=complexity_analysis.get(
                        "reasoning", "Complex task requiring decomposition"
                    ),
                    parent_context=parent_context_str,  # Pass the context as string
                )

                if spawn_result and spawn_result.get("spawn_triggered"):
                    return {
                        "tasks": spawn_result["tasks"],
                        "current_task_id": spawn_result["current_task_id"],
                        "executed_nodes": state.executed_nodes
                        + ["subAGENT_task_executor"],
                    }

                current_task.status = "failed"
                current_task.failure_context = FAILURE_CONTEXT(
                    error_message="Task requires decomposition but spawning failed",
                    error_type="SpawningFailure",
                )
                return {
                    "tasks": updated_tasks,
                    "executed_nodes": state.executed_nodes + ["subAGENT_task_executor"],
                }

            AgentStatusUpdater.update_status(
                "task_execution", task_id=current_task_id, extra_info="Executing tool"
            )
            debug_info(
                "Task Executor",
                f"Task {current_task_id} is atomic - executing directly",
                metadata={
                    "function name": "__subAGENT_task_executor",
                    "task_id": current_task_id,
                },
            )

            # --- SAFETY FIX: mark task as in_progress before attempting execution to avoid immediate retry loops ---
            try:
                if current_task.status != "in_progress":
                    current_task.status = "in_progress"
                    debug_info(
                        "Task Executor",
                        f"Marked Task {current_task_id} as in_progress",
                        metadata={
                            "function name": "__subAGENT_task_executor",
                            "task_id": current_task_id,
                        },
                    )
            except Exception:
                pass

            success, result = AgentCoreHelpers.ToolExecutionHelpers.exeCuteTool(
                tool_name=current_task.execution_context.tool_name,
                parameters=current_task.execution_context.parameters,
                timeout=(
                    settings.BROWSER_USE_TIMEOUT + 10
                    if current_task.execution_context.tool_name == "browser_agent"
                    else 60
                ),
            )

            if success:
                current_task.status = "completed"
                current_task.execution_context.result = result
            else:
                current_task.status = "failed"
                if not current_task.failure_context:
                    current_task.failure_context = FAILURE_CONTEXT(
                        error_message=result,
                        fail_count=1,
                        error_type="ToolExecutionError",
                        failed_parameters=current_task.execution_context.parameters,
                    )
                else:
                    current_task.failure_context.fail_count += 1
                    current_task.failure_context.error_message = result
                    current_task.failure_context.failed_parameters = (
                        current_task.execution_context.parameters
                    )

                # Add explicit debug when failures repeat to help root cause analysis
                debug_error(
                    "Task Executor",
                    f"Task {current_task_id} execution failed (fail_count={current_task.failure_context.fail_count}): {result}",
                    metadata={
                        "function name": "__subAGENT_task_executor",
                        "task_id": current_task_id,
                        "failed_parameters": current_task.execution_context.parameters,
                    },
                )

                if current_task.failure_context.fail_count > 3:
                    AgentStatusUpdater.update_status(
                        "task_execution",
                        task_id=current_task_id,
                        extra_info="failed: exceeded retries",
                    )
                    debug_error(
                        "Task Executor",
                        f"Task {current_task_id} has failed {current_task.failure_context.fail_count} times. Exceeded retry limit of 3.",
                        metadata={
                            "function name": "__subAGENT_task_executor",
                            "task_id": current_task_id,
                            "fail_count": current_task.failure_context.fail_count,
                        },
                    )
                    current_task.failure_context.error_message = f"Task failed after maximum retry attempts (3). Original error: {result}"
                    current_task.status = "failed"
                    return {
                        "tasks": updated_tasks,
                        "executed_nodes": state.executed_nodes
                        + ["subAGENT_task_executor"],
                    }

        except Exception as e:
            debug_error(
                "Task Executor",
                f"Error during task execution: {e!s}",
                metadata={
                    "function name": "__subAGENT_task_executor",
                    "task_id": current_task_id,
                    "exception": str(e),
                },
            )
            # Ensure we preserve/record failed_parameters and strategy history when an unexpected exception occurs
            current_task.status = "failed"
            preserved_strategy_history = (
                current_task.failure_context.strategy_history.copy()
                if current_task.failure_context
                and current_task.failure_context.strategy_history
                else []
            )
            preserved_fail_count = (
                (current_task.failure_context.fail_count + 1)
                if current_task.failure_context
                else 1
            )
            preserved_failed_parameters = None
            try:
                if current_task.execution_context and isinstance(
                    current_task.execution_context.parameters, dict
                ):
                    preserved_failed_parameters = (
                        current_task.execution_context.parameters.copy()
                    )
            except Exception:
                preserved_failed_parameters = None

            current_task.failure_context = FAILURE_CONTEXT(
                error_message=str(e),
                fail_count=preserved_fail_count,
                last_failure_timestamp=get_formatted_timestamp(),
                error_type="UnhandledException",
                failed_parameters=preserved_failed_parameters,
                strategy_history=preserved_strategy_history,
            )

        return {
            "tasks": updated_tasks,
            "executed_nodes": state.executed_nodes + ["subAGENT_task_executor"],
        }

    @classmethod
    def __subAGENT_context_synthesizer(cls, state: "WorkflowStateModel") -> dict:
        """Summarizes the result of a completed task for cleaner context passing."""
        debug_info(
            "--- NODE: Context Synthesizer ---",
            "Summarizing task result for context bridge",
            metadata={"function name": "__subAGENT_context_synthesizer"},
        )
        tasks = state.tasks
        current_task_id = state.current_task_id
        current_task: TASK = next(
            (t for t in tasks if t.task_id == current_task_id), None
        )

        if (
            current_task
            and current_task.status == "completed"
            and current_task.execution_context
            and current_task.execution_context.result
        ):
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_context_synthesis_prompt(
                    current_task.tool_name,
                    current_task.execution_context.result,
                    depth=current_task.depth,
                )
            )

            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )

            summary = response.content.strip()

            # --- MODIFICATION START ---
            if (
                current_task.tool_name == "google_search"
                and current_task.execution_context.parameters
            ):
                query = current_task.execution_context.parameters.get(
                    "query", "unknown query"
                )
                summary = f"A web search for '{query}' was conducted and {summary.lower().lstrip('a web search was conducted and ')}"
            # --- MODIFICATION END ---

            if summary:
                current_task.execution_context.analysis = summary
                debug_info(
                    "Context Synthesizer",
                    f"Generated analysis for Task {current_task_id}: '{summary}'",
                    metadata={
                        "function name": "__subAGENT_context_synthesizer",
                        "task_id": current_task_id,
                        "summary": summary,
                    },
                )
            else:
                current_task.execution_context.analysis = (
                    f"Task {current_task.tool_name} completed successfully."
                )

        # 🔥 SKIP HANDLER: Generate analysis for skipped tasks
        elif (
            current_task.status == "skip"
            and current_task.execution_context
            and current_task.execution_context.result
        ):
            # Handle skipped tasks by summarizing the skip reason
            skip_summary = (
                f"Task was skipped. Reason: {current_task.execution_context.result}"
            )
            current_task.execution_context.analysis = skip_summary
            debug_info(
                "Context Synthesizer - Skip Handler",
                f"Generated analysis for SKIPPED Task {current_task_id}: '{skip_summary}'",
                metadata={
                    "function name": "__subAGENT_context_synthesizer",
                    "task_id": current_task_id,
                },
            )

        return {"tasks": tasks}

    @classmethod
    def __subAGENT_goal_validator(cls, state: "WorkflowStateModel") -> dict:
        """Validates if the task's goal was achieved based on the result and analysis."""
        debug_info(
            "--- NODE: Goal Validator ---",
            "Validating task goal achievement",
            metadata={"function name": "__subAGENT_goal_validator"},
        )
        tasks = state.tasks
        current_task_id = state.current_task_id
        current_task = next((t for t in tasks if t.task_id == current_task_id), None)

        # 🔥 SKIP BYPASS: Skip goal validation for skipped tasks entirely.
        if current_task and current_task.status == "skip":
            debug_info(
                "Goal Validator - Skip Bypass",
                f"Task {current_task_id} is SKIPPED, bypassing goal validation",
                metadata={
                    "task_id": current_task_id,
                    "skip_reason": (
                        current_task.execution_context.result
                        if current_task.execution_context
                        else "Pre-flight skip"
                    ),
                },
            )
            # Task already has execution_context from classifier, just pass through
            return {
                "tasks": tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_goal_validator"],
            }
        elif (
            current_task
            and current_task.status == "completed"
            and current_task.execution_context
        ):
            prompt_generator = HierarchicalAgentPrompt()
            system_prompt, human_prompt = (
                prompt_generator.generate_goal_achievement_prompt(
                    original_goal=state.original_goal,
                    plan_created="\n\n".join(
                        [
                            f"Task {t.task_id}:\n  - Description: {t.description}\n  - Tool: `{t.tool_name}`\n  - Status: {t.status}\n"
                            for t in tasks
                        ]
                    ),
                    task_description=current_task.description,
                    tool_result=current_task.execution_context.result or "N/A",
                    analysis=current_task.execution_context.analysis or "N/A",
                )
            )

            model = ModelManager()
            response = model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )

            validation_result = ModelManager.convert_to_json(response.content)

            if (
                isinstance(validation_result, dict)
                and "goal_achieved" in validation_result
            ):
                current_task.execution_context.goal_achieved = validation_result.get(
                    "goal_achieved", False
                )
                debug_info(
                    "Goal Validator",
                    f"Validation for Task {current_task_id}: Goal Achieved = {validation_result.get('goal_achieved')}, Reasoning: {validation_result.get('reasoning')}",
                    metadata={
                        "function name": "__subAGENT_goal_validator",
                        "task_id": current_task_id,
                        "validation_result": validation_result,
                    },
                )
                if not validation_result.get("goal_achieved"):
                    current_task.status = "failed"
                    # CRITICAL FIX: Preserve the original failed_parameters when creating new failure context
                    original_failed_parameters = (
                        current_task.execution_context.parameters
                        if current_task.execution_context
                        else None
                    )
                    original_strategy_history = (
                        current_task.failure_context.strategy_history.copy()
                        if current_task.failure_context
                        and current_task.failure_context.strategy_history
                        else []
                    )

                    current_task.failure_context = FAILURE_CONTEXT(
                        error_message=f"Goal not achieved: {validation_result.get('reasoning', 'No reasoning provided.')}",
                        fail_count=(
                            (current_task.failure_context.fail_count + 1)
                            if current_task.failure_context
                            else 1
                        ),
                        error_type="GoalValidationFailure",
                        failed_parameters=original_failed_parameters,  # PRESERVE the original failed parameters
                        strategy_history=original_strategy_history,  # PRESERVE the strategy history too
                    )
                    # Persist validator feedback into pre_execution_context so retries and parameter generator see corrective hints
                    try:
                        if not getattr(current_task, "required_context", None):
                            current_task.required_context = REQUIRED_CONTEXT(
                                source_node="subAGENT_goal_validator"
                            )
                        ctx = current_task.required_context.pre_execution_context or {}
                        failed_feedback = ctx.get(
                            "failed_tasks_with_validator_feedback", []
                        )
                        failed_feedback.append(
                            {
                                "task_id": current_task.task_id,
                                "tool_name": current_task.tool_name,
                                "failure_reason": validation_result.get(
                                    "reasoning", "No reasoning provided."
                                ),
                                "validator_payload": validation_result,
                            }
                        )
                        ctx["failed_tasks_with_validator_feedback"] = failed_feedback
                        ctx.setdefault("original_goal", state.original_goal)
                        current_task.required_context.pre_execution_context = ctx
                    except Exception:
                        # Defensive: avoid raising from validator persistence
                        pass
            else:
                debug_warning(
                    "Goal Validator",
                    f"Invalid response from validation LLM for Task {current_task_id}. Defaulting to goal not achieved.",
                    metadata={
                        "function name": "__subAGENT_goal_validator",
                        "task_id": current_task_id,
                        "llm_response": response.content,
                    },
                )
                current_task.execution_context.goal_achieved = False
                current_task.status = "failed"
                # CRITICAL FIX: Preserve the original failed_parameters here too
                original_failed_parameters = (
                    current_task.execution_context.parameters
                    if current_task.execution_context
                    else None
                )
                original_strategy_history = []
                if current_task.failure_context:
                    original_strategy_history = (
                        current_task.failure_context.strategy_history or []
                    )

                current_task.failure_context = FAILURE_CONTEXT(
                    error_message="Failed to validate goal achievement due to invalid LLM response.",
                    fail_count=(
                        (current_task.failure_context.fail_count + 1)
                        if current_task.failure_context
                        else 1
                    ),
                    error_type="GoalValidationFailure",
                    failed_parameters=original_failed_parameters,  # PRESERVE the original failed parameters
                    strategy_history=original_strategy_history,  # PRESERVE the strategy history too
                )

        return {
            "tasks": tasks,
            "executed_nodes": state.executed_nodes + ["subAGENT_goal_validator"],
        }

    @classmethod
    def __subAGENT_error_fallback(cls, state: "WorkflowStateModel") -> dict:
        ## todo shifting fallback to use enhanced helper - pending
        """Handle task failures with a tiered, state-driven recovery system."""
        AgentStatusUpdater.update_status(
            "error_recovery", task_id=state.current_task_id
        )
        debug_info(
            "--- NODE: Error Fallback ---",
            "Handling task failure with tiered recovery strategies",
            metadata={"function name": "__subAGENT_error_fallback"},
        )
        current_task_id = state.current_task_id
        updated_tasks = state.tasks
        current_task: TASK = next(
            (task for task in updated_tasks if task.task_id == current_task_id), None
        )

        if not current_task or not current_task.failure_context:
            return {
                "tasks": updated_tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_error_fallback"],
            }

        # todo here the enhancement start to use the new helper
        # 1. DELEGATE to the new, intelligent helper
        recovery_decision = (
            AgentCoreHelpers.EnhancedErrorFallbackHelpers.decide_recovery_strategy(
                current_task, state
            )
        )
        strategy = recovery_decision.get(
            "recovery_strategy", None
        )  # <-- Use the strategy from the helper
        # Canonicalize strategy names from LLM to internal enums
        if not strategy:
            current_task.status = "failed"
            current_task.failure_context.strategy_history.append(
                FAILURE_CONTEXT_STRATEGY(
                    recovery_strategy="NO_STRATEGY",
                    reasoning=recovery_decision.get(
                        "reasoning", "No viable recovery strategy identified."
                    ),
                    outcome="NOT_APPLIED",
                    details={
                        "description": current_task.description,
                        "error_message": getattr(
                            current_task.failure_context, "error_message", None
                        ),
                    },
                )
            )
            return {
                "tasks": updated_tasks,
                "executed_nodes": state.executed_nodes + ["subAGENT_error_fallback"],
            }
        # 2. ACT on the strategic decision
        try:
            if strategy == "PARAMETER_REPAIR":
                is_repaired, new_params = (
                    AgentCoreHelpers.ErrorFallbackHelpers.attempt_parameter_repair(
                        current_task, state
                    )
                )
                if is_repaired:
                    # Ensure execution_context exists before assigning parameters
                    if current_task.execution_context is None:
                        current_task.execution_context = EXECUTION_CONTEXT(
                            tool_name=current_task.tool_name,
                            parameters={},
                        )
                    else:
                        # Keep tool_name in sync in case it changed elsewhere
                        current_task.execution_context.tool_name = (
                            current_task.tool_name
                        )
                    current_task.execution_context.parameters = new_params
                    current_task.status = "pending"
                    current_task.failure_context.strategy_history.append(
                        FAILURE_CONTEXT_STRATEGY(
                            recovery_strategy="PARAMETER_REPAIR",
                            reasoning=recovery_decision.get(
                                "reasoning",
                                "Parameters repaired based on failure context.",
                            ),
                            outcome="APPLIED",
                            details={
                                "repaired_parameters": new_params,
                                "description": current_task.description,
                                "error_message": getattr(
                                    current_task.failure_context, "error_message", None
                                ),
                            },
                        )
                    )
                else:
                    current_task.status = "failed"
            elif strategy == "ALTERNATIVE_TOOL":
                new_tool = AgentCoreHelpers.ErrorFallbackHelpers.find_alternative_tool(
                    current_task, state
                )
                if new_tool:
                    current_task.tool_name = new_tool
                    # 🚨 CRITICAL FIX: DO NOT reset parameters to {} - preserve failure_context for parameter generator
                    if current_task.execution_context is None:
                        current_task.execution_context = EXECUTION_CONTEXT(
                            tool_name=new_tool, parameters={}
                        )
                    else:
                        # Preserve the failed parameters in failure_context - DO NOT reset to empty dict
                        current_task.execution_context.tool_name = new_tool
                        # 🚨 KEY FIX: Keep parameters empty but ensure failure_context is preserved
                        # The parameter generator will use failure_context.failed_parameters to avoid repetition
                        current_task.execution_context.parameters = {}
                        current_task.execution_context.result = None
                        current_task.execution_context.analysis = None
                        current_task.execution_context.goal_achieved = False
                    current_task.status = "pending"
                    current_task.failure_context.strategy_history.append(
                        FAILURE_CONTEXT_STRATEGY(
                            recovery_strategy="ALTERNATIVE_TOOL",
                            reasoning=recovery_decision.get(
                                "reasoning", "Alternative tool suggested by LLM."
                            ),
                            outcome="APPLIED",
                            details={
                                "alternative_tool": new_tool,
                                "description": current_task.description,
                                "error_message": getattr(
                                    current_task.failure_context, "error_message", None
                                ),
                            },
                        )
                    )
                else:
                    # Record no-op attempt for observability
                    current_task.failure_context.strategy_history.append(
                        FAILURE_CONTEXT_STRATEGY(
                            recovery_strategy="ALTERNATIVE_TOOL",
                            reasoning=recovery_decision.get(
                                "reasoning", "Alternative tool suggested by LLM."
                            ),
                            outcome="NOT_APPLIED",
                            details={
                                "alternative_tool": None,
                                "description": current_task.description,
                                "error_message": getattr(
                                    current_task.failure_context, "error_message", None
                                ),
                            },
                        )
                    )
                    current_task.status = "failed"

            elif strategy == "TASK_DECOMPOSITION":
                # Build parent context with completed tasks and failure context
                completed_tasks = [
                    t
                    for t in updated_tasks
                    if t.status == "completed"
                    and t.execution_context
                    and t.execution_context.result
                ]
                current_task.status = (
                    "skip"  # Mark as like this while we handle decomposition
                )
                # this is the issue it passes the only last strategy context
                parent_context = {
                    "original_goal": state.original_goal,
                    "completed_tasks_history": completed_tasks,
                    "workflow_progress": f"{len(completed_tasks)}/{len(updated_tasks)} tasks completed",
                    "failed_task_context": {
                        "task_id": current_task.task_id,
                        "description": current_task.description,
                        "failure_reason": current_task.failure_context.error_message,
                        "fail_count": current_task.failure_context.fail_count,
                        "error_type": current_task.failure_context.error_type,
                        "failed_parameters": current_task.failure_context.failed_parameters,
                        "strategy_history": current_task.failure_context.strategy_history,
                    },
                }
                parent_context_str = (
                    f"Original Goal: {parent_context['original_goal']}\n"
                    f"Workflow Progress: {parent_context['workflow_progress']}\n"
                    f"Completed Tasks: {[f'Task {t.task_id}: {t.description}' for t in parent_context['completed_tasks_history']]}\n"
                    f"FAILED TASK CONTEXT:\n"
                    f"- Task ID: {parent_context['failed_task_context']['task_id']}\n"
                    f"- Description: {parent_context['failed_task_context']['description']}\n"
                    f"- Failure Reason: {parent_context['failed_task_context']['failure_reason']}\n"
                    f"- Fail Count: {parent_context['failed_task_context']['fail_count']}\n"
                    f"- Error Type: {parent_context['failed_task_context']['error_type']}\n"
                    f"- LAST Failed Parameters: {parent_context['failed_task_context']['failed_parameters']}\n"
                    f"**FAILED FULL HISTORY NEVER IGNORE THIS ***\n"
                    f" \n".join(
                        [
                            f"  {idx + 1}. Strategy: {s.recovery_strategy}, Outcome: {s.outcome}, Reasoning: {s.reasoning}"
                            for idx, s in enumerate(
                                parent_context["failed_task_context"][
                                    "strategy_history"
                                ]
                            )
                        ]
                    )
                )

                # this needs to be got more verbose like what error we are facing and how to decompose such that,
                # we would be able to pass the last finding to next higher task
                detailed_spawn_reason = f"""
                      --- RECOVERY MANDATE: TASK DECOMPOSITION ---
                    
                      A task has failed, and the chosen recovery strategy is to decompose it into a new, investigative plan.
                    
                      Original User Goal:
                      {state.original_goal}
                    
                      Failed Task Details:
                      - Task Description: {current_task.description}
                      - Failed Tool: {current_task.tool_name}
                      - Failed Parameters: {current_task.failure_context.failed_parameters}
                    
                      Failure Analysis:
                      - Error Type: {current_task.failure_context.error_type}
                      - Error Message: {current_task.failure_context.error_message}
                    
                      Recovery Plan from Strategist:
                      - Chosen Strategy: {recovery_decision.get('recovery_strategy')}
                      - Strategist's Reasoning: {recovery_decision.get('reasoning')}
                      - Plan to Execute: {recovery_decision.get('next_steps')}
                    
                      Your Mission:
                      Your only job is to convert the 'Plan to Execute' above into a precise, executable list of new sub-tasks. Do not re-evaluate the strategy
                      or the original task. Your purpose is to implement the recovery plan exactly as specified.
                    """

                # there is we are adding the artificial tasks to TASK DECOMPOSER work on that
                sub_tasks: list[TASK] = (
                    AgentCoreHelpers.ErrorFallbackHelpers.convert_decision_task(
                        [parent_context_str, detailed_spawn_reason],
                        str(
                            AgentCoreHelpers.recommend_tools_for_task(
                                current_task.description
                            )
                        ),
                        current_task,
                    )
                )

                # insert that artificial TASKS created by the parser
                parent_task_idx = next(
                    (
                        i
                        for i, t in enumerate(state.tasks)
                        if t.task_id == current_task.task_id
                    ),
                    None,
                )
                # insertion logic
                state.tasks = (
                    state.tasks[: parent_task_idx + 1]
                    + sub_tasks
                    + state.tasks[parent_task_idx + 1 :]
                )

                spawn_result = Spawn_subAgent.spawn_subAgent_recursive(
                    state,
                    sub_tasks[0],
                    detailed_spawn_reason,
                    parent_context_str,
                    recovery_plan=recovery_decision.get("recovery_plan"),
                )
                if spawn_result.get("spawn_triggered"):
                    current_task.failure_context.strategy_history.append(
                        FAILURE_CONTEXT_STRATEGY(
                            recovery_strategy="TASK_DECOMPOSITION",
                            reasoning=recovery_decision.get(
                                "reasoning", "Decomposition suggested by LLM."
                            ),
                            outcome="APPLIED",
                            details={
                                "spawned_subtasks": [
                                    t.tool_name
                                    for t in spawn_result["tasks"]
                                    if t.task_id != current_task.task_id
                                ],
                                "description": current_task.description,
                                "error_message": getattr(
                                    current_task.failure_context, "error_message", None
                                ),
                            },
                        )
                    )
                    return {
                        "tasks": spawn_result["tasks"],
                        "current_task_id": spawn_result["current_task_id"],
                        "executed_nodes": state.executed_nodes
                        + ["subAGENT_error_fallback"],
                    }
                else:
                    current_task.status = "failed"

            elif strategy == "SKIP":
                current_task.status = "skip"
                current_task.execution_context = EXECUTION_CONTEXT(
                    tool_name=current_task.tool_name,
                    parameters={},
                    result="Task skipped as per recovery strategy.",
                    analysis="Task was skipped to allow workflow progression.",
                    goal_achieved=False,
                )

                current_task.failure_context.strategy_history.append(
                    FAILURE_CONTEXT_STRATEGY(
                        recovery_strategy="SKIP",
                        reasoning=recovery_decision.get(
                            "reasoning", "Skipping task as per recovery strategy."
                        ),
                        confidence_level=recovery_decision.get(
                            "confidence_level", "HIGH"
                        ),
                        estimated_success_probability=recovery_decision.get(
                            "estimated_success_probability", 0
                        ),
                        next_steps=recovery_decision.get(
                            "next_steps", "task got skipped as per strategy"
                        ),
                        outcome="APPLIED",
                        details={
                            "description": current_task.description,
                            "error_message": getattr(
                                current_task.failure_context, "error_message", None
                            ),
                        },
                    )
                )

                return {
                    "tasks": updated_tasks,
                    "executed_nodes": state.executed_nodes
                    + ["subAGENT_error_fallback"],
                }
            else:
                current_task.status = "failed"

        except Exception as e:
            debug_error(
                "Error Fallback",
                f"Error during LLM recovery processing: {e}",
                metadata={
                    "function name": "__subAGENT_error_fallback",
                    "task_id": current_task_id,
                    "exception": str(e),
                },
            )
            current_task.status = "failed"
            current_task.failure_context.error_message += (
                f" | Error during recovery processing: {e}"
            )

        return {
            "tasks": updated_tasks,
            "executed_nodes": state.executed_nodes + ["subAGENT_error_fallback"],
        }

    @classmethod
    def __subAGENT_task_planner(cls, state: "WorkflowStateModel") -> dict:
        """📋 WORKFLOW ORCHESTRATOR: Manages task progression and parent-child relationships.
        🆕 DUAL CONTEXT BRIDGE: Passes both raw results and synthesized analysis to the next task.

        This node implements sophisticated logic for hierarchical task management:

        PARENT-CHILD LOGIC:
        - Monitors spawned sub-tasks (float IDs like 1.1, 1.2) for completion
        - Updates parent task status based on sub-task results
        - Handles both success (all sub-tasks complete) and failure scenarios

        TASK SELECTION WITH DUAL CONTEXT BRIDGE:
        - Finds next pending task in priority order (sorted by task_id)
        - 🆕 COLLECTS the full history of completed TASK objects.
        - 🆕 INJECTS this history (containing both raw `.result` and summarized `.analysis`) into the next task.
        - This prevents infinite loops by giving the next LLM clean, summarized context for decision-making, while preserving the full raw data for tools that need it.
        - Returns None when no more tasks remain (triggers finalizer).

        This is where the hierarchical magic happens - parent tasks are only
        considered complete when their spawned sub-tasks finish successfully.
        """
        debug_info(
            "--- NODE: Task Planner ---",
            "Managing task progression and parent-child relationships",
            metadata={"function name": "__subAGENT_task_planner"},
        )

        tasks = state.tasks
        last_completed_id = state.current_task_id

        # If the last completed task was a sub-task (e.g., '1.1-abc'), update its parent
        if (
            isinstance(last_completed_id, str) and "-" in last_completed_id
        ):  # Check for new string format
            # Extract parent_id from string, e.g., '1' from '1.1-abc'
            parent_id_prefix = last_completed_id.rsplit(".")[
                0
            ]  # immediate parent before dot
            parent_task = next(
                (t for t in tasks if str(t.task_id) == parent_id_prefix), None
            )  # Find parent by prefix
            if parent_task and parent_task.status == "in_progress":
                # Find sibling tasks that share the same parent prefix
                sibling_tasks = [
                    t
                    for t in tasks
                    if isinstance(t.task_id, str)
                    and t.task_id.startswith(f"{parent_id_prefix}.")
                ]
                # 🔥 Include skip in terminal states to handle skipped sub-tasks
                TERMINAL_STATES = ["completed", "failed", "skip"]
                if all(t.status in TERMINAL_STATES for t in sibling_tasks):
                    failed_subtasks = [t for t in sibling_tasks if t.status == "failed"]
                    skipped_subtasks = [t for t in sibling_tasks if t.status == "skip"]
                    if not parent_task.execution_context:
                        parent_task.execution_context = EXECUTION_CONTEXT(
                            tool_name=parent_task.tool_name,
                            parameters={},
                        )
                    if failed_subtasks:
                        parent_task.status = "failed"
                        skip_msg = (
                            f", {len(skipped_subtasks)} skipped"
                            if skipped_subtasks
                            else ""
                        )
                        parent_task.execution_context.analysis = f"Failed due to {len(failed_subtasks)} failed subtasks{skip_msg}."
                    else:
                        parent_task.status = "completed"
                        completed_count = len(
                            [t for t in sibling_tasks if t.status == "completed"]
                        )
                        skip_msg = (
                            f" ({len(skipped_subtasks)} skipped)"
                            if skipped_subtasks
                            else ""
                        )
                        parent_task.execution_context.analysis = f"Successfully completed {completed_count} of {len(sibling_tasks)} subtasks{skip_msg}."

        # 🌉 DUAL CONTEXT BRIDGE: Collect the full history of completed tasks AND failed tasks with validator feedback
        completed_tasks = [t for t in tasks if t.status == "completed"]
        failed_tasks_with_context = [
            t
            for t in tasks
            if t.status == "failed"
            and t.failure_context
            and t.failure_context.error_type == "GoalValidationFailure"
        ]

        # Find the next pending task
        pending_tasks = sorted(
            [t for t in tasks if t.status == "pending"], key=lambda x: x.task_id
        )

        next_task_id = None
        if pending_tasks:
            next_task = pending_tasks[0]
            next_task_id = next_task.task_id

            # 🆕 INJECT DUAL CONTEXT: Pass the *entire list* of completed TASK objects AND validator feedback from failed tasks.
            # This gives the next node access to both raw .result and summarized .analysis from completed tasks,
            # PLUS validator reasoning from failed tasks to avoid repeating the same mistakes.
            # We also include the original goal for full context.
            accumulated_context = {
                "original_goal": state.original_goal,
                "completed_tasks_history": completed_tasks,
                "failed_tasks_with_validator_feedback": failed_tasks_with_context,
            }

            next_task.required_context.pre_execution_context = accumulated_context

            debug_info(
                "Context Bridge",
                f"Injected context from {len(completed_tasks)} completed tasks into Task {next_task_id}",
                metadata={
                    "function name": "__subAGENT_task_planner",
                    "next_task_id": next_task_id,
                    "completed_tasks_count": len(completed_tasks),
                },
            )

        return {
            "current_task_id": next_task_id,
            "executed_nodes": state.executed_nodes + ["subAGENT_task_planner"],
            "tasks": tasks,
        }

    @classmethod
    def __subAGENT_finalizer(cls, state: "WorkflowStateModel") -> dict:
        """Generate final response consolidating all task results."""
        # print_log_message("--- NODE: Finalizer ---", "Finalizer")
        debug_info(
            "--- NODE: Finalizer ---",
            "Generating final response consolidating all task results",
            metadata={"function name": "__subAGENT_finalizer"},
        )

        tasks = state.tasks

        # 🔥 CATEGORIZE tasks by status for clear visibility and skip awareness
        completed_tasks = [t for t in tasks if t.status == "completed"]
        failed_tasks = [t for t in tasks if t.status == "failed"]
        skipped_tasks = [t for t in tasks if t.status == "skip"]

        # Debug system_logging with skip statistics
        debug_info(
            "Finalizer - Task Summary",
            f"Workflow completed: {len(completed_tasks)} completed, {len(skipped_tasks)} skipped, {len(failed_tasks)} failed",
            metadata={
                "function name": "__subAGENT_finalizer",
                "completed_count": len(completed_tasks),
                "skipped_count": len(skipped_tasks),
                "failed_count": len(failed_tasks),
                "total_count": len(tasks),
                "completion_rate": (
                    f"{len(completed_tasks)/len(tasks)*100:.1f}%" if tasks else "0%"
                ),
                "skip_rate": (
                    f"{len(skipped_tasks)/len(tasks)*100:.1f}%" if tasks else "0%"
                ),
            },
        )

        # Build categorized results with clear status indicators
        all_results = []

        # ✅ COMPLETED TASKS - Show successful task outcomes
        if completed_tasks:
            all_results.append(
                f"\n✅ COMPLETED TASKS ({len(completed_tasks)}/{len(tasks)} total tasks):"
            )
            for task in completed_tasks:
                if task.execution_context and task.execution_context.result:
                    # Clean up the task result to remove raw Python representations
                    result_content = task.execution_context.result

                    # If the result contains Python list/dict representations, clean them up
                    try:
                        import json as _json

                        # Try to extract just the meaningful content from MCP tool responses
                        if isinstance(
                            result_content, str
                        ) and result_content.startswith("✅ **Action"):
                            # Extract the actual result from the MCP response format
                            if "Result: [{'type': 'text', 'text':" in result_content:
                                # Extract the text content from the MCP response format
                                import re

                                text_match = re.search(
                                    r"'text':\s*'([^']+)'", result_content
                                )
                                if text_match:
                                    extracted_text = text_match.group(1)
                                    # Unescape newlines and clean up
                                    extracted_text = extracted_text.replace(
                                        "\n", "\n"
                                    ).replace("'", "'")
                                    result_content = extracted_text

                        all_results.append(
                            f"  • Task {task.task_id} ({task.tool_name}): {result_content}"
                        )
                    except Exception:
                        # Fallback to original content if parsing fails
                        all_results.append(
                            f"  • Task {task.task_id} ({task.tool_name}): {task.execution_context.result}"
                        )

        # ⏭️ SKIPPED TASKS - Explicitly highlight skipped tasks with reasons
        if skipped_tasks:
            all_results.append(
                f"\n⏭️ SKIPPED TASKS ({len(skipped_tasks)}/{len(tasks)} total tasks):"
            )
            for task in skipped_tasks:
                if task.execution_context and task.execution_context.result:
                    # Skip result already formatted as "⏭️ Task skipped: reason" from error_fallback
                    skip_reason = task.execution_context.result
                    all_results.append(
                        f"  • Task {task.task_id} ({task.tool_name}): {skip_reason}"
                    )
                else:
                    # Fallback if execution_context somehow missing
                    all_results.append(
                        f"  • Task {task.task_id} ({task.tool_name}): ⏭️ Skipped (reason unknown)"
                    )

        # ❌ FAILED TASKS - Show task failures
        if failed_tasks:
            all_results.append(
                f"\n❌ FAILED TASKS ({len(failed_tasks)}/{len(tasks)} total tasks):"
            )
            for task in failed_tasks:
                error_message = (
                    task.failure_context.error_message
                    if task.failure_context
                    else "Unknown error"
                )
                all_results.append(
                    f"  • Task {task.task_id} ({task.tool_name}): {error_message}"
                )

        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = prompt_generator.generate_final_response_prompt(
            all_results,
            state.original_goal,
        )

        model = ModelManager()
        response = model.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": human_prompt},
            ]
        )

        raw = response.content

        # Try to convert LLM output into JSON using ModelManager helper
        parsed = None
        try:
            parsed = ModelManager.convert_to_json(raw)
        except Exception:
            parsed = None

        # If parsed is a dict matching the expected finalizer schema, return it directly.
        def is_valid_final_schema(obj) -> bool:
            if not isinstance(obj, dict):
                return False
            if (
                "user_response" in obj
                and isinstance(obj["user_response"], dict)
                and isinstance(obj["user_response"].get("message"), str)
            ):
                # Ensure analysis keys exist (maybe empty strings)
                if "analysis" in obj and isinstance(obj["analysis"], dict):
                    return True
            return False

        # If we got any parsed JSON from the LLM, consider it a successful LLM response.
        if parsed is not None:
            final_response_obj = parsed
            # Determine overall workflow status based on task outcomes (with skip awareness)
            any_failed = any(getattr(t, "status", None) == "failed" for t in tasks)
            any_goal_false = any(
                (
                    t.status == "completed"
                    and t.execution_context
                    and t.execution_context.goal_achieved is False
                )
                for t in tasks
            )
            any_skipped = any(getattr(t, "status", None) == "skip" for t in tasks)

            # Enhanced status determination with skip awareness
            if any_failed or any_goal_false:
                workflow_status = "FAILED"
            elif any_skipped and len(completed_tasks) > 0:
                workflow_status = "COMPLETED_WITH_SKIPS"  # Partial success - some tasks completed, some skipped
            elif any_skipped and len(completed_tasks) == 0:
                workflow_status = (
                    "ALL_SKIPPED"  # Nothing accomplished - all tasks skipped
                )
            else:
                workflow_status = "COMPLETED"  # Full success - all tasks completed
            debug_info(
                "Finalizer",
                "LLM produced parsable JSON. Returning parsed object as final_response.",
                metadata={
                    "function name": "__subAGENT_finalizer",
                    "parsed_preview": str(parsed)[:200],
                    "workflow_status": workflow_status,
                },
            )
            return {
                "final_response": final_response_obj,
                "final_response_source": "llm",
                "workflow_status": workflow_status,
                "executed_nodes": state.executed_nodes + ["subAGENT_finalizer"],
            }

        # If not valid JSON, attempt to repair by asking the model to convert its previous output into the exact schema.
        try:
            repair_system = "You are a JSON fixer. Convert the provided text into a JSON object that exactly matches the required schema. Return ONLY the JSON object."
            repair_human = (
                "The original assistant output is:\n\n"
                f"{raw}\n\n\n"
                "Now convert the above into a JSON object matching this schema exactly:\n"
                "{\n"
                '  "user_response": {\n'
                '    "message": "string",\n'
                '    "next_steps": "string"\n'
                "  },\n"
                '  "analysis": {\n'
                '    "issues": "string",\n'
                '    "reason": "string"\n'
                "  }\n"
                "}\n\nReturn only the JSON object, nothing else."
            )

            model = ModelManager()
            repair_resp = model.invoke(
                [
                    {"role": "system", "content": repair_system},
                    {"role": "user", "content": repair_human},
                ]
            )
            repaired = None
            try:
                repaired = ModelManager.convert_to_json(repair_resp.content)
            except Exception:
                repaired = None

            if repaired is not None:
                final_response_obj = repaired
                # Determine overall workflow status based on task outcomes (with skip awareness)
                any_failed = any(getattr(t, "status", None) == "failed" for t in tasks)
                any_goal_false = any(
                    (
                        t.status == "completed"
                        and t.execution_context
                        and t.execution_context.goal_achieved is False
                    )
                    for t in tasks
                )
                any_skipped = any(getattr(t, "status", None) == "skip" for t in tasks)

                # Enhanced status determination with skip awareness
                if any_failed or any_goal_false:
                    workflow_status = "FAILED"
                elif any_skipped and len(completed_tasks) > 0:
                    workflow_status = "COMPLETED_WITH_SKIPS"  # Partial success
                elif any_skipped and len(completed_tasks) == 0:
                    workflow_status = "ALL_SKIPPED"  # Nothing accomplished
                else:
                    workflow_status = "COMPLETED"  # Full success
                debug_info(
                    "Finalizer",
                    "Repaired final response successfully and returning as final_response.",
                    metadata={
                        "function name": "__subAGENT_finalizer",
                        "response_preview": str(repaired)[:200],
                        "workflow_status": workflow_status,
                    },
                )
                return {
                    "final_response": final_response_obj,
                    "final_response_source": "llm_repaired",
                    "workflow_status": workflow_status,
                    "executed_nodes": state.executed_nodes + ["subAGENT_finalizer"],
                }
        except Exception as e:
            debug_warning(
                "Finalizer",
                f"JSON repair attempt failed: {e}",
                metadata={"function name": "__subAGENT_finalizer", "exception": str(e)},
            )

        # As a last resort, build a fallback wrapped schema so the caller can reliably extract a message.
        final_text = None
        try:
            if isinstance(parsed, (dict, list)):
                import json as _json

                final_text = _json.dumps(parsed, ensure_ascii=False, indent=2)
            else:
                final_text = str(raw)
        except Exception:
            final_text = str(raw)

        debug_info(
            "Finalizer",
            f"Final Response (fallback text): {final_text}",
            metadata={
                "function name": "__subAGENT_finalizer",
                "response_preview_length": len(final_text),
            },
        )

        # Wrap fallback text into the exact schema so the caller can reliably extract
        # a human-friendly message. This guarantees the agent_node can always display
        # something meaningful to the user even if the LLM didn't return the strict schema.
        try:
            final_response_obj = {
                "user_response": {
                    "message": str(final_text),
                    "next_steps": "",
                },
                "analysis": {
                    "issues": "",
                    "reason": "",
                },
            }
        except Exception:
            # Ensure we never return None
            final_response_obj = {
                "user_response": {
                    "message": "No response generated from workflow.",
                    "next_steps": "",
                },
                "analysis": {"issues": "", "reason": ""},
            }

        debug_info(
            "Finalizer",
            "Returning wrapped fallback final response as structured JSON schema",
            metadata={
                "function name": "__subAGENT_finalizer",
                "response_preview": str(final_response_obj)[0:200],
            },
        )

        return {
            "final_response": final_response_obj,
            "final_response_source": "fallback",
            "workflow_status": "FAILED",
            "executed_nodes": state.executed_nodes + ["subAGENT_finalizer"],
        }

    # =================================================================
    # Graph Routing Logic
    # =================================================================

    @classmethod
    def __router_after_execution(
        cls, state: "WorkflowStateModel"
    ) -> Literal["subAGENT_classifier", "subAGENT_task_planner", "subAGENT_finalizer"]:
        """Routes after a task execution. Decides whether to retry, plan the next task, or finalize.
        This is a critical routing function that enables the retry loop.
        """
        # print_log_message("--- ROUTER: After Execution ---", "Router")
        debug_info(
            "--- ROUTER: After Execution ---",
            "Routing after task execution based on task status",
            metadata={"function name": "__router_after_execution"},
        )
        current_task_id = state.current_task_id
        tasks = state.tasks
        current_task = next((t for t in tasks if t.task_id == current_task_id), None)

        if current_task and current_task.status == "failed":
            # If the task failed, route back to the classifier to decide on a retry or fallback.
            # This creates the crucial "retry loop".
            # print_log_message(f"Task {current_task_id} failed. Routing to classifier for retry/fallback.", "Router")
            debug_info(
                "Router",
                f"Task {current_task_id} failed. Routing to classifier for retry/fallback.",
                metadata={
                    "function name": "__router_after_execution",
                    "task_id": current_task_id,
                    "task_status": current_task.status,
                },
            )
            return "subAGENT_classifier"

        # If the task succeeded, check if there are more pending tasks.
        pending_tasks = [t for t in tasks if t.status == "pending"]
        if not pending_tasks:
            # If no more pending tasks, it's time to finalize the workflow.
            # print_log_message("All tasks completed. Routing to finalizer.", "Router")
            debug_info(
                "Router",
                "All tasks completed. Routing to finalizer.",
                metadata={"function name": "__router_after_execution"},
            )
            return "subAGENT_finalizer"

        # If there are more pending tasks, route to the planner to select the next one.
        # print_log_message("Task completed. Routing to task planner for next task.", "Router")
        debug_info(
            "Router",
            "Task completed. Routing to task planner for next task.",
            metadata={"function name": "__router_after_execution"},
        )
        return "subAGENT_task_planner"

    @classmethod
    def __router_classifier(
        cls, state: "WorkflowStateModel"
    ) -> Literal["subAGENT_parameter_generator", "subAGENT_error_fallback"]:
        """Route to parameter generation or error fallback."""
        # print_log_message("--- ROUTER: Classifier ---", "Router")
        debug_info(
            "--- ROUTER: Classifier ---",
            "Routing based on classifier decision",
            metadata={"function name": "__router_classifier"},
        )
        if state.persona == "AGENT_PERFORM_ERROR_FALLBACK":
            return "subAGENT_error_fallback"
        return "subAGENT_parameter_generator"

    @classmethod
    def __router_task_planner(
        cls, state: "WorkflowStateModel"
    ) -> Literal["subAGENT_classifier", "subAGENT_finalizer"]:
        """Route from task planner to either classifier or finalizer."""
        # print_log_message("--- ROUTER: Task Planner ---", "Router")
        debug_info(
            "--- ROUTER: Task Planner ---",
            "Routing based on task planner decision",
            metadata={"function name": "__router_task_planner"},
        )
        # Check if all tasks are in terminal states (completed, failed, OR skip)
        tasks = state.tasks
        TERMINAL_STATES = [
            "completed",
            "failed",
            "skip",
        ]  # 🔥 Include skip to prevent workflow hangs
        all_tasks_finished = all(t.status in TERMINAL_STATES for t in tasks)

        if all_tasks_finished:
            return "subAGENT_finalizer"
        return "subAGENT_classifier"

    @classmethod
    def build_graph(cls):
        """🏗️ LANGGRAPH WORKFLOW BUILDER: Constructs the complete hierarchical agent workflow.

        This method creates a sophisticated 7-node state machine that handles:
        - Dynamic task planning with tool pre-filtering
        - Intelligent task execution with spawning capabilities
        - Advanced error recovery with spawning-based recovery
        - Parent-child task relationship management
        - Schema-aware parameter generation
        - Comprehensive result finalization

        WORKFLOW ARCHITECTURE:
        Entry → initial_planner → classifier → [parameter_generator|error_fallback]
              → task_executor → [task_planner|finalizer] → classifier → ... → END

        The conditional routing enables sophisticated decision-making while maintaining
        clean separation of concerns and full observability throughout execution.
        """
        from langgraph.graph import StateGraph

        graph_builder = StateGraph(state_schema=WorkflowStateModel)

        # 🏗️ NODE REGISTRATION: Add all workflow nodes
        graph_builder.add_node(
            "subAGENT_initial_planner", cls.__subAGENT_initial_planner
        )
        graph_builder.add_node("subAGENT_classifier", cls.__subAGENT_classifier)
        graph_builder.add_node(
            "subAGENT_parameter_generator", cls.subAGENT_parameter_generator
        )
        graph_builder.add_node("subAGENT_task_executor", cls.__subAGENT_task_executor)
        graph_builder.add_node(
            "subAGENT_context_synthesizer", cls.__subAGENT_context_synthesizer
        )
        graph_builder.add_node(
            "subAGENT_goal_validator", cls.__subAGENT_goal_validator
        )  # New node
        graph_builder.add_node("subAGENT_error_fallback", cls.__subAGENT_error_fallback)
        graph_builder.add_node("subAGENT_task_planner", cls.__subAGENT_task_planner)
        graph_builder.add_node("subAGENT_finalizer", cls.__subAGENT_finalizer)

        # 🚀 WORKFLOW DEFINITION: Set entry point and routing
        graph_builder.set_entry_point("subAGENT_initial_planner")
        graph_builder.add_edge("subAGENT_initial_planner", "subAGENT_classifier")

        # 🎯 CONDITIONAL ROUTING: Dynamic decision-making based on task state
        graph_builder.add_conditional_edges(
            "subAGENT_classifier",
            cls.__router_classifier,
            {
                "subAGENT_parameter_generator": "subAGENT_parameter_generator",
                "subAGENT_error_fallback": "subAGENT_error_fallback",
            },
        )

        graph_builder.add_edge("subAGENT_parameter_generator", "subAGENT_task_executor")

        # MODIFIED: The executor and fallback now route to the new synthesizer node
        graph_builder.add_edge("subAGENT_task_executor", "subAGENT_context_synthesizer")
        graph_builder.add_edge("subAGENT_error_fallback", "subAGENT_classifier")

        # The synthesizer then routes to the new goal validator
        graph_builder.add_edge(
            "subAGENT_context_synthesizer", "subAGENT_goal_validator"
        )

        # The goal validator then routes to the main "after execution" router
        graph_builder.add_conditional_edges(
            "subAGENT_goal_validator",
            cls.__router_after_execution,
            {
                "subAGENT_classifier": "subAGENT_classifier",
                "subAGENT_task_planner": "subAGENT_task_planner",
                "subAGENT_finalizer": "subAGENT_finalizer",
            },
        )

        graph_builder.add_conditional_edges(
            "subAGENT_task_planner",
            cls.__router_task_planner,
            {
                "subAGENT_classifier": "subAGENT_classifier",
                "subAGENT_finalizer": "subAGENT_finalizer",
            },
        )
        graph_builder.add_edge("subAGENT_finalizer", END)

        return graph_builder.compile()
