from datetime import datetime
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

# =================================================================
# 1. Final, Refined Pydantic Schemas
# =================================================================

class ProvenanceContext(BaseModel):
    """Context about WHERE this task came from and WHY."""
    source_node: str = Field(..., description="Which node created this task.")
    triggering_task_id: Optional[int] = Field(default=None)
    creation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    pre_execution_analysis: Optional[str] = Field(default=None, description="Agent's analysis of the situation *before* execution.")

class ExecutionContext(BaseModel):
    """Context about the specific tool execution itself."""
    tool_name: str
    parameters: dict
    result: Optional[str] = Field(default=None)
    analysis: Optional[str] = Field(default=None, description="Agent's summary of what the result means.")

class FailureContext(BaseModel):
    """Context that ONLY exists if a task fails."""
    error_message: str
    error_type: str
    fail_count: int = Field(default=1, ge=1)
    last_failure_timestamp: datetime = Field(default_factory=datetime.utcnow)
    stack_trace: Optional[str] = None

class Task(BaseModel):
    """The main Task model, composing optional, categorized context blocks."""
    task_id: int
    description: str
    # The planner now sets the intended tool here.
    tool_name: str 
    status: Literal['pending', 'in_progress', 'completed', 'failed'] = 'pending'
    max_retries: int = 2

    provenance: ProvenanceContext
    # The execution context is now created by the parameter_generator, not the planner.
    execution: Optional[ExecutionContext] = None
    failure: Optional[FailureContext] = None

class AgentState(BaseModel):
    """The full, Pydantic-validated state of the agentic workflow."""
    tasks: List[Task] = Field(default_factory=list)
    current_task_id: Optional[int] = None
    original_goal: str
    workflow_status: Literal['STARTED', 'RUNNING', 'COMPLETED', 'FAILED', 'RESTART'] = 'STARTED'
    executed_nodes: List[str] = Field(default_factory=list)
    final_response: Optional[str] = None
    persona: Optional[str] = None # To be set by the classifier

    class Config:
        arbitrary_types_allowed = True

# =================================================================
# 2. Placeholder Node Functions (with new Parameter Generator)
# =================================================================

def subAGENT_initial_planner(state: AgentState) -> dict:
    """
    Creates the high-level plan (the "what" and "which tool"), but not the specific parameters.
    """
    print("--- NODE: Initial Planner ---")
    goal = state['original_goal']
    print(f"Original Goal: {goal}")

    # Placeholder: The LLM returns a high-level plan without parameters.
    # Placeholder for LLM-generated high-level plan (mock data)
    llm_returned: list[dict[str, Union[str, int]]] = [
        {"task_id": 1, "description": "First, read the README.md file.", "tool_name": "read_file"},
        {"task_id": 2, "description": "Next, list the directories in the root folder.", "tool_name": "list_directory"},
    ]

    # Convert LLM output to Task objects
    actual_tasks: list[Task] = [
        Task(
            task_id=item["task_id"],
            description=item["description"],
            tool_name=item["tool_name"],
            provenance=ProvenanceContext(source_node="initial_planner")
        )
        for item in llm_returned
    ]

    print(f"Generated {len(actual_tasks)} high-level tasks.")

    return {
        "tasks": actual_tasks,
        "current_task_id": 1,
        "workflow_status": "RUNNING",
        "executed_nodes": state['executed_nodes'] + ["subAGENT_initial_planner"]
    }

def subAGENT_classifier(state: AgentState) -> dict:
    """Inspects the current task and decides the next step: generate params or handle failure."""
    print("--- NODE: Classifier ---")
    current_task_id = state['current_task_id']
    current_task = next((t for t in state['tasks'] if t.task_id == current_task_id), None)
    
    persona = "AGENT_PERFORM_TASK"
    if current_task and current_task.failure and current_task.failure.fail_count >= current_task.max_retries:
        persona = "AGENT_PERFORM_ERROR_FALLBACK"
        
    print(f"Task ID: {current_task_id}, Persona: {persona}")
    return {"executed_nodes": state['executed_nodes'] + ["subAGENT_classifier"], "persona": persona}


def subAGENT_parameter_generator(state: AgentState) -> dict:
    """
    NEW NODE: Generates the specific parameters for a task just-in-time.
    """
    print("--- NODE: Parameter Generator ---")
    current_task_id = state['current_task_id']
    updated_tasks = state['tasks']
    
    # Find the current task to update it
    for task in updated_tasks:
        if task.task_id == current_task_id:
            print(f"Generating parameters for Task {current_task_id}: {task.description}")
            # TODO: Implement LLM call to generate parameters based on task.description and previous results.
            
            # Placeholder: Create mock parameters.
            mock_parameters = {"path": "."} # Generic parameter for many file tools
            if task.tool_name == "read_file":
                mock_parameters = {"path": "./README.md"}

            # Create and assign the execution context
            task.execution = ExecutionContext(tool_name=task.tool_name, parameters=mock_parameters)
            print(f"Generated Parameters: {mock_parameters}")
            break

    return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_parameter_generator"]}


def subAGENT_task_executor(state: AgentState) -> dict:
    """Executes the current task using the now-defined execution context."""
    print("--- NODE: Task Executor ---")
    current_task_id = state['current_task_id']
    updated_tasks = state['tasks']
    
    for task in updated_tasks:
        if task.task_id == current_task_id:
            print(f"Executing Task ID: {current_task_id} with tool: {task.execution.tool_name}")
            # TODO: Implement the actual tool invocation logic here.
            
            # Placeholder: Simulate a successful execution
            task.status = "completed"
            task.execution.result = f"Successfully executed tool '{task.execution.tool_name}' with params {task.execution.parameters}."
            break
            
    return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_task_executor"]}

