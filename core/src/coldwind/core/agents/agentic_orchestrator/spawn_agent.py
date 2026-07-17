from coldwind.core.agents.agentic_orchestrator.agent_core_helpers import AgentCoreHelpers
import uuid
from coldwind.core.agents.agentic_orchestrator.pydantic_models import TASK, REQUIRED_CONTEXT, EXECUTION_CONTEXT, FAILURE_CONTEXT, subAgent_CONTEXT
from coldwind.core.agents.agentic_orchestrator.hierarchical_agent_prompts import HierarchicalAgentPrompt
from coldwind.core.utils.model_manager import ModelManager
from coldwind.desktop.ui.diagnostics.debug_helpers import debug_info, debug_warning, debug_error
from coldwind.core.utils.timestamp_util import get_formatted_timestamp


class Spawn_subAgent:
    """Handles the logic for dynamically decomposing a complex task into a series of smaller, atomic sub-tasks.
    This class embodies the "Progressive Refinement" pattern, allowing the agent to handle abstract goals.
    """

    @classmethod
    def analyze_spawn_requirement(
        cls, parent_task: TASK, reason: str, state: "WorkflowStateModel"
    ) -> dict:
        """Uses an LLM to analyze if a task is too complex and requires decomposition."""
        debug_info(
            "--- SPAWNER: Analyzing Task for sub-agent spawning ---",
            f"Task ID: {parent_task.task_id}, Reason: {reason}",
            metadata={
                "function name": "analyze_spawn_requirement",
                "task_id": parent_task.task_id,
                "reason": reason,
            },
        )

        prompt_generator = HierarchicalAgentPrompt()
        tool_schema = AgentCoreHelpers.get_tool_schema(parent_task.tool_name)

        # 🚨 FIX: Pass the `reason` (which contains the Recovery Mandate) to the prompt generator.
        system_prompt, human_prompt = (
            prompt_generator.generate_tool_schema_complexity_prompt(
                parent_task.description,
                parent_task.tool_name,
                tool_schema,
                parent_task.depth,
                parent_context=reason,
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
            debug_warning(
                "SubAgent Spawner",
                "LLM failed to provide a valid spawn analysis. Defaulting to NO spawn.",
                metadata={
                    "function name": "analyze_spawn_requirement",
                    "task_id": parent_task.task_id,
                    "reason": reason,
                },
            )
            return {
                "should_spawn": False,
                "reasoning": "Fallback due to invalid LLM response.",
            }

        debug_info(
            "SubAgent Spawner",
            f"Spawn Analysis Result: {analysis_result.get('reasoning')}",
            metadata={
                "function name": "analyze_spawn_requirement",
                "task_id": parent_task.task_id,
                "reason": reason,
                "should_spawn": analysis_result.get("requires_decomposition"),
                "reasoning": analysis_result.get("reasoning"),
            },
        )
        analysis_result["should_spawn"] = analysis_result.get(
            "requires_decomposition", False
        )
        return analysis_result

    @classmethod
    def decompose_task_for_subAgent(
        cls,
        parent_task: TASK,
        state: "WorkflowStateModel",
        parent_context: str | None,
        recovery_plan: str | None = None,
    ) -> list[TASK]:
        """Uses LLM to decompose a complex parent task into smaller, atomic sub-tasks.
        Enhanced with tool pre-filtering and context passing.
        FIX 2: Now implements discovery-first approach when parent task has failure context.
        """
        debug_info(
            "--- SPAWNER: Decomposing Task into smaller tasks ---",
            f"Task ID: {parent_task.task_id}",
            metadata={
                "function name": "decompose_task_for_subAgent",
                "task_id": parent_task.task_id,
                "description": parent_task.description,
                "tool_name": parent_task.tool_name,
                "depth": parent_task.depth,
            },
        )

        try:
            if parent_task.depth < 1:
                # only if depth is 1 we can also modify the description to get better tool recommendations like add recommended tools of fallbacks
                recommended_tools = AgentCoreHelpers.recommend_tools_for_task(
                    f"Break down complex task: {parent_task.description}",
                    max_tools=8,
                    parent_context=parent_context,
                )
            else:
                # if depth is more than 1, we get all the tools so that we don't limit the capabilities of sub-agents
                # FIX: Convert tool objects to tool names for consistent string comparison
                all_tools = AgentCoreHelpers.get_safe_tools_list()
                recommended_tools = [tool.name for tool in all_tools]

            # Ensure the virtual Collector tool is always allowed during decomposition
            if "perform_synthesis" not in recommended_tools:
                recommended_tools.append("perform_synthesis")

            available_tools_str = AgentCoreHelpers.get_detailed_tool_context(
                recommended_tools
            )
        except Exception as e:
            # This is a critical internal error, not just a planning choice.
            debug_error(
                "SubAgent Spawner",
                f"CRITICAL: Failed to generate sub-task prompt due to an internal error: {e}",
                metadata={
                    "function name": "decompose_task_for_subAgent",
                    "task_id": parent_task.task_id,
                    "exception_type": type(e).__name__,
                    "exception": str(e),
                },
            )
            return (
                []
            )  # Return empty list to signal decomposition failure to the caller.

        prompt_generator = HierarchicalAgentPrompt()

        # FIX 2: Pass parent failure context to prompt generator for better decomposition

        failure_context_info = None
        if parent_task.failure_context:
            # Format a concise string for the decomposition prompt
            try:
                fp_preview = (
                    (str(parent_task.failure_context.failed_parameters)[:300] + "...")
                    if parent_task.failure_context.failed_parameters
                    else "None"
                )
            except Exception:
                fp_preview = "None"
            chain_part = (
                f" | Chain: {parent_task.failure_context.parent_failure_chain}"
                if getattr(parent_task.failure_context, "parent_failure_chain", None)
                else ""
            )
            failure_context_info = (
                f"PARENT FAILURE CONTEXT → Type: {parent_task.failure_context.error_type or 'Unknown'} | Message: {parent_task.failure_context.error_message} | "
                f"Fail Count: {getattr(parent_task.failure_context, 'fail_count', 1)} | Failed Params: {fp_preview}{chain_part}"
            )

        system_prompt, human_prompt = (
            prompt_generator.generate_task_decomposition_prompt(
                original_goal=state.original_goal,
                complex_task_description=parent_task.description,
                available_tools_str=available_tools_str,
                parent_context=parent_context,
                depth=parent_task.depth,
                failure_context=failure_context_info,  # Pass failure context to prompt
                recovery_plan=recovery_plan,
            )
        )

        model = ModelManager()
        response = model.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": human_prompt},
            ]
        )
        decomposed_tasks_data = ModelManager.convert_to_json(response.content)

        if not isinstance(decomposed_tasks_data, list):
            debug_warning(
                "SubAgent Spawner",
                "LLM failed to return a valid list for decomposition.",
                metadata={
                    "function name": "decompose_task_for_subAgent",
                    "task_id": parent_task.task_id,
                },
            )
            return []

        sub_tasks: list[TASK] = []
        for i, item in enumerate(decomposed_tasks_data):
            if isinstance(item, dict) and all(
                key in item for key in ["description", "tool_name"]
            ):
                # FIX: Now recommended_tools is consistently list[str] for both depth cases
                if item["tool_name"] not in recommended_tools:
                    debug_warning(
                        "SubAgent Spawner",
                        f"Tool '{item['tool_name']}' not in recommended set. Skipping.",
                        metadata={
                            "function name": "decompose_task_for_subAgent",
                            "task_id": parent_task.task_id,
                            "tool_name": item["tool_name"],
                        },
                    )
                    continue

                base_id_str = str(parent_task.task_id)
                unique_suffix = uuid.uuid4().hex[:8]  # Short UUID part
                sub_task_id = f"{base_id_str}.{i + 1}-{unique_suffix}"

                sub_tasks.append(
                    TASK(
                        task_id=sub_task_id,
                        description=item["description"],
                        tool_name=item["tool_name"],
                        depth=parent_task.depth
                        + 1,  # Increment depth for creating sub-tasks
                        requires_high_fidelity_context=item.get(
                            "requires_high_fidelity_context", False
                        ),
                        # Pass the flag
                        required_context=REQUIRED_CONTEXT(
                            source_node="subAgent_decomposer",
                            triggering_task_id=parent_task.task_id,
                            pre_execution_context=(
                                {
                                    "parent_context_str": parent_context,
                                    "context_type": "spawning_context",
                                    "original_goal": state.original_goal,
                                }
                                if parent_context
                                else None
                            ),
                            # Pass parent's context (completed history + failure info) wrapped in dict
                        ),
                    ),
                )

        debug_info(
            "SubAgent Spawner",
            f"Decomposed into {len(sub_tasks)} validated sub-tasks.",
            metadata={
                "function name": "decompose_task_for_subAgent",
                "task_id": parent_task.task_id,
                "subtasks_created": len(sub_tasks),
            },
        )
        return sub_tasks

    @classmethod
    def inject_subAgent_into_workflow(
        cls, parent_task: TASK, subtasks: list[TASK], state: "WorkflowStateModel"
    ) -> dict:
        """Injects the newly created sub-tasks into the main task list."""
        debug_info(
            "--- SPAWNER: Injecting sub-tasks into the workflow ---",
            f"Parent Task ID: {parent_task.task_id}, Sub-tasks to inject: {len(subtasks)}",
            metadata={
                "function name": "inject_subAgent_into_workflow",
                "parent_task_id": parent_task.task_id,
                "subtasks_to_inject": len(subtasks),
            },
        )

        parent_task.status = "in_progress"
        if not parent_task.execution_context:
            parent_task.execution_context = EXECUTION_CONTEXT(
                tool_name=parent_task.tool_name,
                parameters={},
            )
        parent_task.execution_context.analysis = (
            f"Decomposed into {len(subtasks)} sub-tasks."
        )

        # FIX 1: Inherit parent's failure context for sub-tasks so parameter repair can work
        if (
            parent_task.failure_context
            and parent_task.failure_context.failed_parameters
        ):
            for subtask in subtasks:
                if not subtask.failure_context:
                    subtask.failure_context = FAILURE_CONTEXT(
                        error_message="Inherited from parent task",
                        fail_count=1,
                        error_type="InheritedContext",
                        failed_parameters=parent_task.failure_context.failed_parameters.copy(),
                        strategy_history=(
                            parent_task.failure_context.strategy_history.copy()
                            if parent_task.failure_context.strategy_history
                            else []
                        ),
                    )
                debug_info(
                    "SubAgent Spawner",
                    f"Inherited failed_parameters from parent {parent_task.task_id} to subtask {subtask.task_id}",
                    metadata={
                        "parent_failed_params": parent_task.failure_context.failed_parameters,
                        "subtask_id": subtask.task_id,
                    },
                )

        current_tasks = state.tasks
        try:
            current_task_index = current_tasks.index(parent_task)
        except ValueError:
            debug_warning(
                "SubAgent Spawner",
                f"Could not find parent task {parent_task.task_id} in state.",
                metadata={
                    "function name": "inject_subAgent_into_workflow",
                    "parent_task_id": parent_task.task_id,
                },
            )
            return {"tasks": current_tasks}

        # --- START DEDUPLICATION LOGIC ---
        filtered_subtasks = []
        # Collect descriptions of all completed tasks for quick lookup
        completed_task_signatures = set()
        for t in current_tasks:
            if t.status == "completed":
                # Create a unique signature for comparison
                signature = f"{t.tool_name.lower()}:{t.description.lower()}"
                completed_task_signatures.add(signature)

        for new_sub_task in subtasks:
            new_signature = (
                f"{new_sub_task.tool_name.lower()}:{new_sub_task.description.lower()}"
            )

            if new_signature in completed_task_signatures:
                debug_warning(
                    "SubAgent Spawner",
                    f"Skipping redundant sub-task {new_sub_task.task_id} ('{new_sub_task.description}') as it's semantically equivalent to a completed task.",
                    metadata={
                        "function name": "inject_subAgent_into_workflow",
                        "redundant_task_id": new_sub_task.task_id,
                        "redundant_task_description": new_sub_task.description,
                    },
                )
            else:
                filtered_subtasks.append(new_sub_task)
        # --- END DEDUPLICATION LOGIC ---

        updated_tasks = (
            current_tasks[: current_task_index + 1]
            + filtered_subtasks
            + current_tasks[current_task_index + 1 :]
        )
        return {"tasks": updated_tasks}

    @classmethod
    def spawn_subAgent_recursive(
        cls,
        state: "WorkflowStateModel",
        parent_task: TASK,
        spawn_reason: str,
        parent_context: str | None,
        recovery_plan: str | None = None,
    ) -> dict:
        """The main orchestrator for the spawning process."""
        # FIX: Ensure a failure_context exists for the parent BEFORE we call any analysis or decomposition.
        # Some failure paths set task.status = 'failed' but don't populate failure_context; the spawner and
        # recovery logic rely on that context to choose discovery-first decompositions.
        if getattr(parent_task, "status", None) == "failed" and not getattr(
            parent_task, "failure_context", None
        ):
            # Create a minimal synthetic failure_context from available execution_context so downstream nodes
            # (strategy decision, decomposer) have the failed parameters and an error message to reason about.
            synthetic_failed_params = None
            try:
                if parent_task.execution_context and isinstance(
                    parent_task.execution_context.parameters, dict
                ):
                    synthetic_failed_params = (
                        parent_task.execution_context.parameters.copy()
                    )
            except Exception:
                synthetic_failed_params = None

            parent_task.failure_context = FAILURE_CONTEXT(
                error_message=(
                    parent_task.execution_context.result
                    if parent_task.execution_context
                    and getattr(parent_task.execution_context, "result", None)
                    else f"Parent task {parent_task.task_id} failed without explicit failure_context."
                ),
                fail_count=1,
                last_failure_timestamp=get_formatted_timestamp(),
                error_type="SyntheticFailureContext",
                failed_parameters=synthetic_failed_params,
                strategy_history=[],
            )
            debug_info(
                "SubAgent Spawner",
                f"Injected synthetic failure_context into parent task {parent_task.task_id}",
                metadata={
                    "function name": "spawn_subAgent_recursive",
                    "parent_task_id": parent_task.task_id,
                    "injected_failed_parameters": synthetic_failed_params,
                },
            )

        spawn_analysis = cls.analyze_spawn_requirement(parent_task, spawn_reason, state)
        if not spawn_analysis.get("should_spawn"):
            debug_info(
                "SubAgent Spawner",
                f"Analysis decided not to spawn a sub-agent for task {parent_task.task_id}.",
                metadata={
                    "function name": "spawn_subAgent_recursive",
                    "task_id": parent_task.task_id,
                },
            )

        subtasks = cls.decompose_task_for_subAgent(
            parent_task, state, parent_context, recovery_plan
        )
        if not subtasks:
            debug_warning(
                "SubAgent Spawner",
                f"Decomposition failed for task {parent_task.task_id}.",
                metadata={
                    "function name": "spawn_subAgent_recursive",
                    "task_id": parent_task.task_id,
                },
            )
            return {"spawn_triggered": False}

        injection_result = cls.inject_subAgent_into_workflow(
            parent_task, subtasks, state
        )

        parent_task.subAgent_context = subAgent_CONTEXT(
            subAgent_id=parent_task.task_id,
            subAgent_persona=spawn_analysis.get("spawn_strategy", "decomposer"),
            subAgent_status="active",
            subAgent_tasks=subtasks,
            parent_task_id=parent_task.task_id,
            creation_timestamp=get_formatted_timestamp(),
            notes=f"Spawned for: {spawn_reason}",
        )

        return {
            "spawn_triggered": True,
            "tasks": injection_result["tasks"],
            "current_task_id": subtasks[0].task_id,
            "subtasks_created": len(subtasks),
        }


# 🎭 User-friendly status updates with funny quotes
