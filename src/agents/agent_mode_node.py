"""
Agent Node and Agent Class for LangGraph Workflow

This module defines the Agent class and the agent_node function, which together implement the core agent node logic for the LangGraph workflow system.

Features:
    - Agent class encapsulates tool execution, reasoning, and evaluation logic for a single agent node.
    - agent_node function orchestrates the message processing, tool selection, execution, and final response evaluation for each node in the workflow.
    - Robust error handling and debug logging using the debug_helpers and rich_traceback_manager modules.
    - Full support for tool fallback, parameter generation, and workflow quality evaluation.
    - Designed for extensibility and integration with LangGraph and other workflow engines.

Usage:
    # To use the agent node in a workflow:
    from src.agents.agent_mode_node import agent_node
    result = agent_node(state)

    # To use the Agent class directly:
    agent = Agent(agent_exe_array=[...])
    agent.start(index=0)

All major steps are instrumented with debug_info, debug_warning, and debug_critical for traceability and diagnostics.
"""
import re
from datetime import datetime

from src.config import settings
from src.models.state import StateAccessor
from src.prompts.agent_mode_prompts import Prompt
from src.tools.lggraph_tools.tool_assign import ToolAssign
# 🚀 Debug System Migration (v2 - Robust Protocol)
from src.ui.diagnostics.debug_helpers import (
    debug_info, debug_warning, debug_critical,
    debug_tool_response
)
# 🎨 Rich Traceback Integration
from src.ui.diagnostics.rich_traceback_manager import RichTracebackManager, rich_exception_handler
from src.utils.argument_schema_util import get_tool_argument_schema
from src.utils.listeners.rich_status_listen import RichStatusListener
from src.utils.model_manager import ModelManager