def subAGENT_error_fallback(state: AgentState) -> dict:
    """Handles tasks that have failed their retry limit."""
    print("--- NODE: Error Fallback ---")
    current_task_id = state['current_task_id']
    print(f"Handling failure for Task ID: {current_task_id}")
    updated_tasks = state['tasks']
    for task in updated_tasks:
        if task.task_id == current_task_id:
            task.status = "failed"
            break
    return {"tasks": updated_tasks, "executed_nodes": state['executed_nodes'] + ["subAGENT_error_fallback"]}

def subAGENT_task_planner(state: AgentState) -> dict:
    """Finds the next pending task and sets it as current."""
    print("--- NODE: Task Planner ---")
    pending_tasks = [t for t in state['tasks'] if t.status == 'pending']
    next_task_id = min([t.task_id for t in pending_tasks]) if pending_tasks else None
    print(f"Next task ID: {next_task_id}")
    return {"current_task_id": next_task_id, "executed_nodes": state['executed_nodes'] + ["subAGENT_task_planner"]}

def subAGENT_finalizer(state: AgentState) -> dict:
    """Consolidates results and generates a final response."""
    print("--- NODE: Finalizer ---")
    all_results = [t.execution.result for t in state['tasks'] if t.execution and t.execution.result]
    final_response = "Workflow complete. Summary of results: " + " | ".join(all_results)
    print(f"Final Response: {final_response}")
    return {"final_response": final_response, "workflow_status": "COMPLETED", "executed_nodes": state['executed_nodes'] + ["subAGENT_finalizer"]}

# =================================================================
# 3. Graph Routing Logic (Updated for New Flow)
# =================================================================

def router_main(state: AgentState) -> Literal["subAGENT_classifier", "subAGENT_task_planner", "subAGENT_finalizer", END]:
    """Main router after a task is completed or failed."""
    print("--- ROUTER: Main ---")
    all_tasks_finished = all(t.status in ['completed', 'failed'] for t in state['tasks'])
    if all_tasks_finished:
        return "subAGENT_finalizer"
    return "subAGENT_task_planner"

def router_classifier(state: AgentState) -> Literal["subAGENT_parameter_generator", "subAGENT_error_fallback"]:
    """Routes to parameter generation for normal tasks or to fallback for failed tasks."""
    print("--- ROUTER: Classifier ---")
    if state.get("persona") == "AGENT_PERFORM_ERROR_FALLBACK":
        return "subAGENT_error_fallback"
    return "subAGENT_parameter_generator"

# =================================================================
# 4. Graph Definition Class
# =================================================================

class AgentGraphCore:
    @classmethod
    def build_graph(cls):
        graph_builder = StateGraph(AgentState)

        # Add all nodes
        graph_builder.add_node("subAGENT_initial_planner", subAGENT_initial_planner)
        graph_builder.add_node("subAGENT_classifier", subAGENT_classifier)
        graph_builder.add_node("subAGENT_parameter_generator", subAGENT_parameter_generator)
        graph_builder.add_node("subAGENT_task_executor", subAGENT_task_executor)
        graph_builder.add_node("subAGENT_error_fallback", subAGENT_error_fallback)
        graph_builder.add_node("subAGENT_task_planner", subAGENT_task_planner)
        graph_builder.add_node("subAGENT_finalizer", subAGENT_finalizer)

        # Define the graph's flow
        graph_builder.set_entry_point("subAGENT_initial_planner")
        graph_builder.add_edge("subAGENT_initial_planner", "subAGENT_classifier")
        
        graph_builder.add_conditional_edges(
            "subAGENT_classifier",
            router_classifier,
            {"subAGENT_parameter_generator": "subAGENT_parameter_generator", "subAGENT_error_fallback": "subAGENT_error_fallback"}
        )
        
        graph_builder.add_edge("subAGENT_parameter_generator", "subAGENT_task_executor")

        graph_builder.add_conditional_edges(
            "subAGENT_task_executor",
            router_main,
            {"subAGENT_task_planner": "subAGENT_task_planner", "subAGENT_finalizer": "subAGENT_finalizer", END: END}
        )
        
        graph_builder.add_conditional_edges(
            "subAGENT_error_fallback",
            router_main,
            {"subAGENT_task_planner": "subAGENT_task_planner", "subAGENT_finalizer": "subAGENT_finalizer", END: END}
        )
        
        graph_builder.add_edge("subAGENT_task_planner", "subAGENT_classifier")
        graph_builder.add_edge("subAGENT_finalizer", END)

        return graph_builder.compile()

if __name__ == '__main__':
    print("Building Agent Graph Core with Just-in-Time Parameter Generation...")
    agent_graph = AgentGraphCore.build_graph()
    print("Graph compiled successfully!")
    
    try:
        image_data = agent_graph.get_graph().draw_png()
        with open("agent_graph_JIT.png", "wb") as f:
            f.write(image_data)
        print("Graph visualization saved to agent_graph_JIT.png")
    except Exception as e:
        print(f"Could not create graph visualization. Please install graphviz and pydot.\nError: {e}")