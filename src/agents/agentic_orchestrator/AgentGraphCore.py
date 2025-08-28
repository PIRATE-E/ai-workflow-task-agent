from datetime import datetime
from typing import TypedDict, Literal, Optional, Union, List, TYPE_CHECKING, Dict, Any

from langgraph.constants import END
from langgraph.graph import StateGraph
#
from pydantic import BaseModel, Field

# Fixed imports - use relative imports instead of src.
from ...models.state import State
from ...tools.lggraph_tools.tool_assign import ToolAssign
from ...utils.model_manager import ModelManager
from .hierarchical_agent_prompts import HierarchicalAgentPrompt

# Forward reference for TASK to avoid circular import issues
if TYPE_CHECKING:
    from typing import List as ListType
    TaskListType = ListType['TASK']
else:
    TaskListType = 'List[TASK]'


class MAIN_STATE(BaseModel):
    state:State # would be maintained by the stateAccessor for conversation messages and other main state info
    # metadata about the session and routing logics could be added here in future
    WORKFLOW_STATUS:Literal['RUNNING', 'COMPLETED', 'FAILED', 'RESTART', 'STARTED'] = Field(default="STARTED") # overall status of the workflow
    EXECUTED_NODES: list[str] = Field(default_factory=list, description="List of executed nodes in the workflow") # list of executed nodes in the workflow (I know that it could be derived from the state graph but for easy access we maintain it here)



class REQUIRED_CONTEXT(BaseModel):
    source_node:str = Field(..., description="Which node created this task (e.g., 'initial_planner', 'error_fallback_agent').") # the specific node that provided this context
    triggering_task_id:Optional[int] = Field(default=None, description="The ID of the parent task that spawned this one, if any.") # the task id that triggered this context if any
    creation_timestamp:datetime = Field(default_factory=datetime.utcnow) # timestamp of when the context was created

    # ----- pre execution context -----
    pre_execution_context:Optional[dict] = Field(default=None, description="Any context or notes relevant before executing the task. (could be instruction or system level details)") # any additional context or notes relevant before executing the task


class EXECUTION_CONTEXT(BaseModel):
    tool_name:str = Field(..., description="The specific tool required to execute this task (e.g., 'google_search', 'read_file', etc).") # the specific tool required to execute this task
    parameters:dict = Field(..., description="Parameters required for the tool execution.") # parameters required for the tool execution
    result:Optional[str] = Field(default=None, description="The output or result from the last execution attempt of the tool.") # result of the tool execution

    # ----- post execution context -----
    analysis:Optional[str] = Field(default=None, description="Any analysis or post execution context derived from the tool execution result.") # any analysis or insights derived from the tool execution result

class recovery_actions(TypedDict):
    require_spawn_new_agent:bool # whether to spawn a new agent to handle the task
    updated_parameters:Optional[dict] # updated parameters for retrying the task
    alternative_tool:Optional[str] # alternative tool to use for retrying the task

class FAILURE_CONTEXT(BaseModel):
    error_message:str = Field(..., description="Detailed error message from the last failure.") # detailed error message from the last failure
    fail_count:int = Field(description="number of times the task has failed", default=1, ge=1) # number of times the task has failed
    last_failure_timestamp:Optional[datetime] = Field(default=None, description="Timestamp of the last failure occurrence.") # timestamp of the last failure occurrence
    stack_trace:Optional[str] = Field(default=None, description="Stack trace or debug info from the failure, if available.") # stack trace or debug info from the failure if available
    recovery_actions:Optional[Dict[str, Any]] = Field(default=None, description="Any recovery actions taken after the failure.") # any recovery actions taken after the failure
    error_type:Optional[str] = Field(default=None, description="Type or category of the error (e.g., 'ToolExecutionError', 'ValidationError', etc).") # type or category of the error


class subAgent_CONTEXT(BaseModel):
    """ CONTEXT for tasks to spawn their own sub-agents if required """
    subAgent_id:Optional[int] = Field(default=None, description="Unique identifier for the sub-agent, if spawned.") # unique identifier for the sub-agent if spawned
    subAgent_persona:Optional[str] = Field(default=None, description="The persona or role assigned to the sub-agent (e.g., 'task agent', 'fallback agent').") # the persona or role assigned to the sub-agent
    subAgent_status:Optional[Literal['idle', 'active', 'completed', 'failed']] = Field(default=None, description="Current status of the sub-agent.") # current status of the sub-agent
    # Fixed circular reference using forward reference
    subAgent_tasks:Optional[TaskListType] = Field(default=None, description="List of tasks assigned to the sub-agent.") # list of tasks assigned to the sub-agent
    parent_task_id:Optional[int] = Field(default=None, description="The ID of the parent task that spawned this sub-agent.") # the ID of the parent task that spawned this sub-agent
    creation_timestamp:Optional[datetime] = Field(default=None, description="Timestamp of when the sub-agent was created.") # timestamp of when the sub-agent was created
    completion_timestamp:Optional[datetime] = Field(default=None, description="Timestamp of when the sub-agent completed its tasks.") # timestamp of when the sub-agent completed its tasks
    notes:Optional[str] = Field(default=None, description="Any additional notes or context about the sub-agent's operations.") # any additional notes or context about the sub-agent's operations
    result:Optional[str] = Field(default=None, description="Overall result or output from the sub-agent's operations.") # overall result or output from the sub-agent's operations


class TASK(BaseModel):
    task_id:Union[int, float] = Field(description="Unique identifier for the task", default=0)
    description:str = Field(..., description="A clear, natural language description of what the task is supposed to achieve.")
    tool_name:str = Field(..., description="The specific tool required to execute this task (e.g., 'google_search', 'read_file', etc).") # the specific tool required to execute this task
    status:Literal['pending', 'in_progress', 'completed', 'failed'] = Field(description="current status of the task", default='pending') # status of the task
    max_retries:int = Field(description="maximum number of retries allowed for the task", default=3, ge=0) # maximum number of retries allowed for the task

    # complex context's for the task
    required_context:REQUIRED_CONTEXT = Field(..., description="Context required before executing the task.") # context required before executing the task
    execution_context:Optional[EXECUTION_CONTEXT] = Field(default=None, description="Context required for executing the task.") # context required for executing the task
    failure_context:Optional[FAILURE_CONTEXT] = Field(default=None, description="Context related to any failures encountered during task execution.") # context related to any failures encountered during task execution
    subAgent_context:Optional[subAgent_CONTEXT] = Field(default=None, description="Context related to any sub-agents spawned for this task.") # context related to any sub-agents spawned for this task