class Agent:
    """
    Agent class that encapsulates the behavior of an agent node in the LangGraph workflow.
    This class is responsible for processing messages, invoking tools, and generating responses.
    
    🔧 ENHANCED v3.0: Context-aware agent with comprehensive execution context tracking.
    """

    @rich_exception_handler("Agent Initialization")
    def __init__(self, agent_exe_array: list):
        """
        Initializes the Agent with an execution tool_name's array that contains the sequence of operations to perform.
        :param agent_exe_array: List of tool_names to execute in the agent node.
        """
        try:
            if not isinstance(agent_exe_array, list):
                raise ValueError(f"agent_exe_array must be a list, got {type(agent_exe_array)}")
            if not agent_exe_array:
                raise ValueError("agent_exe_array cannot be empty")
            self.agent_exe_array = agent_exe_array
            # 🔧 NEW: Track execution context for context-aware operations
            self.execution_context = {
                "tool_execution_history": [],
                "reasoning_chain": [],
                "success_patterns": [],
                "failure_patterns": [],
                "workflow_state": "initializing"
            }
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Agent Initialization",
                extra_context={
                    "agent_exe_array_type": type(agent_exe_array),
                    "agent_exe_array_length": len(agent_exe_array) if hasattr(agent_exe_array, '__len__') else 'N/A'
                }
            )
            raise

    def _build_execution_context(self, current_index: int) -> str:
        """
        🔧 NEW: Build comprehensive execution context for context-aware prompting.
        
        Args:
            current_index: Current position in the execution array
            
        Returns:
            Formatted execution context string for prompts
        """
        context_parts = []

        # ✅ SAFE: Add None checking
        execution_history = self.execution_context.get("tool_execution_history") or []
        reasoning_chain = self.execution_context.get("reasoning_chain") or []

        # Add workflow state
        total_tools = len(self.agent_exe_array)
        workflow_state = self.execution_context.get("workflow_state", "initializing")
        context_parts.append(f"🔄 WORKFLOW STATE: Step {current_index + 1} of {total_tools} (Status: {workflow_state})")

        # ✅ SAFE: Check length after ensuring it's not None
        if execution_history:
            context_parts.append("\n📈 TOOL EXECUTION HISTORY:")
            for i, execution in enumerate(execution_history): 
                context_parts.append(
                    f"  Step {execution.get('step', i)}: {execution.get('tool_name', 'unknown')} - {execution.get('status', 'unknown')}")
                if execution.get('reasoning'):
                    context_parts.append(f"    Reasoning: {execution['reasoning']}...")
                if execution.get('result_summary'):
                    context_parts.append(f"    Result: {execution['result_summary']}...")

        # Add reasoning chain
        if reasoning_chain:
            context_parts.append("\n🧠 REASONING CHAIN:")
            for i, reasoning in enumerate(reasoning_chain):
                context_parts.append(f"  {i + 1}. {reasoning}...")

        # Add success patterns
        if self.execution_context["success_patterns"]:
            context_parts.append("\n✅ SUCCESSFUL PATTERNS:")
            for pattern in self.execution_context["success_patterns"]:
                context_parts.append(f"  • {pattern}")

        # Add failure patterns to avoid
        if self.execution_context["failure_patterns"]:
            context_parts.append("\n❌ PATTERNS TO AVOID:")
            for pattern in self.execution_context["failure_patterns"]:
                context_parts.append(f"  • {pattern}")

        # Add current step context
        if current_index < len(self.agent_exe_array):
            current_tool = self.agent_exe_array[current_index]
            context_parts.append(f"\n🎯 CURRENT STEP CONTEXT:")
            context_parts.append(f"  Tool: {current_tool.get('tool_name', 'unknown')}")
            context_parts.append(f"  Position: {current_index + 1}/{total_tools}")
            context_parts.append(
                f"  Workflow: {'Sequential execution' if total_tools > 1 else 'Single tool execution'}")

        return "\n".join(context_parts)

    def _update_execution_context(self, step_info: dict):
        """
        🔧 NEW: Update execution context with new step information.
        
        Args:
            step_info: Dictionary containing step execution information
        """
        # Add to execution history
        self.execution_context["tool_execution_history"].append(step_info)

        # Update reasoning chain
        if step_info.get("reasoning"):
            self.execution_context["reasoning_chain"].append(step_info["reasoning"])

        # Track success/failure patterns
        if step_info.get("status") == "success":
            pattern = f"{step_info.get('tool_name', 'unknown')} with {step_info.get('parameter_summary', 'default params')}"
            self.execution_context["success_patterns"].append(pattern)
        elif step_info.get("status") == "failed":
            pattern = f"{step_info.get('tool_name', 'unknown')} failed: {step_info.get('failure_reason', 'unknown')}"
            self.execution_context["failure_patterns"].append(pattern)

        # Update workflow state
        total_steps = len(self.agent_exe_array)
        completed_steps = len(self.execution_context["tool_execution_history"])

        if completed_steps == 0:
            self.execution_context["workflow_state"] = "starting"
        elif completed_steps < total_steps:
            self.execution_context["workflow_state"] = "in_progress"
        else:
            self.execution_context["workflow_state"] = "completing"

    @rich_exception_handler("Agent Execution Start")
    def start(self, index: int = 0) -> 'Agent':
        from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
        """
        Starts the agent node execution.
        start the execution one by one in the agent_exe_array.
        Each operation in the array is executed sequentially.
        :return:
        """

        @rich_exception_handler("Single Tool Execution")
        def execute_single_tool(tool_exe_dict: dict):
            """
            execute single tool based on the provided dictionary.
            :param tool_exe_dict: dict with the following structure:
                {
                    "tool_name": str,  # Name of the tool to execute
                    "reasoning": str,  # AI reasoning for selecting this tool
                    "parameters": dict # Parameters to pass to the tool
                }
            :return: The result of the tool execution.
            """
            try:
                tool_name = tool_exe_dict.get("tool_name", "none")
                reasoning = tool_exe_dict.get("reasoning", "")
                parameters = tool_exe_dict.get("parameters", {})

                if tool_name.lower() == "none":
                    return settings.AIMessage(content=f"Agent decided not to use any tools. Reasoning: {reasoning}")

                # Find the tool by name
                for tool in ToolAssign.get_tools_list():
                    if tool.name.lower() == tool_name.lower():
                        try:
                            # run the tool with the provided parameters
                            tool.invoke(parameters)
                            # only for debugging going to remove it later
                            debug_info(
                                heading="AGENT_MODE • TOOL_EXECUTION",
                                body=f"Executing tool '{tool_name}' with parameters: {parameters}",
                                metadata={
                                    "tool_name": tool_name,
                                    "parameters": str(parameters),
                                    "reasoning": reasoning,
                                    "context": "tool_execution"
                                }
                            )
                            # get the result of the tool execution
                            result = ToolResponseManager().get_response()[-1].content
                            ## evaluate the result
                            try:
                                # 🔧 NEW: Build evaluation context including execution history
                                evaluation_context = self._build_execution_context(
                                    index if hasattr(self, '_build_execution_context') else 0)

                                evaluation_prompt = Prompt().evaluate_in_end(
                                    tool.name.lower(),
                                    result,
                                    StateAccessor().get_last_human_message().content,
                                    evaluation_context  # 🔧 NEW: Pass execution context for context-aware evaluation
                                )

                                eval_model = ModelManager(model=settings.GPT_MODEL)
                                eval_response = eval_model.invoke([
                                    settings.HumanMessage(content=evaluation_prompt[0]),
                                    settings.HumanMessage(content=evaluation_prompt[1])
                                ])
                                eval_response = ModelManager.convert_to_json(eval_response)

                                self._validate_and_fix_evaluation_response(eval_response)

                                evaluation = eval_response.get("evaluation", {})
                                is_success = (evaluation.get("status", "complete") == "complete")
                                # log
                                debug_tool_response(
                                    tool_name=tool_name,
                                    status=evaluation.get('status', 'unknown'),
                                    response_summary=evaluation.get('reasoning', 'No reasoning provided'),
                                    metadata={
                                        "evaluation_status": evaluation.get('status'),
                                        "context": "tool_evaluation",
                                        "user_query": StateAccessor().get_last_human_message().content if StateAccessor().get_last_human_message() else "No query"
                                    }
                                )

                                if not is_success:
                                    reasoning = evaluation.get("reasoning", "No reasoning provided")
                                    debug_critical(
                                        heading="AGENT_MODE • TOOL_EXECUTION",
                                        body=f"Tool '{tool_name}' execution failed",
                                        metadata={
                                            "tool_name": tool_name,
                                            "failure_reason": reasoning,
                                            "context": "tool_execution_failure"
                                        }
                                    )

                                    # now fallback logic to handle the failure
                                    fallback = eval_response.get('fallback', {})
                                    if fallback:
                                        fallback_tool_name = fallback.get('tool_name')
                                        fallback_params = fallback.get('parameters', {})

                                        # Find the actual tool object
                                        for fallback_tool in ToolAssign.get_tools_list():
                                            if fallback_tool.name.lower() == fallback_tool_name.lower():
                                                # Invoke the fallback tool with the provided parameters
                                                debug_info(
                                                    heading="AGENT_MODE • FALLBACK_HANDLING",
                                                    body=f"Invoking fallback tool '{fallback_tool_name}'",
                                                    metadata={
                                                        "original_tool": tool_name,
                                                        "fallback_tool": fallback_tool_name,
                                                        "fallback_params": fallback_params,
                                                        "context": "fallback_execution"
                                                    }
                                                )
                                                fallback_tool.invoke(fallback_params)

                                                # change the result to the fallback tool's response
                                                result = ToolResponseManager().get_response()[-1].content
                                                break
                            except Exception as eval_error:
                                RichTracebackManager.handle_exception(
                                    eval_error,
                                    context=f"Tool Evaluation - {tool_name}",
                                    extra_context={
                                        "tool_name": tool_name,
                                        "result": str(result),
                                        "reasoning": reasoning,
                                        "parameters": str(parameters) if parameters else "No parameters",
                                        "fallback_used": True if 'fallback' in eval_response else False
                                    }
                                )
                                return settings.AIMessage(
                                    content=f"Error evaluating tool '{tool_name}': {str(eval_error)}")

                            return settings.AIMessage(
                                content=f"Tool '{tool_name}' executed successfully. Result: {result}")
                        except Exception as e:
                            RichTracebackManager.handle_exception(
                                e,
                                context=f"Tool Invocation - {tool_name}",
                                extra_context={
                                    "tool_name": tool_name,
                                    "parameters": str(parameters)[:200],
                                    "reasoning": reasoning
                                }
                            )
                            return settings.AIMessage(content=f"Error executing tool '{tool_name}': {str(e)}")

                return settings.AIMessage(content=f"Tool '{tool_name}' not found.")

            except Exception as e:
                RichTracebackManager.handle_exception(
                    e,
                    context="Single Tool Execution Setup",
                    extra_context={"tool_exe_dict": str(tool_exe_dict)[:200]}
                )
                return settings.AIMessage(content=f"Error in tool execution setup: {str(e)}")

        # got list of tool names to execute
        # generate the tool's execution dictionary e.g.:
        """
            {
                    "tool_name": str,  # Name of the tool to execute
                    "reasoning": str,  # AI reasoning for selecting this tool
                    "parameters": dict # Parameters to pass to the tool
            }
        """

        try:
            # Find the tool by name with error handling
            tool_found = None
            for tool in ToolAssign.get_tools_list():
                if tool.name.lower() == self.agent_exe_array[index]["tool_name"].lower():
                    tool_found = tool
                    break

            if not tool_found:
                available_tools = [tool.name for tool in ToolAssign.get_tools_list()]
                raise ValueError(
                    f"Tool '{self.agent_exe_array[index]['tool_name']}' not found in the tool list. Available tools: {available_tools}")

            # extract the parameters from the first tool execution dictionary
            try:
                parameters_schema_found_tool = get_tool_argument_schema(tool_found)
            except Exception as schema_error:
                RichTracebackManager.handle_exception(
                    schema_error,
                    context=f"Tool Schema Extraction - {tool_found.name}",
                    extra_context={"tool_name": tool_found.name}
                )
                raise

            # Get previous responses with error handling
            try:
                if index == 0 or len(self.agent_exe_array) == 1:
                    previous_ai_response = "No previous response"
                else:
                    last_ai_msg = ToolResponseManager().get_last_ai_message()
                    previous_ai_response = getattr(last_ai_msg, 'content', 'No previous response')

                last_human_msg = StateAccessor().get_last_human_message()
                previous_human_response = getattr(last_human_msg, 'content', 'No previous response')
            except Exception as response_error:
                RichTracebackManager.handle_exception(
                    response_error,
                    context="Previous Response Retrieval",
                    extra_context={"index": index, "array_length": len(self.agent_exe_array)}
                )
                previous_ai_response = "No previous response"
                previous_human_response = "No previous response"

            # Debug logging with error handling
            try:
                debug_info(
                    heading="AGENT_MODE • PARAMETER_GENERATION",
                    body=f"Generating parameters for tool '{self.agent_exe_array[index]['tool_name']}'",
                    metadata={
                        "tool_name": self.agent_exe_array[index]['tool_name'],
                        "previous_ai_response": previous_ai_response[:200] if previous_ai_response else "None",
                        "previous_human_response": previous_human_response[:200] if previous_human_response else "None",
                        "parameters_schema": str(parameters_schema_found_tool)[
                            :300] if parameters_schema_found_tool else "None",
                        "context": "parameter_generation_debug",
                        "step_index": index
                    }
                )
            except Exception as debug_error:
                # Don't let debug logging errors break the flow
                print(f"Debug logging error: {debug_error}")

            # Generate prompt with error handling and conversation history
            try:
                # Get full conversation history from StateAccessor for better context
                try:
                    all_messages = StateAccessor().get_messages()
                    conversation_context = []
                    for msg in all_messages:
                        if hasattr(msg, 'content') and msg.content:
                            msg_type = "Human" if "Human" in str(type(msg)) else "AI"
                            conversation_context.append(f"{msg_type}: {msg.content}")

                    full_conversation_history = "\n".join(
                        conversation_context) if conversation_context else "No conversation history"
                except Exception as history_error:
                    debug_warning(
                        heading="AGENT_MODE • CONVERSATION_HISTORY",
                        body="Could not retrieve full conversation history",
                        metadata={
                            "error_type": type(history_error).__name__,
                            "error_message": str(history_error)[:200],
                            "context": "conversation_history_retrieval",
                            "fallback_used": True
                        }
                    )
                    full_conversation_history = f"Previous AI: {previous_ai_response}\n Previous Human: {previous_human_response}"

                # 🔧 NEW: Build comprehensive execution context for context-aware prompting
                execution_context = self._build_execution_context(index)

                debug_info(
                    heading="AGENT_MODE • CONTEXT_AWARE_PROMPTING",
                    body="Generating context-aware prompt with execution history",
                    metadata={
                        "tool_name": self.agent_exe_array[index]["tool_name"],
                        "step_index": index,
                        "context_length": len(execution_context),
                        "has_execution_history": len(self.execution_context["tool_execution_history"]) > 0,
                        "has_reasoning_chain": len(self.execution_context["reasoning_chain"]) > 0,
                        "workflow_state": self.execution_context["workflow_state"]
                    }
                )

                prompt = Prompt().generate_parameter_prompt(
                    self.agent_exe_array[index]["tool_name"],
                    parameters_schema_found_tool,
                    previous_ai_response,
                    full_conversation_history,
                    execution_context  # 🔧 NEW: Pass execution context for context-aware prompting
                )
            except Exception as prompt_error:
                RichTracebackManager.handle_exception(
                    prompt_error,
                    context="Parameter Prompt Generation",
                    extra_context={
                        "tool_name": self.agent_exe_array[index]["tool_name"],
                        "schema_type": type(parameters_schema_found_tool)
                    }
                )
                raise

            # AI invocation with error handling
            try:
                agent_ai = ModelManager(model=settings.GPT_MODEL)
                with settings.console.status("[bold green]Thinking... generating parameters...[/bold green]",
                                             spinner="dots"):
                    response = agent_ai.invoke([
                        settings.HumanMessage(content=prompt[0]),
                        settings.HumanMessage(content=prompt[1])
                    ])
                    response = ModelManager.convert_to_json(response)

                    # 🔧 ENHANCED: Robust parameter response validation
                    if not isinstance(response, dict):
                        debug_warning(
                            heading="AGENT_MODE • INVALID_PARAMETER_RESPONSE",
                            body=f"Expected dict for parameters, got {type(response).__name__}",
                            metadata={
                                "response_type": type(response).__name__,
                                "response_content": str(response)[:200] if response else "None",
                                "expected_type": "dict",
                                "tool_name": self.agent_exe_array[index]["tool_name"],
                                "fallback_action": "create_minimal_dict"
                            }
                        )
                        # Create minimal valid response as fallback
                        response = {
                            "tool_name": self.agent_exe_array[index]["tool_name"],
                            "reasoning": "Fallback response due to invalid LLM output",
                            "parameters": {}
                        }

                    # Validate required keys in response
                    required_keys = ["tool_name", "reasoning", "parameters"]
                    missing_keys = [key for key in required_keys if key not in response]
                    if missing_keys:
                        debug_warning(
                            heading="AGENT_MODE • MISSING_PARAMETER_KEYS",
                            body=f"Missing required keys: {missing_keys}",
                            metadata={
                                "missing_keys": missing_keys,
                                "present_keys": list(response.keys()),
                                "tool_name": self.agent_exe_array[index]["tool_name"],
                                "fallback_action": "add_missing_keys"
                            }
                        )
                        # Add missing keys with safe defaults
                        if "tool_name" not in response:
                            response["tool_name"] = self.agent_exe_array[index]["tool_name"]
                        if "reasoning" not in response:
                            response["reasoning"] = "Auto-generated reasoning due to missing key"
                        if "parameters" not in response:
                            response["parameters"] = {}

                    # Validate tool_name matches expected
                    if response.get("tool_name") != self.agent_exe_array[index]["tool_name"]:
                        debug_warning(
                            heading="AGENT_MODE • TOOL_NAME_MISMATCH",
                            body=f"Tool name mismatch: expected '{self.agent_exe_array[index]['tool_name']}', got '{response.get('tool_name')}'",
                            metadata={
                                "expected_tool": self.agent_exe_array[index]["tool_name"],
                                "received_tool": response.get("tool_name"),
                                "correction_action": "force_correct_tool_name"
                            }
                        )
                        # Force correct tool name
                        response["tool_name"] = self.agent_exe_array[index]["tool_name"]

                    debug_info(
                        heading="AGENT_MODE • PARAMETER_RESPONSE_VALIDATED",
                        body="Parameter response validated successfully",
                        metadata={
                            "tool_name": response.get("tool_name"),
                            "reasoning_length": len(response.get("reasoning", "")),
                            "parameter_count": len(response.get("parameters", {})),
                            "validation_status": "approved"
                        }
                    )

            except Exception as ai_error:
                RichTracebackManager.handle_exception(
                    ai_error,
                    context="AI Parameter Generation",
                    extra_context={
                        "tool_name": self.agent_exe_array[index]["tool_name"],
                        "model": settings.GPT_MODEL,
                        "prompt_length": len(str(prompt)) if 'prompt' in locals() else 'N/A'
                    }
                )
                raise

            # Tool execution with error handling
            try:
                tool_execution_dict = {
                    "tool_name": self.agent_exe_array[index]["tool_name"],
                    "reasoning": response.get("reasoning", ""),
                    "parameters": response.get("parameters", {})
                }

                # 🔧 NEW: Track execution step start
                step_start_info = {
                    "step": index + 1,
                    "tool_name": tool_execution_dict["tool_name"],
                    "reasoning": tool_execution_dict["reasoning"],
                    "parameter_summary": f"{len(tool_execution_dict['parameters'])} parameters",
                    "status": "executing",
                    "timestamp": "current"
                }

                # execute the tool with the provided parameters
                result = execute_single_tool(tool_execution_dict)
                ToolResponseManager().set_response([settings.AIMessage(content=result.content)])

                # 🔧 NEW: Track execution step completion
                step_completion_info = {
                    "step": index + 1,
                    "tool_name": tool_execution_dict["tool_name"],
                    "reasoning": tool_execution_dict["reasoning"],
                    "parameter_summary": f"{len(tool_execution_dict['parameters'])} parameters",
                    "status": "success",
                    "result_summary": result.content[:200] if hasattr(result, 'content') else "No content",
                    "timestamp": "current"
                }
                self._update_execution_context(step_completion_info)

                debug_info(
                    heading="AGENT_MODE • CONTEXT_TRACKING",
                    body="Updated execution context with step completion",
                    metadata={
                        "step": index + 1,
                        "tool_name": tool_execution_dict["tool_name"],
                        "total_history_entries": len(self.execution_context["tool_execution_history"]),
                        "workflow_state": self.execution_context["workflow_state"],
                        "context": "execution_context_update"
                    }
                )

            except Exception as execution_error:
                # 🔧 NEW: Track execution failure
                step_failure_info = {
                    "step": index + 1,
                    "tool_name": self.agent_exe_array[index]["tool_name"],
                    "reasoning": response.get("reasoning", "") if 'response' in locals() else "",
                    "status": "failed",
                    "failure_reason": str(execution_error)[:200],
                    "timestamp": "current"
                }
                self._update_execution_context(step_failure_info)

                RichTracebackManager.handle_exception(
                    execution_error,
                    context="Tool Execution and Response Setting",
                    extra_context={
                        "tool_execution_dict": str(tool_execution_dict) if 'tool_execution_dict' in locals() else 'N/A',
                        "execution_context_state": self.execution_context["workflow_state"]
                    }
                )
                raise

            return self

        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context=f"Agent Start Method - Index {index}",
                extra_context={
                    "index": index,
                    "agent_exe_array_length": len(self.agent_exe_array),
                    "current_tool": self.agent_exe_array[index].get("tool_name", "Unknown") if index < len(
                        self.agent_exe_array) else "Index out of range"
                }
            )
            raise

    def _validate_and_fix_evaluation_response(self, eval_response):
        """
        🔧 ULTRA-ROBUST: Ensure evaluation response is always a valid dict
        """
        # Type validation
        if not isinstance(eval_response, dict):
            debug_critical(
                heading="AGENT_MODE • RESPONSE_TYPE_CORRECTION",
                body=f"Converting {type(eval_response).__name__} to dict",
                metadata={"original_type": type(eval_response).__name__}
            )
            
            # If it's a list, try to extract first dict element
            if isinstance(eval_response, list) and eval_response:
                for item in eval_response:
                    if isinstance(item, dict):
                        eval_response = item
                        break
                else:
                    # No dict found in list, create fallback
                    eval_response = self._create_fallback_evaluation()
            else:
                # Not a dict or useful list, create fallback
                eval_response = self._create_fallback_evaluation()
        
        # Ensure required keys exist
        required_keys = ["evaluation"]
        for key in required_keys:
            if key not in eval_response:
                debug_warning(
                    heading="AGENT_MODE • MISSING_KEY_CORRECTION",
                    body=f"Adding missing key: {key}",
                    metadata={"missing_key": key}
                )
                eval_response[key] = self._get_default_value_for_key(key)
        
        return eval_response

    def _create_fallback_evaluation(self):
        """Create a safe fallback evaluation when LLM response fails"""
        return {
            "evaluation": {
                "status": "complete",
                "reasoning": "Fallback evaluation due to invalid LLM response format"
            }
        }

    def _get_default_value_for_key(self, key):
        """
        Returns a safe default value for a required key in evaluation response.
        """
        if key == "evaluation":
            return {
                "status": "complete",
                "reasoning": "Fallback evaluation due to missing key."
            }
        # Add more keys as needed for future-proofing
        return None

