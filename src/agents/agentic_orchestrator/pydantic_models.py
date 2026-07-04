from pydantic import BaseModel, Field
from typing import Literal, Any, TYPE_CHECKING
import uuid
from ...utils.timestamp_util import get_formatted_timestamp

# Forward reference for TASK to avoid circular import issues


if TYPE_CHECKING:
    from typing import List

    TaskListType = List["TASK"]
else:
    TaskListType = list["TASK"]


class MAIN_STATE(BaseModel):
    # TODO we are removed main state from the workflow because workflow should work isolated but if we feel context is needed we can add it back

    WORKFLOW_STATUS: Literal["RUNNING", "COMPLETED", "FAILED", "RESTART", "STARTED"] = (
        Field(default="STARTED")
    )
    EXECUTED_NODES: list[str] = Field(
        default_factory=list, description="List of executed nodes in the workflow"
    )


class REQUIRED_CONTEXT(BaseModel):
    source_node: str = Field(..., description="Which node created this task")
    triggering_task_id: str | int | float | None = Field(
        default=None, description="The ID of the parent task that spawned this one"
    )
    creation_timestamp: str = Field(default_factory=lambda: get_formatted_timestamp())
    pre_execution_context: dict | None = Field(
        default=None, description="Any context relevant before executing the task"
    )


class EXECUTION_CONTEXT(BaseModel):
    tool_name: str = Field(
        ..., description="The specific tool required to execute this task"
    )
    parameters: dict = Field(
        ..., description="Parameters required for the tool execution"
    )
    result: str | None = Field(
        default=None, description="The output or result from the last execution attempt"
    )
    analysis: str | None = Field(
        default=None, description="Any analysis derived from the tool execution result"
    )
    goal_achieved: bool = Field(
        default=False, description="Indicates if the task's specific goal was met"
    )


class FAILURE_CONTEXT_STRATEGY(BaseModel):
    recovery_strategy: Literal[
        "PARAMETER_REPAIR",
        "ALTERNATIVE_TOOL",
        "TASK_DECOMPOSITION",
        "NO_STRATEGY",
        "SKIP",
    ] = Field(default="PARAMETER_REPAIR", description="The recovery strategy attempted")
    reasoning: str = Field(..., description="Reasoning behind choosing this strategy")
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="LOW", description="Confidence in this strategy"
    )
    estimated_success_probability: int = Field(
        default=0,
        description="Estimated probability (0-100) of success with this strategy",
        ge=0,
        le=100,
    )
    next_steps: str | None = Field(
        default=None, description="Recommended next steps after this strategy"
    )
    outcome: Literal["FAILURE", "APPLIED", "NOT_APPLIED"] = Field(
        default="NOT_APPLIED", description="Outcome after attempting this strategy"
    )
    timestamp: str = Field(
        default_factory=lambda: get_formatted_timestamp(),
        description="Timestamp when this strategy was attempted",
    )

    details: dict[str, Any] | None = Field(
        default={}, description="contains Additional details about the strategy attempt"
    )


class FAILURE_CONTEXT(BaseModel):
    error_message: str = Field(
        ..., description="Detailed error message from the last failure"
    )
    fail_count: int = Field(
        description="number of times the task has failed", default=1, ge=1
    )
    last_failure_timestamp: str | None = Field(
        default=None, description="Timestamp of the last failure"
    )
    stack_trace: str | None = Field(
        default=None, description="Stack trace or debug info from the failure"
    )
    recovery_actions: dict[str, Any] | None = Field(
        default=None, description="Any recovery actions taken"
    )
    error_type: str | None = Field(
        default=None, description="Type or category of the error"
    )
    failed_parameters: dict[str, Any] | None = Field(
        default=None, description="The parameters that caused the failure"
    )  # <-- NEW FIELD
    strategy_history: list[FAILURE_CONTEXT_STRATEGY] | None = Field(
        default_factory=list,
        description="History of all recovery strategies attempted with outcomes",
    )  # <-- NEW FIELD
    # Cooldown timestamp to avoid tight retry loops
    next_attempt_timestamp: str | None = Field(
        default=None, description="Earliest time allowed for next retry"
    )


class subAgent_CONTEXT(BaseModel):
    subAgent_id: str | int | float | None = Field(
        default=None, description="Unique identifier for the sub-agent"
    )
    subAgent_persona: str | None = Field(
        default=None, description="The persona or role assigned to the sub-agent"
    )
    subAgent_status: Literal["idle", "active", "completed", "failed"] | None = Field(
        default=None, description="Current status"
    )
    subAgent_tasks: TaskListType | None = Field(
        default=None, description="List of tasks assigned to the sub-agent"
    )
    parent_task_id: str | int | float | None = Field(
        default=None,
        description="The ID of the parent task that spawned this sub-agent",
    )
    creation_timestamp: str | None = Field(
        default=None, description="Timestamp of when the sub-agent was created"
    )
    completion_timestamp: str | None = Field(
        default=None, description="Timestamp of completion"
    )
    notes: str | None = Field(
        default=None, description="Additional notes about the sub-agent's operations"
    )
    result: str | None = Field(
        default=None, description="Overall result from the sub-agent's operations"
    )


class TASK(BaseModel):
    task_id: str = Field(
        description="Unique identifier for the task",
        default_factory=lambda: str(uuid.uuid4()),
    )
    description: str = Field(
        ..., description="A clear description of what the task is supposed to achieve"
    )
    tool_name: str = Field(
        ..., description="The specific tool required to execute this task"
    )
    status: Literal["pending", "in_progress", "completed", "failed", "skip"] = Field(
        description="current status", default="pending"
    )
    max_retries: int = Field(
        description="maximum number of retries allowed", default=1, ge=0
    )
    depth: int = Field(
        description="recursion depth of the task", default=0, ge=0
    )  # for tracking how deep we are in sub-agent spawning and preventing infinite loops
    requires_high_fidelity_context: bool = Field(
        description="If true, the raw results of parent/sibling tasks should be prioritized in the context.",
        default=False,
    )

    required_context: REQUIRED_CONTEXT = Field(
        ..., description="Context required before executing the task"
    )
    execution_context: EXECUTION_CONTEXT | None = Field(
        default=None, description="Context for executing the task"
    )
    failure_context: FAILURE_CONTEXT | None = Field(
        default=None, description="Context for any failures"
    )
    subAgent_context: subAgent_CONTEXT | None = Field(
        default=None, description="Context for sub-agents"
    )
    # Optional earliest next attempt timestamp (for exponential backoff / cooldown)
    next_attempt_at: str | None = Field(
        default=None,
        description="Earliest timestamp when this task can be attempted again",
    )


class AgentState(BaseModel):
    TASKS: list[TASK]
    CURRENT_TASK_ID: int | float = Field(
        ..., description="current task id being executed"
    )
    original_goal: str = Field(
        ..., description="The original high-level goal provided by the user"
    )
    persona: str | None = Field(
        default=None, description="The persona for the next action"
    )


class WorkflowStateModel(BaseModel):
    tasks: list[TASK]
    current_task_id: str | int | float
    executed_nodes: list[str]
    original_goal: str
    persona: str | None = None
    workflow_status: str | None = None
    final_response: Any | None = None


# Resolve forward references after all models are defined
subAgent_CONTEXT.model_rebuild()
TASK.model_rebuild()