class AgentState(BaseModel):
    TASKS:list[TASK] # list of tasks with their details for current session
    MAIN_STATE:MAIN_STATE # state of the main workflow
    CURRENT_TASK_ID:Union[int, float] =  Field(..., description="current task id which is getting execution")# details of the current task being worked on
    original_goal:str = Field(..., description="The original high-level goal provided by the user.") # the original high-level goal provided by the user
    persona: Optional[str] = Field(default=None, description="The persona for the next action, set by the classifier.")

# Resolve forward references after all models are defined
subAgent_CONTEXT.model_rebuild()
TASK.model_rebuild()

#### why do we need this class (to maintain the core graph structure and routing logic for the agentic orchestrator)
####### answer :- because we need to perform the true agentic flow without bloating out the context window of the main agent (agent_mode_node)
####### and this is not only limited to trigger once and wait for the result, even in future we could allow the creation
####### this Agent orchestrator to be into subAGENT means :------ MAIN AGENT -> subAGENT1 -> subAGENT2 -> subAGENT3 and so on and these subAGENT's have their own tasks and context

###??? why do we need multiple subAgents??? when the tasks are not depend on each other write a file of summary from this repo and
# another task is find the best repo for automation these are not interdependent tasks so
# we can create multiple subAgents to handle these tasks in parallel (doesn't share context or their context is not dependent on each other)
####### example -

"""
user: I want you to analyze this GitHub repository: <link>.
First, use a code summarization tool to generate a high-level summary of the codebase.
Next, use a static analysis tool to identify potential code issues or areas for improvement.
Finally, use a project management tool to create a prioritized TODO list of features and improvements based on your findings.
----------
agent: Sure! I will create a sub-agent to handle this multi-step task. (subAgent could launch another subAgent if required)
context : - user query, STARTED as main state
------------ then -
Subagent 1 :
 task 1 Code Summarization Agent
 (do this task requires more than 2 tools - if yes then create subAgent1 with its own tasks and context) why subagent 1?? because it is sub agent of subAgent 1 
 by this you would understand that we can trigger the graph {recursively} but they wont share full context - just decided context on by the SubAgent's persona here sub Agent starts acting like main agent XD !!!
 
 
 
 task 2 Static Analysis Agent
 this required only llm processing which got done 
 
 task 3 Project Management Agent
 this required write file tool 
"""