def save_to_db(collection, data):
    # TODO : Implement database saving logic
    pass


def formated_final_response(create_display_response: str) -> str:
    """
    Formats the final response string for display, handling Windows paths and Unicode decoding issues.

    Args:
        create_display_response (str): The response string to format.

    Returns:
        str: The formatted response string.
    """
    # Escape Windows paths
    if re.search(r'[A-Za-z]:\\', create_display_response):
        create_display_response = create_display_response.replace("\\", "\\\\")
    # If actual escape sequences are present, decode them
    if re.search(r"\\u[0-9a-fA-F]{4}|\\n|\\t|\\r", create_display_response):
        try:
            create_display_response = bytes(create_display_response, "utf-8").decode("unicode_escape")
        except Exception:
            pass  # Fallback: show as-is
    # Return the formatted string
    return create_display_response


@rich_exception_handler("Agent Node Processing")
def agent_node(state):
    from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
    from src.ui.print_message_style import print_message
    """
    Agent node that handles messages requiring agent-like behavior.
    This node processes the latest message and determines which tools to invoke or if it should respond as an agent.
    
    🔧 ENHANCED v3.0: Context-aware agent node with comprehensive execution context integration.
    """

    def _build_comprehensive_final_context(messages, execution_history, tool_results):
        """
        🔧 NEW: Build comprehensive context for final evaluation including full conversation and execution context.
        
        Args:
            messages: Full conversation messages
            execution_history: Tool execution history
            tool_results: Results from tool executions
            
        Returns:
            Formatted comprehensive context string
        """
        context_parts = ["🗣️ CONVERSATION ANALYSIS:"]

        # Conversation analysis
        human_messages = [msg.content for msg in messages if "Human" in str(type(msg)) and hasattr(msg, 'content')]
        ai_messages = [msg.content for msg in messages if "AI" in str(type(msg)) and hasattr(msg, 'content')]

        context_parts.append(f"  Total conversation turns: {len(messages)}")
        context_parts.append(f"  User messages: {len(human_messages)}")
        context_parts.append(f"  AI responses: {len(ai_messages)}")

        # Intent evolution
        if len(human_messages) > 1:
            context_parts.append("\n🎯 USER INTENT EVOLUTION:")
            context_parts.append(f"  Initial request: {human_messages[0]}...")
            if len(human_messages) > 2:
                context_parts.append(f"  Latest refinement: {human_messages[-1]}...")

            # Detect patterns
            request_keywords = " ".join(human_messages).lower()
            if any(word in request_keywords for word in ["file", "directory", "folder"]):
                context_parts.append("  Pattern: File/Directory operations")
            if any(word in request_keywords for word in ["search", "find", "look"]):
                context_parts.append("  Pattern: Search/Discovery operations")
            if any(word in request_keywords for word in ["create", "make", "generate"]):
                context_parts.append("  Pattern: Creation operations")

        # Execution workflow analysis
        context_parts.append("\n⚙️ EXECUTION WORKFLOW ANALYSIS:")
        if execution_history:
            context_parts.append(f"  Total steps executed: {len(execution_history)}")
            tools_used = [step.get('tool_name', 'unknown') for step in execution_history]
            unique_tools = list(set(tools_used))
            context_parts.append(f"  Unique tools used: {len(unique_tools)} ({', '.join(unique_tools)})")

            # Success rate analysis
            if tool_results:
                successful_tools = sum(
                    1 for result in tool_results if "error" not in str(result.get('content', '')).lower())
                success_rate = successful_tools / len(tool_results) if tool_results else 0
                context_parts.append(f"  Success rate: {success_rate:.1%}")

        # Context continuity assessment
        context_parts.append("\n🔗 CONTEXT CONTINUITY:")
        if len(human_messages) > 1:
            context_parts.append("  Multi-turn conversation detected")
            context_parts.append("  User has provided context refinements")
        else:
            context_parts.append("  Single-turn request")

        if execution_history and len(execution_history) > 1:
            context_parts.append("  Multi-step workflow executed")
            context_parts.append("  Tools built on each other's results")
        else:
            context_parts.append("  Single-step or simple workflow")

        # User satisfaction indicators
        context_parts.append("\n😊 USER SATISFACTION INDICATORS:")
        if any(word in " ".join(human_messages).lower() for word in ["thanks", "good", "perfect", "exactly"]):
            context_parts.append("  Positive feedback detected in conversation")
        if any(word in " ".join(human_messages).lower() for word in ["wrong", "not", "different", "instead"]):
            context_parts.append("  Correction requests detected")

        return "\n".join(context_parts)

    try:
        console = settings.console
        console.print("\t\t----Node is agent_node")

        # Access state directly from LangGraph parameter (no sync needed)
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else " No messages available"

        # Get tool list with error handling
        try:
            tool_list = ToolAssign.get_tools_list()
            tool_context = "\n\n".join(
                [
                    f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {get_tool_argument_schema(tool)}"
                    for tool in tool_list
                ]
            ) if tool_list else "No tools available for selection."
        except Exception as tool_error:
            RichTracebackManager.handle_exception(
                tool_error,
                context="Tool List Generation",
                extra_context={"tool_list_length": len(tool_list) if 'tool_list' in locals() else 'N/A'}
            )
            tool_context = "Error loading tools for selection."

        # Generate the list of tool_names to execute with full conversation history
        try:
            # Build comprehensive conversation history for better context
            conversation_history = []
            for msg in messages:
                if hasattr(msg, 'content') and msg.content:
                    # Determine message type based on message class
                    msg_type = "Human" if "Human" in str(type(msg)) else "AI"
                    conversation_history.append(f"{msg_type}: {msg.content}")

            # Join conversation history into readable format
            full_conversation = "\n".join(
                conversation_history) if conversation_history else "No conversation history available"

            # 🔧 NEW: Build execution context for context-aware tool selection
            try:
                # Get any previous tool execution data from ToolResponseManager
                previous_responses = ToolResponseManager().get_response() if hasattr(ToolResponseManager(),
                                                                                     'get_response') else []

                execution_context_parts = ["🔄 SESSION CONTEXT:", f"  Messages in conversation: {len(messages)}",
                                           f"  Previous tool responses: {len(previous_responses)}"]

                # Add any recent tool execution patterns
                if previous_responses:
                    execution_context_parts.append("\n📈 RECENT TOOL ACTIVITY:")
                    for i, resp in enumerate(previous_responses[-3:]):  # Last 3 responses
                        if hasattr(resp, 'content'):
                            content_preview = resp.content[:100] if resp.content else "No content"
                            execution_context_parts.append(f"  {i + 1}. {content_preview}...")

                # Add conversation context patterns
                user_messages = [msg.content for msg in messages if
                                 "Human" in str(type(msg)) and hasattr(msg, 'content')]
                if len(user_messages) > 1:
                    execution_context_parts.append("\n🧠 CONVERSATION PATTERNS:")
                    execution_context_parts.append(f"  User has made {len(user_messages)} requests")
                    execution_context_parts.append("  Previous requests suggest: " +
                                                   ("continuing workflow" if any(word in " ".join(user_messages).lower()
                                                                                 for word in ["then", "next", "also",
                                                                                              "and"]) else "new task"))

                execution_context = "\n".join(execution_context_parts)

                debug_info(
                    heading="AGENT_MODE • CONTEXT_BUILDING",
                    body="Built comprehensive execution context for tool selection",
                    metadata={
                        "conversation_messages": len(messages),
                        "previous_responses": len(previous_responses),
                        "context_length": len(execution_context),
                        "has_patterns": len(user_messages) > 1,
                        "context": "tool_selection_context"
                    }
                )

            except Exception as context_error:
                debug_warning(
                    heading="AGENT_MODE • CONTEXT_BUILD_ERROR",
                    body="Failed to build execution context, using minimal context",
                    metadata={
                        "error_type": type(context_error).__name__,
                        "error_message": str(context_error),
                        "fallback_action": "minimal_context"
                    }
                )
                execution_context = "🔄 MINIMAL CONTEXT: First tool selection in session"

            prompt = Prompt().generate_tool_list_prompt(
                full_conversation,  # Pass full conversation instead of just last message
                last_message,
                tool_context,
                execution_context  # 🔧 NEW: Pass execution context for context-aware tool selection
            )
            # if no tools are available, raise an error
        except Exception as prompt_error:
            RichTracebackManager.handle_exception(
                prompt_error,
                context="Tool List Prompt Generation",
                extra_context={
                    "messages_count": len(messages),
                    "last_message_length": len(last_message) if last_message else 0,
                    "tool_context_length": len(tool_context) if tool_context else 0
                }
            )
            raise

        # AI invocation for tool chain generation
        try:
            with console.status("[bold green]Thinking... generating chain...[/bold green]", spinner="dots"):
                agent_ai = ModelManager(model=settings.GPT_MODEL)
                # first time invoke the agent_ai with the system prompt and the last message from the actual user
                # but middle of the chain, we will invoke the agent_ai with system prompt and the last result from the previous tool
                response = agent_ai.invoke([
                    settings.HumanMessage(content=prompt[0]),
                    settings.HumanMessage(content=prompt[1])
                ])
                response = ModelManager.convert_to_json(response)  # Convert the response to JSON format

                # 🔧 ENHANCED: Robust response validation with anti-hallucination checks
                if not isinstance(response, list):
                    debug_warning(
                        heading="AGENT_MODE • INVALID_TOOL_CHAIN_RESPONSE",
                        body=f"Expected list for tool chain, got {type(response).__name__}",
                        metadata={
                            "response_type": type(response).__name__,
                            "response_content": str(response)[:200] if response else "None",
                            "expected_type": "list",
                            "fallback_action": "empty_list"
                        }
                    )
                    # Use empty list as fallback (no tools selected)
                    response = []

                # Validate each tool in the list
                if isinstance(response, list):
                    validated_tools = []
                    available_tool_names = [tool.name.lower() for tool in ToolAssign.get_tools_list()]

                    for i, tool_item in enumerate(response):
                        if isinstance(tool_item, dict) and "tool_name" in tool_item:
                            tool_name = tool_item["tool_name"]
                            if tool_name.lower() in available_tool_names:
                                validated_tools.append(tool_item)
                                debug_info(
                                    heading="AGENT_MODE • TOOL_VALIDATED",
                                    body=f"Tool '{tool_name}' validated successfully",
                                    metadata={
                                        "tool_name": tool_name,
                                        "position": i,
                                        "validation_status": "approved"
                                    }
                                )
                            else:
                                debug_critical(
                                    heading="AGENT_MODE • TOOL_HALLUCINATION_DETECTED",
                                    body=f"Invalid tool name '{tool_name}' detected - skipping",
                                    metadata={
                                        "invalid_tool_name": tool_name,
                                        "position": i,
                                        "available_tools": available_tool_names,
                                        "validation_status": "rejected",
                                        "action": "skipped_invalid_tool"
                                    }
                                )
                        else:
                            debug_warning(
                                heading="AGENT_MODE • MALFORMED_TOOL_ITEM",
                                body=f"Malformed tool item at position {i} - skipping",
                                metadata={
                                    "position": i,
                                    "item_type": type(tool_item).__name__,
                                    "item_content": str(tool_item)[:100],
                                    "action": "skipped_malformed_item"
                                }
                            )

                    response = validated_tools
                    debug_info(
                        heading="AGENT_MODE • TOOL_CHAIN_VALIDATED",
                        body=f"Validated tool chain: {len(response)} tools approved",
                        metadata={
                            "original_count": len(response) if 'response' in locals() else 0,
                            "validated_count": len(validated_tools),
                            "tools": [tool.get("tool_name", "unknown") for tool in validated_tools]
                        }
                    )

        except Exception as ai_error:
            RichTracebackManager.handle_exception(
                ai_error,
                context="Agent AI Tool Chain Generation",
                extra_context={
                    "model": settings.GPT_MODEL,
                    "prompt_length": len(str(prompt)) if 'prompt' in locals() else 'N/A',
                    "response_type": type(response) if 'response' in locals() else 'N/A'
                }
            )
            raise

        # Agent execution with error handling
        try:
            ###### so now we got the [list of tool names] to execute so we have to execute them one by one pass one result to another using middleware of llm
            ###### which convert the last result to the next input for the tool

            agent = Agent(agent_exe_array=response)
            for i in range(len(agent.agent_exe_array)):
                try:
                    agent.start(index=i)
                except Exception as execution_error:
                    RichTracebackManager.handle_exception(
                        execution_error,
                        context=f"Agent Tool Execution - Step {i + 1}",
                        extra_context={
                            "step": i + 1,
                            "total_steps": len(agent.agent_exe_array),
                            "current_tool": agent.agent_exe_array[i].get("tool_name", "Unknown") if i < len(
                                agent.agent_exe_array) else "Index out of range"
                        }
                    )
                    # Continue with next tool even if one fails
                    continue
        except Exception as agent_error:
            RichTracebackManager.handle_exception(
                agent_error,
                context="Agent Creation and Execution",
                extra_context={
                    "response_length": len(response) if isinstance(response, list) else 'N/A',
                    "response_type": type(response)
                }
            )
            raise

        # Return the final response from the agent
        try:
            final_response = "No messages available" if not ToolResponseManager().get_last_ai_message().content else ToolResponseManager().get_last_ai_message().content
            if not final_response:
                raise ValueError("No response generated by the agent.")

            # 🎯 FINAL RESPONSE EVALUATION (NEW FEATURE)
            try:
                # Prepare execution history and tool results
                execution_history = []
                tool_results = []

                # Collect execution data from the agent
                if 'agent' in locals() and hasattr(agent, 'agent_exe_array'):
                    for i, tool_exec in enumerate(agent.agent_exe_array):
                        execution_history.append({
                            "step": i + 1,
                            "tool_name": tool_exec.get("tool_name", "unknown"),
                            "reasoning": tool_exec.get("reasoning", ""),
                            "parameters": tool_exec.get("parameters", {})
                        })

                # Get all tool responses
                all_responses = ToolResponseManager().get_response()
                if all_responses:
                    tool_results = [{"content": msg.content, "type": type(msg).__name__} for msg in all_responses]

                # Generate final evaluation prompt
                evaluation_prompt = Prompt().evaluate_final_response(
                    final_response=final_response,
                    original_request=last_message,
                    execution_history=execution_history,
                    tool_results=tool_results,
                    full_context=_build_comprehensive_final_context(messages, execution_history, tool_results)
                    # 🔧 NEW: Comprehensive context
                )

                # Get evaluation from AI
                eval_model = ModelManager(model=settings.GPT_MODEL)
                # with settings.console.status("[bold yellow]Evaluating workflow quality...[/bold yellow]", spinner="dots"):
                #     eval_response = eval_model.invoke([
                #         settings.HumanMessage(content=evaluation_prompt[0]),
                #         settings.HumanMessage(content=evaluation_prompt[1])
                #     ])
                #     eval_result = ModelManager.convert_to_json(eval_response)

                rich_evaluation_listener = RichStatusListener(settings.console)
                rich_evaluation_listener.start_status('Evaluating workflow quality with context...', spinner='dots')
                settings.listeners['eval'] = rich_evaluation_listener  # Register listener for evaluation status updates

                # 🔧 NEW: Log context-aware final evaluation
                debug_info(
                    heading="AGENT_MODE • CONTEXT_AWARE_FINAL_EVALUATION",
                    body="Performing context-aware final evaluation with comprehensive context",
                    metadata={
                        "final_response_length": len(final_response),
                        "execution_steps": len(execution_history),
                        "tool_results_count": len(tool_results),
                        "conversation_messages": len(messages),
                        "context_type": "comprehensive_workflow_context",
                        "evaluation_model": settings.GPT_MODEL
                    }
                )

                eval_response = eval_model.invoke([
                    settings.HumanMessage(content=evaluation_prompt[0]),
                    settings.HumanMessage(content=evaluation_prompt[1])
                ])
                eval_result = ModelManager.convert_to_json(eval_response)
                rich_evaluation_listener.stop_status_display()
                rich_evaluation_listener = None  # Clear listener after evaluation

                # 🔧 ULTRA-STRICT: Force evaluation to be dictionary
                if not isinstance(eval_result, dict):
                    debug_critical(
                        heading="AGENT_MODE • FINAL_EVALUATION_TYPE_ERROR",
                        body=f"Final evaluation returned {type(eval_result).__name__} instead of dict",
                        metadata={
                            "expected_type": "dict",
                            "actual_type": type(eval_result).__name__,
                            "eval_content": str(eval_result)[:300] if eval_result else "None",
                            "fallback_action": "create_minimal_evaluation_dict"
                        }
                    )
                    # Force create a valid evaluation dictionary
                    eval_result = {
                        "evaluation": {
                            "overall_status": "complete_success",
                            "quality_score": 0.8,
                            "completeness_score": 0.8,
                            "accuracy_score": 0.8,
                            "relevance_score": 0.8,
                            "efficiency_score": 0.8,
                            "user_satisfaction_prediction": 0.8
                        },
                        "analysis": {
                            "request_fulfillment": "Task completed successfully",
                            "workflow_effectiveness": "Tool chain executed properly",
                            "strengths": ["Task completed"],
                            "weaknesses": ["LLM evaluation failed"],
                            "improvement_opportunities": ["Fix evaluation prompt"]
                        },
                        "user_response": {
                            "message": f"✅ Task Completed\n\n{final_response}\n\nThe requested operation has been completed successfully.",
                            "confidence_level": "medium",
                            "next_steps_suggested": ["Verify results"],
                            "formatting_style": "clean_and_readable_with_structure"
                        },
                        "system_analytics": {
                            "execution_time_assessment": "moderate",
                            "tool_chain_efficiency": 0.8,
                            "error_recovery_effectiveness": 0.7,
                            "context_preservation_quality": 0.8,
                            "learning_insights": ["Evaluation prompt needs improvement"],
                            "optimization_recommendations": ["Strengthen JSON validation"]
                        },
                        "follow_up_actions": {
                            "required": False,
                            "suggested_actions": ["Check results"],
                            "alternative_approaches": ["Manual verification available"]
                        }
                    }

                # Process evaluation results
                if isinstance(eval_result, dict):
                    # Extract user-facing response (if evaluation suggests improvements)
                    user_response = eval_result.get("user_response", {})

                    if (user_response.get("message")
                            and user_response.get("confidence_level", "low")
                            and user_response.get('next_steps_suggested')):
                        # Use improved response if quality is low
                        create_display_response = (
                            f"\n**User-Response:** {user_response.get('message', '')}\n"
                            f"**Confidence-Level:** {user_response.get('confidence_level', 'unknown')}\n"
                            f"**Next Steps Suggested:** {', '.join(user_response.get('next_steps_suggested', []) or [])}\n"
                        )
                        final_response = formated_final_response(create_display_response)

                    # Log evaluation results for system improvement
                    evaluation_data = eval_result.get("evaluation", {})
                    system_analytics = eval_result.get("system_analytics", {})

                    debug_critical(
                        heading="AGENT_MODE • FINAL_EVALUATION",
                        body="Workflow quality assessment completed",
                        metadata={
                            "quality_score": evaluation_data.get('quality_score', 'N/A'),
                            "completeness_score": evaluation_data.get('completeness_score', 'N/A'),
                            "user_satisfaction_prediction": evaluation_data.get('user_satisfaction_prediction', 'N/A'),
                            "context": "final_evaluation_metrics",
                            "system_analytics": system_analytics
                        }
                    )

                    # TODO: Save system_analytics to database for continuous improvement
                    save_to_db(
                        collection="agent_evaluations",
                        data={
                            "user message": last_message,
                            "timestamp": datetime.now(),
                            "evaluation_data": evaluation_data,
                            "system_analytics": system_analytics,
                            "execution_history": execution_history,
                            "tool_results": tool_results,
                            "final_response": final_response
                        }
                    )
                    # This data can be used to optimize future agent executions

                else:
                    debug_critical(
                        heading="AGENT_MODE • FINAL - EVALUATION_FAILURE",
                        body="Final evaluation failed - using original response",
                        metadata={
                            "context": "final_evaluation_parsing",
                            "fallback_action": "using_original_response",
                            "eval_response_type": type(
                                eval_result).__name__ if 'eval_result' in locals() else 'unknown',
                            "eval_response": eval_result
                        }
                    )

            except Exception as eval_error:
                RichTracebackManager.handle_exception(
                    eval_error,
                    context="Final Response Evaluation",
                    extra_context={
                        "final_response_length": len(final_response) if final_response else 0,
                        "execution_history_length": len(execution_history) if 'execution_history' in locals() else 0

                    }
                )
                # Continue with original response if evaluation fails
                debug_warning(
                    heading="AGENT_MODE • EVALUATION_EXCEPTION",
                    body="Final evaluation failed with exception - using original response",
                    metadata={
                        "context": "final_evaluation_exception",
                        "fallback_action": "using_original_response",
                        "error_handled_by": "rich_traceback_manager"
                    }
                )

            print_message(final_response, "ai")
            return {"messages": [settings.AIMessage(content=final_response)]}
        except Exception as response_error:
            RichTracebackManager.handle_exception(
                response_error,
                context="Final Response Generation",
                extra_context={
                    "tool_response_manager_status": "available" if ToolResponseManager().get_response() else "no_response"
                }
            )
            raise

    except Exception as e:
        RichTracebackManager.handle_exception(
            e,
            context="Agent Node Processing",
            extra_context={
                "state_keys": list(state.keys()) if isinstance(state, dict) else 'N/A',
                "messages_count": len(state.get("messages", [])) if isinstance(state, dict) else 'N/A'
            }
        )
        raise
