from src.models.state import StateAccessor
from src.prompts.agent_mode_prompts import Prompt
from src.tools.lggraph_tools.tool_assign import ToolAssign
from src.utils.argument_schema_util import get_tool_argument_schema
from src.utils.model_manager import ModelManager
from src.config import settings

# 🎨 Rich Traceback Integration
from src.utils.rich_traceback_manager import RichTracebackManager, rich_exception_handler, safe_execute

class Agent:
    """
    Agent class that encapsulates the behavior of an agent node in the LangGraph workflow.
    This class is responsible for processing messages, invoking tools, and generating responses.
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
                            result = ToolResponseManager().get_response()[-1].content
                            ## evaluate the result
                            try:
                                evaluation_prompt = Prompt().evaluate_in_end(tool.name.lower(), result,
                                                                             StateAccessor().get_last_human_message().content)

                                eval_model = ModelManager(model=settings.GPT_MODEL)
                                eval_response = eval_model.invoke([
                                    settings.HumanMessage(content=evaluation_prompt[0]),
                                    settings.HumanMessage(content=evaluation_prompt[1])
                                ])
                                eval_response = ModelManager.convert_to_json(eval_response)
                                evaluation = eval_response.get("evaluation", {})
                                is_success = (evaluation.get("status", "complete") == "complete")

                                if not is_success:
                                    reasoning = evaluation.get("reasoning", "No reasoning provided")
                                    settings.socket_con.send_error(
                                        f"[ERROR] Tool '{tool_name}' execution failed: {reasoning}")

                                    # now fallback logic to handle the failure
                                    fallback = eval_response.get('fallback', {})
                                    if fallback:
                                        fallback_tool_name = fallback.get('tool_name')
                                        fallback_params = fallback.get('parameters', {})

                                        # Find the actual tool object
                                        for fallback_tool in ToolAssign.get_tools_list():
                                            if fallback_tool.name.lower() == fallback_tool_name.lower():
                                                # Invoke the fallback tool with the provided parameters
                                                settings.socket_con().send_error(
                                                    f"[INFO] Invoking fallback tool '{fallback_tool_name}' with parameters: {fallback_params}")
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
                                        "result": str(result)[:200],
                                        "reasoning": reasoning
                                    }
                                )
                                return settings.AIMessage(content=f"Error evaluating tool '{tool_name}': {str(eval_error)}")


                            return settings.AIMessage(content=f"Tool '{tool_name}' executed successfully. Result: {result}")
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
        # # get the tool parameters then pass to the llm
        # for tool_exe in self.agent_exe_array:
        #     if isinstance(tool_exe, dict) and "tool_name" in tool_exe:
        #         # execute the tool with the provided parameters
        #         # get the tool argument schema from the tool list
        #         if tool_exe["tool_name"] in ToolAssign.get_tools_list():
        #             parameters = ToolAssign.get_tools_list()[tool_exe["tool_name"]].args_schema
        #         try:
        #             # get the tool argument schema from llm
        #             prompt = Prompt().generate_parameter_prompt(
        #                 tool_exe["tool_name"],
        #                 parameters,
        #                 "No previous response" if self.agent_exe_array[0] == tool_exe else ToolResponseManager().get_response().settings.AIMessage.content,
        #                 ToolResponseManager().get_response().settings.HumanMessage.content if ToolResponseManager().get_response() else "No previous response"
        #             )
        #             agent_ai = ModelManager(model=settings.GPT_MODEL)
        #             response = agent_ai.invoke([
        #                 settings.HumanMessage(content=prompt[0]),
        #                 settings.HumanMessage(content=prompt[1])
        #             ])
        #             response = ModelManager.convert_to_json(response)  # Convert the response to JSON format
        #             ToolResponseManager().set_response(
        #                 [settings.AIMessage(content=response.get("content", "No content returned from AI."))])
        #             # execute the tool with the provided parameters
        #             result = execute_single_tool(tool_exe)
        #             ToolResponseManager().set_response([result])
        #         except ValueError as ve:
        #             raise ValueError(f"Error generating parameter prompt: {ve}")
        #         except Exception as e:
        #             raise Exception (f"Error generating parameter prompt: {e}")
        #         pass
        #
        #

        try:
            # Find the tool by name with error handling
            tool_found = None
            for tool in ToolAssign.get_tools_list():
                if tool.name.lower() == self.agent_exe_array[index]["tool_name"].lower():
                    tool_found = tool
                    break
            
            if not tool_found:
                available_tools = [tool.name for tool in ToolAssign.get_tools_list()]
                raise ValueError(f"Tool '{self.agent_exe_array[index]['tool_name']}' not found in the tool list. Available tools: {available_tools}")

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
                settings.socket_con.send_error(f"\n\n\n[DEBUG] Tool Name: {self.agent_exe_array[index]['tool_name']} \n")
                settings.socket_con.send_error(f"[DEBUG] Previous AI Response: {previous_ai_response} \n")
                settings.socket_con.send_error(f"[DEBUG] Previous Human Response: {previous_human_response} \n")
                settings.socket_con.send_error(f"[DEBUG] Parameters: {parameters_schema_found_tool} \n\n\n")
            except Exception as debug_error:
                # Don't let debug logging errors break the flow
                print(f"Debug logging error: {debug_error}")

            # Generate prompt with error handling
            try:
                prompt = Prompt().generate_parameter_prompt(
                    self.agent_exe_array[index]["tool_name"],
                    parameters_schema_found_tool,
                    previous_ai_response,
                    previous_human_response
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
                with settings.console.status("[bold green]Thinking... generating parameters...[/bold green]", spinner="dots"):
                    response = agent_ai.invoke([
                        settings.HumanMessage(content=prompt[0]),
                        settings.HumanMessage(content=prompt[1])
                    ])
                    response = ModelManager.convert_to_json(response)
                    if not isinstance(response, dict):
                        raise ValueError("Agent response must be a dictionary with tool execution instructions.")
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
                
                # execute the tool with the provided parameters
                result = execute_single_tool(tool_execution_dict)
                ToolResponseManager().set_response([settings.AIMessage(content=result.content)])
                
            except Exception as execution_error:
                RichTracebackManager.handle_exception(
                    execution_error,
                    context="Tool Execution and Response Setting",
                    extra_context={
                        "tool_execution_dict": str(tool_execution_dict)[:200] if 'tool_execution_dict' in locals() else 'N/A'
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
                    "current_tool": self.agent_exe_array[index].get("tool_name", "Unknown") if index < len(self.agent_exe_array) else "Index out of range"
                }
            )
            raise

    def evaluate(self, response: str) -> str:
        """
        Evaluates the final response from the agent.
        This method can be extended to include additional evaluation logic if needed.
        :param response: The final response from the agent.
        :return: The evaluated response.
        """
        # For now, just return the response as is
        return response


@rich_exception_handler("Agent Node Processing")
def agent_node(state):
    from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
    from src.ui.print_message_style import print_message
    """
    Agent node that handles messages requiring agent-like behavior.
    This node processes the latest message and determines which tools to invoke or if it should respond as an agent.
    """
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

        # Generate the list of tool_names to execute
        try:
            prompt = Prompt().generate_tool_list_prompt(
                messages[-1].content if messages else "No messages available",
                last_message, 
                tool_context
            )
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
                if not isinstance(response, list):
                    raise ValueError("Agent response must be a list of tool execution instructions.")
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
                        context=f"Agent Tool Execution - Step {i+1}",
                        extra_context={
                            "step": i+1,
                            "total_steps": len(agent.agent_exe_array),
                            "current_tool": agent.agent_exe_array[i].get("tool_name", "Unknown") if i < len(agent.agent_exe_array) else "Index out of range"
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
            # suggestion we can add up evaluate llm in the last step to evaluate the final response
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