class AgentGraphCore:
    # which nodes we do required for the agent graph
    # 1 - subAGENT_classifier - classify the subAGENT's persona then provide the TASK(CONTEXT) or assume its result(LOOPBACK) which subAGENT have to performed
    # ** what is agent's persona - it could be a AGENT PERFORM TASK OR AGENT PERFORM ERROR FALLBACK (# ** Note: 'agent's persona' is a learning term here, not actual logic. It could be 'AGENT PERFORM TASK' or 'AGENT PERFORM ERROR FALLBACK'. **)
    # 2 - subAGENT_router - route the subAGENT to the correct node as per its persona
    # 3 - subAGENT_task_executor - execute the task assigned to the subAGENT
    # 4 - subAGENT_error_fallback - if the subAGENT fails for at-least 2 times then route it to error fallback which would try to fix the issue and reassign the task
    # 5 - subAGENT_task_updater - update the task status in the AgentState
    # 6 - subAGENT_task_planner - plan the next task for the agent based on the current state and previous tasks
    # 7 - subAGENT_finalizer - finalize the task and update the state accordingly

    @classmethod
    def __subAGENT_initial_planner(cls, state: AgentState) -> dict:
        """
        Creates the high-level plan (the "what" and "which tool"), but not the specific parameters.
        """
        print("--- NODE: Initial Planner ---")
        goal = state.get('original_goal', 'Unknown goal')
        print(f"Original Goal: {goal}")

        # Generate prompts for the LLM
        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = prompt_generator.generate_initial_plan_prompt(goal)

        # Invoke the LLM to generate the high-level plan
        model = ModelManager(model="openai/gpt-oss-120b")  # Using the default model from settings
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ])

        # Convert the response to JSON format
        llm_returned = ModelManager.convert_to_json(response.content)

        # Handle case where LLM returns a dict with a "content" key instead of a list
        if isinstance(llm_returned, dict) and "content" in llm_returned:
            try:
                llm_returned = ModelManager.convert_to_json(llm_returned["content"])
            except:
                # If parsing fails, create a minimal plan
                llm_returned = [
                    {"task_id": 1, "description": "Process user request", "tool_name": "llm_summarize"}
                ]

        # Ensure we have a list
        if not isinstance(llm_returned, list):
            llm_returned = [
                {"task_id": 1, "description": "Process user request", "tool_name": "llm_summarize"}
            ]

        # Convert LLM output to Task objects
        actual_tasks: list[TASK] = []
        for item in llm_returned:
            # Validate that item has the required keys
            if all(key in item for key in ["task_id", "description", "tool_name"]):
                actual_tasks.append(
                    TASK(
                        task_id=item["task_id"],
                        description=item["description"],
                        tool_name=item["tool_name"],
                        required_context=REQUIRED_CONTEXT(source_node="initial_planner")
                    )
                )

        # If no valid tasks were created, create a fallback task
        if not actual_tasks:
            actual_tasks.append(
                TASK(
                    task_id=1,
                    description="Process user request",
                    tool_name="llm_summarize",
                    required_context=REQUIRED_CONTEXT(source_node="initial_planner")
                )
            )

        print(f"Generated {len(actual_tasks)} high-level tasks.")

        return {
            "tasks": actual_tasks,
            "current_task_id": actual_tasks[0].task_id if actual_tasks else 1,
            "workflow_status": "RUNNING",
            "executed_nodes": state['executed_nodes'] + ["subAGENT_initial_planner"]
        }

    # -------------------------------------------------------------
    @classmethod
    def __subAGENT_classifier(cls, state: AgentState) -> dict:
        """Inspects the current task and decides the next step: generate params or handle failure."""
        print("--- NODE: Classifier ---")
        current_task_id = state.get('current_task_id', 0)
        tasks = state.get('tasks', [])
        current_task = next((t for t in tasks if t.task_id == current_task_id), None)

        persona = "AGENT_PERFORM_TASK"
        if current_task and current_task.failure_context and current_task.failure_context.fail_count >= current_task.max_retries:
            persona = "AGENT_PERFORM_ERROR_FALLBACK"

        print(f"Task ID: {current_task_id}, Persona: {persona}")
        return {"executed_nodes": state['executed_nodes'] + ["subAGENT_classifier"], "persona": persona}

    @classmethod
    def subAGENT_parameter_generator(cls, state: AgentState) -> dict:
        """
        NEW NODE: Generates the specific parameters for a task just-in-time.
        """
        print("--- NODE: Parameter Generator ---")
        current_task_id = state.get('current_task_id', 0)
        updated_tasks = state.get('tasks', [])

        # Find the current task to update it
        for task in updated_tasks:
            if task.task_id == current_task_id:
                print(f"Generating parameters for Task {current_task_id}: {task.description}")

                # Generate prompts for parameter generation
                prompt_generator = HierarchicalAgentPrompt()
                system_prompt, human_prompt = prompt_generator.generate_parameter_prompt(
                    task.description,
                    task.tool_name,
                    str(task.required_context.pre_execution_context) if task.required_context.pre_execution_context else None
                )

                # Invoke the LLM to generate parameters
                model = ModelManager(model="openai/gpt-oss-120b")
                response = model.invoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt}
                ])

                # Convert the response to JSON format
                parameters = ModelManager.convert_to_json(response.content)

                # Handle case where LLM returns a dict with a "content" key instead of the actual parameters
                if isinstance(parameters, dict) and "content" in parameters:
                    try:
                        parameters = ModelManager.convert_to_json(parameters["content"])
                    except Exception as e:
                        print(f"WARNING: JSON parsing failed for parameters: {e}")
                        print(f"Raw content: {parameters.get('content', 'No content')[:200]}...")
                        # If parsing fails, create minimal parameters
                        parameters = {"task_id": current_task_id}

                # Ensure parameters is a dict
                if not isinstance(parameters, dict):
                    parameters = {"task_id": current_task_id}

                # Create and assign the execution context
                task.execution_context = EXECUTION_CONTEXT(
                    tool_name=task.tool_name,
                    parameters=parameters
                )
                print(f"Generated Parameters: {parameters}")
                break

        return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_parameter_generator"]}

    @classmethod
    def __tool_executor(cls, tool_name: str, parameters: dict) -> tuple[bool, str]:
        """
        Finds and executes the appropriate tool from the tool registry.
        Returns a tuple of (success: bool, result: str).
        """
        # Step 1: Import necessary singletons inside the method to avoid circular dependencies.
        from ...tools.lggraph_tools.tool_assign import ToolAssign
        from ...tools.lggraph_tools.tool_response_manager import ToolResponseManager

        print(f"--- HELPER: Attempting to execute tool: '{tool_name}' with parameters: {parameters} ---")

        # Step 2: Retrieve the list of all currently registered tools.
        try:
            registered_tools = cls.__get_safe_tools_list()
        except RuntimeError as e:
            error_msg = str(e)
            print(error_msg)
            return (False, error_msg)

        # Step 3: Find the specific tool by name (case-insensitive).
        tool_to_execute = next((tool for tool in registered_tools if tool.name.lower() == tool_name.lower()), None)

        if not tool_to_execute:
            error_msg = f"Error: Tool '{tool_name}' is not a valid or registered tool."
            print(error_msg)
            return (False, error_msg)

        # Step 4: Invoke the tool and handle potential exceptions.
        try:
            invoke_params = parameters.copy()
            invoke_params["tool_name"] = tool_name

            tool_to_execute(invoke_params)

            # Safe access to ToolResponseManager response
            responses = ToolResponseManager().get_response()
            if not responses:
                error_msg = f"No response received from tool {tool_name}"
                return (False, error_msg)
            
            last_response = responses[-1]
            if not hasattr(last_response, 'content'):
                error_msg = f"Invalid response format from tool {tool_name}"
                return (False, error_msg)
            
            result = last_response.content
            print(f"Tool '{tool_name}' executed successfully.")
            return (True, result)
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            print(error_msg)
            return (False, error_msg)

    @classmethod
    def __analyze_task_complexity(cls, task: TASK) -> dict:
        """
        Analyzes the complexity of a single task to determine if it's atomic or requires decomposition.
        This is a helper function called by the executor node.
        """
        # Step 1: Log the initiation of the analysis.
        print(f"--- HELPER: Analyzing complexity for Task {task.task_id}: '{task.description}' ---")

        # Step 2: Generate the appropriate prompt for the LLM call.
        # This uses the prompt design we finalized to ask the LLM if the task is simple or complex.
        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = prompt_generator.generate_task_complexity_analysis_prompt(
            task_description=task.description,
            high_level_tool_name=task.tool_name
        )

        # Step 3: Invoke the LLM to get the analysis.
        model = ModelManager(model="openai/gpt-oss-120b")
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ])

        # Step 4: Parse the LLM's JSON response.
        analysis_result = ModelManager.convert_to_json(response.content)

        # Step 5: Provide robust fallback logic. If the LLM response is invalid or malformed,
        # we default to the safest option: assuming the task is simple and does not require decomposition.
        if not isinstance(analysis_result, dict) or "requires_decomposition" not in analysis_result:
            print(f"Warning: Invalid complexity analysis response. Defaulting to non-decomposable.")
            return {
                "requires_decomposition": False,
                "reasoning": "Fallback due to invalid LLM response format.",
                "atomic_tool_name": task.tool_name # Assume the initial tool name is atomic
            }
        
        # Step 6: Return the validated analysis from the LLM.
        print(f"Complexity Analysis Result: {analysis_result}")
        return analysis_result

    @classmethod
    def __subAGENT_task_executor(cls, state: AgentState) -> dict:
        """Executes the current task OR triggers decomposition if the task is complex."""
        print("--- NODE: Task Executor ---")
        current_task_id = state.get('current_task_id', 0)
        updated_tasks = state.get('tasks', [])
        tasks = state.get('tasks', [])
        current_task = next((task for task in tasks if task.task_id == current_task_id), None)

        if not current_task:
            print(f"Error: Could not find current task with ID {current_task_id}. Halting execution.")
            return {"workflow_status": "FAILED"}

        # --- Complexity Analysis and Spawning Logic ---
        try:
            # Step 1: Call the helper function to analyze the task's complexity.
            complexity_analysis = cls.__analyze_task_complexity(current_task)

            # Step 2: Check the result from the analyzer.
            if complexity_analysis.get("requires_decomposition"):
                spawn_result = Spawn_subAgent.spawn_subAgent_recursive(
                    parent_task=current_task,
                    spawn_reason=complexity_analysis.get("reasoning", "No reasoning provided."),
                    state=state
                )
                if spawn_result and spawn_result.get("spawn_triggered"):
                    return {"tasks": spawn_result['tasks'], "executed_nodes": state['executed_nodes'] + ["subAGENT_task_executor"]}
                else:
                    # Spawning failed - mark task as failed, don't continue
                    current_task.status = "failed"
                    current_task.failure_context = FAILURE_CONTEXT(
                        error_message="Task requires decomposition but spawning failed",
                        error_type="SpawningFailure"
                    )
                    return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_task_executor"]}
            else:
                print(f"Task ID: {current_task_id} is atomic. Proceeding with direct execution.")

        except Exception as e:
            print(f"Error during complexity analysis or sub-agent spawning logic: {str(e)}")
            # If analysis fails, we can add failure context and halt, or try to proceed.
            # For now, we'll add a failure context and let the graph route to the error handler.
            current_task.status = "failed"
            current_task.failure_context = FAILURE_CONTEXT(error_message=f"Complexity analysis failed: {e}", error_type="AnalysisError")
            return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_task_executor"]}

        # --- Direct Execution for Atomic Tasks ---
        try:
            # The task was deemed atomic, so we execute it directly.
            print(f"Executing atomic Task ID: {current_task_id} with tool: {current_task.execution_context.tool_name}")

            success, result = cls.__tool_executor(current_task.execution_context.tool_name,
                                                  current_task.execution_context.parameters)
            # Update task status and result based on execution outcome.
            if not success:  # Use the boolean flag
                # Handle failure
                current_task.status = "failed"
                current_task.failure_context = FAILURE_CONTEXT(
                    error_message=result,  # result contains error message when success=False
                    fail_count=1,
                    error_type="ToolExecutionError"
                )
            else:
                # Handle success
                current_task.status = "completed"
                current_task.execution_context.result = result

        except Exception as e:
            # This is a fallback for unexpected errors during the execution loop itself.
            print(f"Critical error during task execution for Task ID: {current_task_id}: {str(e)}")
            current_task.status = "failed"
            if not current_task.failure_context:
                current_task.failure_context = FAILURE_CONTEXT(error_message=str(e), error_type="UnhandledException")
            else:
                current_task.failure_context.error_message += f"\nAdditional error: {str(e)}"

        return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_task_executor"]}


    @classmethod
    def __get_safe_tools_list(cls):
        """Get a safe list of tools, raising an error if no tools are available."""
        tools = ToolAssign.get_tools_list()
        if not tools:
            # Return at least basic tools or raise meaningful error
            raise RuntimeError("No tools available - system cannot function")
        return tools

    @classmethod
    def __get_tools_string(cls):
        """Get a formatted string of available tools."""
        try:
            tools = cls.__get_safe_tools_list()
            return "\n".join([f"- {tool.name}: {getattr(tool, 'description', 'No description')}" for tool in tools])
        except RuntimeError:
            return "No tools available"

    @classmethod
    def __subAGENT_error_fallback(cls, state: AgentState) -> dict:
        """Handles tasks that have failed their retry limit."""
        print("--- NODE: Error Fallback ---")
        current_task_id = state.get('current_task_id', 0)
        print(f"Handling failure for Task ID: {current_task_id}")
        updated_tasks = state.get('tasks', [])
        tasks = state.get('tasks', [])
        current_task = next((task for task in tasks if task.task_id == current_task_id), None) # todo replace this to all updated tasks var

        for task in updated_tasks:
            if task.task_id == current_task_id:
                # Get error information
                error_message = task.failure_context.error_message if task.failure_context else "Unknown error"
                error_type = task.failure_context.error_type if task.failure_context else "Unknown error type"

                # Generate prompts for error analysis and recovery
                prompt_generator = HierarchicalAgentPrompt()
                # Call with correct parameters
                available_tools_str = cls.__get_tools_string()  # Readable string of tool names
                system_prompt, human_prompt = prompt_generator.generate_error_recovery_prompt(
                    task_description=task.description,  # ✅ Correct parameter
                    tool_name=task.tool_name,
                    error_message=error_message,
                    available_tools_str=available_tools_str,  # ✅ Pass as keyword argument
                    error_type=error_type  # ✅ Pass as keyword argument
                )

                # Invoke the LLM to analyze the error and suggest recovery actions
                model = ModelManager(model="openai/gpt-oss-120b")
                response = model.invoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt}
                ])

                # Convert the response to JSON format
                recovery_suggestion = ModelManager.convert_to_json(response.content)

                # Handle case where LLM returns a dict with a "content" key
                if isinstance(recovery_suggestion, dict) and "content" in recovery_suggestion:
                    try:
                        recovery_suggestion = ModelManager.convert_to_json(recovery_suggestion["content"])
                    except Exception as e:
                        print(f"WARNING: JSON parsing failed for recovery suggestion: {e}")
                        print(f"Raw content: {recovery_suggestion.get('content', 'No content')[:200]}...")
                        # If parsing fails, create minimal recovery actions
                        recovery_suggestion = {
                            "recovery_strategy": "RETRY_WITH_NEW_PARAMS",
                            "updated_parameters": {},
                            "alternative_tool": None,
                            "reasoning": "Fallback due to JSON parsing error"
                        }

                # Ensure recovery_suggestion is a dict with the required keys
                if not isinstance(recovery_suggestion, dict):
                    recovery_suggestion = {
                        "recovery_strategy": "RETRY_WITH_NEW_PARAMS",
                        "updated_parameters": {},
                        "alternative_tool": None,
                        "reasoning": "Fallback due to invalid response type"
                    }

                # Transform the prompt schema to the code schema
                # Map "recovery_strategy" to "require_spawn_new_agent"
                require_spawn = recovery_suggestion.get("recovery_strategy") == "DECOMPOSE_FAILURE"
                
                # Create recovery_actions dict with the expected schema
                recovery_actions_dict = {
                    "require_spawn_new_agent": require_spawn,
                    "updated_parameters": recovery_suggestion.get("updated_parameters", {}),
                    "alternative_tool": recovery_suggestion.get("alternative_tool")
                }

                # Update the task's failure context with recovery actions
                if task.failure_context:
                    # ✅ FIXED: Direct assignment instead of constructor call
                    task.failure_context.recovery_actions = recovery_actions_dict
                else:
                    task.failure_context = FAILURE_CONTEXT(
                        error_message=error_message,
                        fail_count=task.failure_context.fail_count if task.failure_context else 1,
                        recovery_actions=recovery_actions_dict
                    )

                # Mark task as failed
                task.status = "failed"

                # now inject the recursive error handling subAgent if required
                spawn_result = Spawn_subAgent.spawn_subAgent_recursive(
                    state,
                    current_task,
                    f"error recovery for current task : "
                    f"message :- {task.failure_context.error_message} , "
                    f"failure count :- {task.failure_context.fail_count}"
                    f"error type :- {task.failure_context.error_type}" )
                # Validate spawning result thoroughly
                if spawn_result and spawn_result.get("spawn_triggered") and spawn_result.get("tasks"):
                    print(f"✅ Error recovery spawned {spawn_result.get('subtasks_created', 0)} recovery tasks")

                    # Update parent task status to reflect recovery attempt
                    current_task.status = "in_progress"
                    current_task.execution_context.analysis = f"Recovery spawned: {spawn_result.get('subtasks_created')} tasks"

                    return {
                        "tasks": spawn_result["tasks"],
                        "current_task_id": spawn_result["current_task_id"],
                        "executed_nodes": state["executed_nodes"] + ["subAGENT_error_fallback"]
                    }
                else:
                    print("❌ Error recovery spawning failed - falling back to standard error handling")
                    # Implement fallback error handling
                    current_task.status = "failed"
                    return {"tasks": updated_tasks,
                            "executed_nodes": state['executed_nodes'] + ["subAGENT_error_fallback"]}

        return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_error_fallback"]}


    @classmethod
    def __subAGENT_task_planner(cls, state: AgentState) -> dict:
        """Finds the next pending task. Also checks if a parent task can be marked as completed."""
        print("--- NODE: Task Planner ---")
        
        # Get the ID of the task that just finished.
        last_completed_id = state.get('current_task_id')
        tasks = state.get('tasks', [])

        # --- Parent Task Completion Logic ---
        # Check if the just-completed task was a sub-task (i.e., has a float ID).
        # Enhanced parent completion logic
        if isinstance(last_completed_id, float):
            parent_id = int(last_completed_id)

            # Find the parent task first
            parent_task = next((t for t in tasks if t.task_id == parent_id), None)

            # Only proceed if parent exists and is in_progress
            if parent_task and parent_task.status == "in_progress":
                sibling_tasks = [t for t in tasks if isinstance(t.task_id, float) and int(t.task_id) == parent_id]

                if all(t.status in ['completed', 'failed'] for t in sibling_tasks):
                    # Check if any subtasks failed
                    failed_subtasks = [t for t in sibling_tasks if t.status == 'failed']
                    # Ensure execution_context exists before using it
                    if not parent_task.execution_context:
                        parent_task.execution_context = EXECUTION_CONTEXT(
                            tool_name=parent_task.tool_name,
                            parameters={}
                        )
                    
                    if failed_subtasks:
                        parent_task.status = 'failed'
                        parent_task.execution_context.analysis = f"Failed due to {len(failed_subtasks)} failed subtasks"
                    else:
                        parent_task.status = 'completed'
                        parent_task.execution_context.analysis = f"Successfully completed {len(sibling_tasks)} subtasks"
        
        # --- Find Next Task Logic ---
        # Find all tasks that are still pending.
        pending_tasks = [t for t in tasks if t.status == 'pending']
        
        # Sort by task_id to ensure logical progression (e.g., 3.1, then 3.2, then 4).
        if pending_tasks:
            pending_tasks.sort(key=lambda x: x.task_id)
            next_task_id = pending_tasks[0].task_id
        else:
            next_task_id = None
        
        print(f"Next task ID: {next_task_id}")
        return {"current_task_id": next_task_id, "executed_nodes": state.get('executed_nodes', []) + ["subAGENT_task_planner"], "tasks": tasks}


    @classmethod
    def __subAGENT_finalizer(cls, state: AgentState) -> dict:
        """Consolidates results and generates a final response."""
        print("--- NODE: Finalizer ---")

        # Collect all task results
        all_results = []
        tasks = state.get('tasks', [])
        for task in tasks:
            if task.execution_context and task.execution_context.result:
                all_results.append(f"Task {task.task_id} ({task.tool_name}): {task.execution_context.result}")
            elif task.failure_context:
                all_results.append(f"Task {task.task_id} ({task.tool_name}) failed: {task.failure_context.error_message}")

        # Generate prompts for the final response generation
        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = prompt_generator.generate_final_response_prompt(
            all_results,
            state.get('original_goal', 'Unknown goal')
        )

        # Invoke the LLM to generate the final response
        model = ModelManager(model="openai/gpt-oss-120b")
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ])

        final_response = response.content
        print(f"Final Response: {final_response}")

        return {"final_response": final_response, "workflow_status": "COMPLETED",
                "executed_nodes": state.get('executed_nodes', []) + ["subAGENT_finalizer"]}

    # =================================================================
    # 3. Graph Routing Logic (Updated for New Flow)
    # =================================================================

    @classmethod
    def __router_main(cls, state: AgentState) -> Literal["subAGENT_classifier", "subAGENT_task_planner", "subAGENT_finalizer", "END"]:
        """Main router after a task is completed or failed."""
        print("--- ROUTER: Main ---")
        all_tasks_finished = all(t.status in ['completed', 'failed'] for t in state.get('tasks', []))
        if all_tasks_finished:
            return "subAGENT_finalizer"
        return "subAGENT_task_planner"

    @classmethod
    def __router_classifier(cls, state: AgentState) -> Literal["subAGENT_parameter_generator", "subAGENT_error_fallback"]:
        """Routes to parameter generation for normal tasks or to fallback for failed tasks."""
        print("--- ROUTER: Classifier ---")
        if state.get("persona") == "AGENT_PERFORM_ERROR_FALLBACK":
            return "subAGENT_error_fallback"
        return "subAGENT_parameter_generator"


    #------- sub agent spawning and routing logic could be added in future ---------

    @classmethod
    def __spawn_subAgent(cls, parent_task: TASK, subtasks: list[TASK]) -> dict:
        """Implement your recursive subAgent spawning concept"""
        # Create subAgent context
        subagent_context = subAgent_CONTEXT(
            subAgent_id=len(parent_task.subAgent_context.subAgent_tasks) if parent_task.subAgent_context else 1,
            subAgent_persona="specialized_executor",
            subAgent_status="active",
            subAgent_tasks=subtasks,
            parent_task_id=parent_task.task_id,
            creation_timestamp=datetime.utcnow()
        )

        # Recursive graph execution for subAgent
        subagent_state = AgentState(
            TASKS=subtasks,
            MAIN_STATE=MAIN_STATE(state=State(), WORKFLOW_STATUS="RUNNING"),
            CURRENT_TASK_ID=subtasks[0].task_id,
            original_goal=f"SubAgent execution for parent task {parent_task.task_id}"
        )

        # Execute subAgent workflow recursively
        subagent_graph = cls.build_graph()
        final_state = subagent_graph.invoke(subagent_state)

        return final_state

    # -------------------------------------------------------------

    @classmethod
    def build_graph(cls):
        # Use dict-based state for LangGraph instead of Pydantic model
        from langgraph.graph import StateGraph
        from typing import TypedDict, List, Union
        
        class WorkflowState(TypedDict):
            tasks: List[TASK]
            current_task_id: Union[int, float]
            executed_nodes: List[str]
            original_goal: str
            persona: str
            workflow_status: str
            
        graph_builder = StateGraph(WorkflowState)

        # Add all nodes
        graph_builder.add_node("subAGENT_initial_planner", cls.__subAGENT_initial_planner)
        graph_builder.add_node("subAGENT_classifier", cls.__subAGENT_classifier)
        graph_builder.add_node("subAGENT_parameter_generator", cls.subAGENT_parameter_generator)
        graph_builder.add_node("subAGENT_task_executor", cls.__subAGENT_task_executor)
        graph_builder.add_node("subAGENT_error_fallback", cls.__subAGENT_error_fallback)
        graph_builder.add_node("subAGENT_task_planner", cls.__subAGENT_task_planner)
        graph_builder.add_node("subAGENT_finalizer", cls.__subAGENT_finalizer)

        # Define the graph's flow
        graph_builder.set_entry_point("subAGENT_initial_planner")
        graph_builder.add_edge("subAGENT_initial_planner", "subAGENT_classifier")

        graph_builder.add_conditional_edges(
            "subAGENT_classifier",
            cls.__router_classifier,
            {"subAGENT_parameter_generator": "subAGENT_parameter_generator",
             "subAGENT_error_fallback": "subAGENT_error_fallback"}
        )

        graph_builder.add_edge("subAGENT_parameter_generator", "subAGENT_task_executor")

        graph_builder.add_conditional_edges(
            "subAGENT_task_executor",
            cls.__router_main,
            {"subAGENT_task_planner": "subAGENT_task_planner", "subAGENT_finalizer": "subAGENT_finalizer", END: END}
        )

        graph_builder.add_conditional_edges(
            "subAGENT_error_fallback",
            cls.__router_main,
            {"subAGENT_task_planner": "subAGENT_task_planner", "subAGENT_finalizer": "subAGENT_finalizer", END: END}
        )

        graph_builder.add_edge("subAGENT_task_planner", "subAGENT_classifier")
        graph_builder.add_edge("subAGENT_finalizer", END)

        return graph_builder.compile()



    ##### subAgent spawning and routing logic #####

class Spawn_subAgent:
    """
    Handles the logic for dynamically decomposing a complex task into a series of smaller, atomic sub-tasks.
    This class embodies the "Progressive Refinement" pattern, allowing the agent to handle abstract goals.
    """

    @classmethod
    def analyze_spawn_requirement(cls, parent_task: TASK, reason: str, state: AgentState) -> dict:
        """
        Uses an LLM to analyze if a task is too complex and requires decomposition (spawning).
        
        Args:
            parent_task: The task to be analyzed.
            reason: The high-level reason for the analysis (e.g., "initial execution", "error recovery").
            state: The current state of the main agent for context.

        Returns:
            A dictionary containing the analysis, including a boolean `should_spawn`.
        """
        # Step 1: Provide clear feedback on what is being analyzed.
        error_context = "no context till now available"
        if parent_task.failure_context:
            error_context = f"task failed {parent_task.failure_context.fail_count} times.. and Last error: {parent_task.failure_context.error_message}"
        print(f"--- SPAWNER: Analyzing Task ID: {parent_task.task_id} for sub-agent spawning due to {reason}. {error_context} ---")

        # Step 2: Generate a prompt for the LLM to analyze the task's complexity.
        prompt_generator = HierarchicalAgentPrompt()
        # todo not implemented the prompt generator for spawn analysis
        system_prompt, human_prompt = prompt_generator.generate_spawn_analysis_prompt(
            task_description=parent_task.description,
            tool_name=parent_task.tool_name,
            status=parent_task.status,
            spawn_reason=reason,
            error_context=error_context
        )

        # Step 3: Invoke the LLM.
        model = ModelManager(model="openai/gpt-oss-120b")
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ])
        analysis_result = ModelManager.convert_to_json(response.content)

        # Step 4: Implement robust fallback logic. If the LLM fails to provide a valid response,
        # default to the safest option: do not spawn a sub-agent.
        if not isinstance(analysis_result, dict) or "should_spawn" not in analysis_result:
            print("Warning: LLM failed to provide a valid spawn analysis. Defaulting to NO spawn.")
            return {"should_spawn": False, "reasoning": "Fallback due to invalid LLM response."}

        print(f"Spawn Analysis Result: {analysis_result.get('reasoning')}")
        return analysis_result

    @classmethod
    def decompose_task_for_subAgent(cls, parent_task: TASK, state: AgentState) -> List[TASK]:
        """
        Uses an LLM to decompose a single complex parent task into a list of smaller, atomic sub-tasks.
        
        Args:
            parent_task: The complex task to decompose.
            state: The current state of the main agent.

        Returns:
            A list of new, atomic TASK objects.
        """
        print(f"--- SPAWNER: Decomposing Task ID: {parent_task.task_id} into smaller tasks. ---")
        
        # Step 1: Get the list of available, real tools to ground the LLM.
        try:
            available_tool_names = [tool.name.lower() for tool in AgentGraphCore._AgentGraphCore__get_safe_tools_list()]
        except RuntimeError:
            available_tool_names = []  # Empty list if no tools available

        available_tools_str = "\n".join(available_tool_names)

        # Step 2: Generate the prompt for the decomposition LLM call.
        prompt_generator = HierarchicalAgentPrompt()
        system_prompt, human_prompt = prompt_generator.generate_task_decomposition_prompt(
            complex_task_description=parent_task.description,
            available_tools_str=available_tools_str
        )

        # Step 3: Invoke the LLM.
        model = ModelManager(model="openai/gpt-oss-120b")
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ])
        decomposed_tasks_data = ModelManager.convert_to_json(response.content)

        # Step 4: Validate and convert the LLM response into a list of Task objects.
        if not isinstance(decomposed_tasks_data, list):
            print("Warning: LLM failed to return a valid list for decomposition. Returning empty list.")
            return []

        # ✅ FIXED: Get tool names for proper comparison
        try:
            available_tool_names = [tool.name.lower() for tool in AgentGraphCore.__get_safe_tools_list()]
        except RuntimeError:
            print("Warning: No tools available. Skipping sub-task creation.")
            return []

        sub_tasks: List[TASK] = []
        for i, item in enumerate(decomposed_tasks_data):
            if all(key in item for key in ["description", "tool_name"]):
                # Create a new, unique ID for the sub-task to avoid conflicts.
                # A simple approach is to use the parent ID and a sub-index.

                # Validate tool name
                if item["tool_name"].lower() not in available_tool_names:
                    print(f"Warning: Tool '{item['tool_name']}' is not registered. Skipping this sub-task.")
                    # todo currently we are skipping the invalid tool subtask but in future we can route it to error fallback node of subAGENT
                    continue

                # Ensure parent ID is integer part only
                base_id = int(parent_task.task_id) if isinstance(parent_task.task_id, float) else parent_task.task_id
                sub_task_id = float(f"{base_id}.{i + 1}")

                # Validate result is reasonable
                if sub_task_id > 999.999:
                    raise ValueError(f"Task ID too complex: {sub_task_id}")
                
                sub_tasks.append(
                    TASK(
                        task_id=sub_task_id,
                        description=item["description"],
                        tool_name=item["tool_name"],
                        required_context=REQUIRED_CONTEXT(
                            source_node="subAgent_decomposer",
                            triggering_task_id=parent_task.task_id
                        )
                    )
                )
        
        print(f"Decomposed into {len(sub_tasks)} smaller tasks.")
        return sub_tasks

    @classmethod
    def inject_subAgent_into_workflow(cls, parent_task: TASK, subtasks: List[TASK], state: AgentState) -> dict:
        """
        Injects the newly created sub-tasks into the main task list, right after the parent task.
        """
        print(f"--- SPAWNER: Injecting {len(subtasks)} sub-tasks into the workflow. ---")
        
        # Mark the parent task as 'in_progress' since its sub-tasks are now being executed.
        parent_task.status = "in_progress"
        if parent_task.execution_context:
            parent_task.execution_context.analysis = f"Decomposed into {len(subtasks)} sub-tasks."
        else:
            # Create execution context if it doesn't exist
            parent_task.execution_context = EXECUTION_CONTEXT(
                tool_name=parent_task.tool_name,
                parameters={},
                analysis=f"Decomposed into {len(subtasks)} sub-tasks."
            )

        # Find the exact position for the injection (after the current task).
        try:
            # Handle both dict and AgentState model formats
            if isinstance(state, dict):
                current_tasks = state.get('tasks', [])
            else:
                # AgentState model format
                current_tasks = state.TASKS if hasattr(state, 'TASKS') else []
                
            current_task_index = current_tasks.index(parent_task)
        except ValueError:
            print(f"Error: Could not find parent task {parent_task.task_id} in state. Cannot inject sub-tasks.")
            return {"tasks": current_tasks}  # Return original tasks on error

        # Splice the sub-tasks into the main task list.
        updated_tasks = current_tasks[:current_task_index + 1] + subtasks + current_tasks[current_task_index + 1:]

        return {
            "tasks": updated_tasks,
        }

    @classmethod
    def spawn_subAgent_recursive(cls, state: AgentState, parent_task: TASK, spawn_reason: str) -> dict:
        """
        The main orchestrator for the spawning process. It analyzes, decomposes, and injects.
        """
        # 1. Analyze the requirement of spawning the sub-agent.
        spawn_analysis = cls.analyze_spawn_requirement(parent_task, spawn_reason, state)
        if not spawn_analysis.get("should_spawn"):
            print(f"Analysis decided not to spawn a sub-agent for task {parent_task.task_id}.")
            return {"spawn_triggered": False}

        # 2. Generate the sub-tasks using LLM decomposition.
        subtasks = cls.decompose_task_for_subAgent(parent_task, state)
        if not subtasks:
            print(f"Warning: Decomposition failed for task {parent_task.task_id}. No sub-tasks were generated.")
            return {"spawn_triggered": False}

        # 3. Inject the sub-tasks into the main agent's workflow.
        injection_result = cls.inject_subAgent_into_workflow(parent_task, subtasks, state)

        # 4. Update the parent task with sub-agent context.
        parent_task.subAgent_context = subAgent_CONTEXT(
            subAgent_id=parent_task.task_id, # Use parent task ID for association
            subAgent_persona=spawn_analysis.get("spawn_strategy", "unknown"),
            subAgent_status="active",
            subAgent_tasks=subtasks,
            parent_task_id=parent_task.task_id,
            creation_timestamp=datetime.utcnow(),
            notes=f"Spawned for: {spawn_reason}"
        )

        # 5. Return the updated state with spawn details.
        return {
            "spawn_triggered": True,
            "tasks": injection_result['tasks'],
            "current_task_id": subtasks[0].task_id, # Set the first sub-task as the new current task
        }

    # the main actual headache is how to route in the subAGENT graph such that it can handle the LOOPBACK and ERROR FALLBACK scenarios
    # also how to maintain the state of the subAGENT's tasks and their results in the main AgentState

    # ** now break it down this is routing logic template or instruction for the subAGENT's persona **
    #               ########### when to rout to which node ###########

    ####@@@@@@@@@@@@@@@@ route to the initial_planner when @@@@@@@@@@@@@@@@@#####
    #                      when the WORKFLOW_STATUS is 'STARTED' only
    #                       its work to get the higher level request from the user and break it down into smaller tasks for agents (details marked in the memory mcp)

    ####@@@@@@@@@@@@@@@@@@ route to the end node when @@@@@@@@@@@@@@@@@#####
    #                      when the all status of the tasks for task1 task2 ...
    #                      taskN are completed like task1.status == 'completed'
    #                      and task2.status == 'completed'
    #                      and ... taskN.status == 'completed'


    ####@@@@@@@@@@@@@@@@@@ route to the task executor node when @@@@@@@@@@@@@@@@@#####
    #                      when the subAGENT's persona is 'AGENT PERFORM TASK'
    #                      and the CURRENT_TASK.status is 'pending' or 'in_progress'
    #                      and the CURRENT_TASK.result is empty or None

    ####@@@@@@@@@@@@@@@@@@ route to the error fallback node when @@@@@@@@@@@@@@@@@#####
    #                      when the subAGENT's persona is 'AGENT PERFORM ERROR FALLBACK'
    #                      and the CURRENT_TASK.status is 'in_progress' or 'pending'
    #                      and the CURRENT_TASK.result is empty or None
    #                      and the CURRENT_TASK has failed for at-least 2 times (you can maintain a fail_count in the task context for this)

    ####@@@@@@@@@@@@@@@@@@ route to the task updater node when @@@@@@@@@@@@@@@@@#####
    #                      when the CURRENT_TASK.status is 'completed'
    #                      and the CURRENT_TASK.result is not empty or None
    #                      and the subAGENT's persona is 'AGENT PERFORM TASK' or 'AGENT PERFORM ERROR FALLBACK'

    ####@@@@@@@@@@@@@@@@@@ route to the task planner node when @@@@@@@@@@@@@@@@@#####
    #                      when the CURRENT_TASK.status is 'completed'
    #                      and the CURRENT_TASK.result is not empty or None
    #                      and the subAGENT's persona is 'AGENT PERFORM TASK' or 'AGENT PERFORM ERROR FALLBACK'
    #                      and there are more tasks in the TASKS list with status 'pending'

    ####@@@@@@@@@@@@@@@@@@ route to the task classifier node when @@@@@@@@@@@@@@@@@#####
    #                      when the CURRENT_TASK.status is 'completed'
    #                      and the CURRENT_TASK.result is not empty or None
    #                      and the subAGENT's persona is 'AGENT PERFORM TASK' or 'AGENT PERFORM ERROR FALLBACK'
    #                      and there are no more tasks in the TASKS list with status 'pending'
    #                      and the WORKFLOW_STATUS is 'RUNNING' or 'RESTART'
    #                      and the EXECUTED_NODES does not contain 'subAGENT_finalizer'

    ####@@@@@@@@@@@@@@@@@@ route to the finalizer node when @@@@@@@@@@@@@@@@@#####
    #                      when the WORKFLOW_STATUS is 'COMPLETED' or 'FAILED'
    #                      and the EXECUTED_NODES does not contain 'subAGENT_finalizer'
    #                      and all tasks in TASKS list have status 'completed' or 'failed'
    #                      and the CURRENT_TASK.status is 'completed'
    #                      and the CURRENT_TASK.result is not empty or None


