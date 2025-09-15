"""
This module provides a robust, process-managed wrapper for the browser-use tool.
It uses Python's multiprocessing to run the browser automation in an isolated process,
providing timeout handling, process ID (PID) tracking, and clean termination.
"""
import asyncio
import datetime
import os
import sys
from multiprocessing import Process, Queue
from pathlib import Path
from typing import List, Optional, TypeVar, overload

# Ensure project root is on sys.path for correct module resolution in the subprocess
if __package__ is None:
    p = Path(__file__).resolve()
    project_root = next((parent for parent in p.parents if (parent / 'src').is_dir()),
                        p.parents[4] if len(p.parents) > 4 else p.parent)
    sys.path.insert(0, str(project_root))

# browser dependencies
from browser_use.llm.messages import BaseMessage, UserMessage, SystemMessage, AssistantMessage
from browser_use.llm.views import ChatInvokeCompletion
from browser_use.agent.views import AgentHistoryList
from browser_use import Browser

from pydantic import BaseModel

from src.config import settings
from src.utils.model_manager import ModelManager
from src.ui.diagnostics.debug_helpers import debug_info

T = TypeVar('T', bound=BaseModel)


class BrowserUseCompatibleLLM:
    """Adapter to make ModelManager compatible with browser_use's BaseChatModel protocol"""

    def __init__(self, model_manager: ModelManager):
        self._model_manager = model_manager
        self.model = ModelManager.current_model or 'default'
        self._verified_api_keys = getattr(model_manager, '_verified_api_keys', False)

    @property
    def provider(self) -> str:
        model_name = getattr(self, 'model', 'default').lower()
        if 'gpt' in model_name: return 'openai'
        if 'claude' in model_name: return 'anthropic'
        if 'llama' in model_name or 'mistral' in model_name: return 'ollama'
        return 'unknown'

    @property
    def name(self) -> str:
        return getattr(self, 'model', 'default_model')

    @property
    def model_name(self) -> str:
        return getattr(self, 'model', 'default')

    @overload
    async def ainvoke(self, messages: List[BaseMessage], output_format: None = None) -> ChatInvokeCompletion[str]:
        ...  # pragma: no cover

    @overload
    async def ainvoke(self, messages: List[BaseMessage], output_format: type[T]) -> ChatInvokeCompletion[T]:
        ...  # pragma: no cover

    async def ainvoke(
            self,
            messages: List[BaseMessage],
            output_format: Optional[type[T]] = None
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        """
        Convert browser_use messages to LangChain format and invoke the model
        """
        # Convert browser_use messages to LangChain format
        langchain_messages = []
        for msg in messages:
            # Handle different message types
            if isinstance(msg, UserMessage):
                from langchain_core.messages import HumanMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(HumanMessage(content=content))
            elif isinstance(msg, SystemMessage):
                from langchain_core.messages import SystemMessage as LangChainSystemMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(LangChainSystemMessage(content=content))
            elif isinstance(msg, AssistantMessage):
                from langchain_core.messages import AIMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(AIMessage(content=content or ''))
            else:
                from langchain_core.messages import HumanMessage
                langchain_messages.append(HumanMessage(content=str(msg)))
        try:
            response = await asyncio.get_running_loop().run_in_executor(
                None, self._model_manager.invoke, langchain_messages
            )
            usage = None
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                prompt_tokens = metadata.get('prompt_eval_count', 0) or metadata.get('prompt_tokens', 0)
                completion_tokens = metadata.get('eval_count', 0) or metadata.get('completion_tokens', 0)
                total_tokens = prompt_tokens + completion_tokens
                if prompt_tokens > 0 or completion_tokens > 0:
                    from browser_use.llm.views import ChatInvokeUsage
                    usage = ChatInvokeUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                                            total_tokens=total_tokens)

            if output_format is None:
                completion = response.content if hasattr(response, 'content') else str(response)
                return ChatInvokeCompletion[str](completion=completion, usage=usage)
            else:
                try:
                    if hasattr(response, 'content') and isinstance(response.content, str):
                        import json
                        try:
                            json_content = json.loads(response.content)
                            completion = output_format.model_validate(json_content)
                            return ChatInvokeCompletion[T](completion=completion, usage=usage)
                        except (json.JSONDecodeError, Exception):
                            completion = output_format.model_validate(response.content)
                            return ChatInvokeCompletion[T](completion=completion, usage=usage)
                    else:
                        completion = output_format.model_validate(response.content)
                        return ChatInvokeCompletion[T](completion=completion, usage=usage)
                except Exception:
                    completion = response.content if hasattr(response, 'content') else str(response)
                    return ChatInvokeCompletion[str](completion=completion, usage=usage)
        except Exception as e:
            raise e


def _browser_use_subprocess(queue: Queue, query: str, head_less_mode: bool, log: bool = True, keep_alive: bool = False):
    """
    This target function runs in a separate process to isolate the browser_use tool.
    It places the result in a multiprocessing.Queue for the main process to retrieve.
    """
    if log:
        try:
            log_path = settings.BASE_DIR / "basic_logs" / "browser.txt"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "w", encoding="utf-8", buffering=1)
            log_file.write(f"browser use logs at {datetime.datetime.now()} with query of : {query}\n")
            log_file.flush()
            # Redirect stdout and stderr at the OS level to capture all output
            os.dup2(log_file.fileno(), sys.stdout.fileno())
            os.dup2(log_file.fileno(), sys.stderr.fileno())
            sys.stderr.flush()
            sys.stdout.flush()
        except Exception as e:
            # If redirection fails, we can't log it, but we can try to pass it back.
            sys.stderr.flush()
            sys.stdout.flush()
            queue.put(f"Fatal: Failed to redirect subprocess logs: {e}")
            return

    try:
        from browser_use import Agent

        ## todo ----------- main -------------------------------------------------------------------
        async def main():
            if settings.AIMessage is None and settings.HumanMessage is None:
                from langchain_core.messages import AIMessage as LangChainAIMessage
                from langchain_core.messages import HumanMessage as LangChainHumanMessage
                settings.AIMessage = LangChainAIMessage
                settings.HumanMessage = LangChainHumanMessage


            model_manager = ModelManager(model="moonshotai/kimi-k2-instruct")
            browser_use_llm = BrowserUseCompatibleLLM(model_manager)
            browser = Browser(headless=head_less_mode,
                              keep_alive=keep_alive,
                              record_video_dir=settings.BASE_DIR / "basic_logs" / "browser_videos" if log else None)
            agent = Agent(task=query, llm=browser_use_llm, browser=browser, max_failures=5, max_steps=500,vision_detail_level='high')


            result:AgentHistoryList = await agent.run()
            await agent.close()
            await browser.stop()
            return str(result.final_result())

        result = asyncio.run(main())
        queue.put(result)
    except Exception as e:
        # This error will now be written to the log file due to redirection
        # and also sent back to the parent process.
        error_info = f"Error in browser_use_tool subprocess: {e}"
        print(error_info)  # Print to the redirected stderr
        queue.put(error_info)
    finally:
        # The process is about to exit, OS will handle closing descriptors.
        # No need to restore stdout/stderr as this process is terminating.
        if 'browser' and 'agent' in locals():
            a = locals().get('agent')
            b = locals().get('browser')
            if b is not None and a is not None:
                try:
                    asyncio.run(b.kill())
                    asyncio.run(a.stop())
                except Exception as e:
                    sys.stderr.write(f"Error during cleanup: {e}\n")
        sys.stderr.flush()
        sys.stdout.flush()
        if log and 'log_file' in locals():
            try:
                os.fsync(log_file.fileno())
                log_file.flush()
                log_file.close()
            except:
                pass
        queue.put(f"Process finished to read all the logs of the browser use tool. LOGS are in {log_path.resolve()}" if log else "Process finished.")


def _format_browser_use_result(history: AgentHistoryList) -> str:
    """
    Formats the browser use tool result to better understanding of the agent.
    this is mentioned in the DOC:- https://docs.browser-use.com/customize/agent/output-format
    """

    #todo Access useful information we are not confirm that the final_result is readable str or not if yes then ok else use below to format readable result for ai !! rather than list of dict
    # final result just provide final extracted content so we have to use these to provide much more context ~
    history.urls()  # List of visited URLs
    history.screenshot_paths()  # List of screenshot paths
    history.screenshots()  # List of screenshots as base64 strings
    history.action_names()  # Names of executed actions
    history.extracted_content()  # List of extracted content from all actions
    history.errors()  # List of errors (with None for steps without errors)
    history.model_actions()  # All actions with their parameters
    history.model_outputs()  # All model outputs from history
    history.last_action()  # Last action in history

    # Analysis methods
    history.final_result()  # Get the final extracted content (last step)
    history.is_done()  # Check if agent completed successfully
    history.is_successful()  # Check if agent completed successfully (returns None if not done)
    history.has_errors()  # Check if any errors occurred
    history.model_thoughts()  # Get the agent's reasoning process (AgentBrain objects)
    history.action_results()  # Get all ActionResult objects from history
    history.action_history()  # Get truncated action history with essential fields
    history.number_of_steps()  # Get the number of steps in the history
    history.total_duration_seconds()  # Get total duration of all steps in seconds

    # Structured output (when using output_model_schema)

    final_response_str = history.final_result()
    return final_response_str if final_response_str else "No final result extracted."


class BrowserHandler:
    """
    Handles the execution of the browser_use_tool in a separate, manageable process.
    This class now returns the result directly instead of using a manager.
    """
    time_out: int = settings.BROWSER_USE_TIMEOUT
    enabled: bool = settings.BROWSER_USE_ENABLED
    running_processes: List[Process] = []

    def __init__(self, query: str, head_less_mode: bool = True, log: bool = False, keep_alive: bool = False):
        if not self.enabled:
            raise RuntimeError("Browser use tool is disabled in the settings.")
        self.query = query
        self.head_less_mode = head_less_mode
        self.keep_alive = keep_alive
        self.process_id = None  # not useful for current implementation but kept for compatibility
        self.process: Process | None = None
        self.log = log  # Store log parameter
        self.result = self._run_with_process_management()

    def _run_with_process_management(self) -> str:
        """
        Manages the subprocess and returns the result or error message.
        """
        q = Queue()
        # Pass the log parameter to the subprocess
        self.process = Process(target=_browser_use_subprocess, args=(q, self.query, self.head_less_mode, self.log, self.keep_alive))
        self.running_processes.append(self.process)
        result_str = None

        try:
            self.process.start()
            self.process_id = self.process.pid

            self.process.join(timeout=self.time_out)

            if self.process.is_alive():
                self.process.terminate()
                self.process.join()
                result_str = f"Tool execution timed out after {self.time_out} seconds and was terminated."
            else:
                if not q.empty():
                    result_str = q.get()
                else:
                    result_str = f"Tool process finished with exit code {self.process.exitcode} but returned no result."
        except Exception as e:
            result_str = f"An error occurred while managing the browser tool process: {e}"
            if self.process:
                try:
                    if self.process.is_alive():
                        self.process.terminate()
                        self.process.join()
                except:
                    pass
            self.process_id = None

        return result_str

    @staticmethod
    def _clean_up(process: Process):
        """
        Ensures the process is terminated if still running.
        """
        if process is None:
            return
            
        try:
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
                if process.is_alive():
                    process.kill()
                    process.join()
            debug_info(
                "BROWSER TOOL CLEAN UP",
                f"BrowserHandler: Cleaned up process with PID {process.pid}",
                metadata={
                    "process_id": process.pid,
                    "is_alive": process.is_alive(),
                    "exitcode": process.exitcode
                }
            )
            if process in BrowserHandler.running_processes:
                BrowserHandler.running_processes.remove(process)
        except ProcessLookupError:
            pass
        except OSError:
            pass

    @staticmethod
    def clear_all_processes():
        """
        close all the running subprocesses if any
        :return:
        """
        if hasattr(BrowserHandler, 'running_processes') and BrowserHandler.running_processes:
            # Create a copy of the list to avoid modification during iteration
            processes_to_clean = BrowserHandler.running_processes.copy()
            for proc in processes_to_clean:
                BrowserHandler._clean_up(proc)


def browser_use_tool(query: str, head_less_mode: bool = True, log: bool = True, keep_alive:bool = False) -> str:
    """
    Main entry point for the browser_agent tool.
    Creates an instance of BrowserHandler and returns the result.
    
    Args:
        query: The task/query to be executed by the browser agent
        head_less_mode: Whether to run the browser in headless mode
        log: Whether to enable logging to browser.txt
        keep_alive: Whether to keep the browser alive after execution
        
    Returns:
        str: The result of the browser agent execution or error message
    """
    try:
        handler = BrowserHandler(query=query, head_less_mode=head_less_mode, log=log, keep_alive=keep_alive)
        return handler.result
    except Exception as e:
        error_msg = f"browser_use_tool failed with exception: {e}"
        # Try to log the error if logging is enabled
        if log:
            try:
                log_path = settings.BASE_DIR / "basic_logs" / "browser.txt"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[ERROR] {error_msg}\n")
            except:
                pass  # Ignore logging errors
        return error_msg


if __name__ == '__main__':
    test_query = "/agent you have to open browser in which open nvidia nim api website where you have to get knowledge about the models it offers for developers those model are text-to-text generation capabilities you have to then provide me best model for agentic and bigger context window !! to accomplish best among them you have to keep comparing with each others into ai benchmark websites !! after which you have to just provide me one model name !! who is best agentic model and long context model !! https://build.nvidia.com/explore/discover this is the website url !!"
    print(f"Invoking browser_use_tool for query: '{test_query}'")

    # Run the tool and get the result directly
    final_response = browser_use_tool(query=test_query, head_less_mode=False, log=True)

    print(f"\n--- Standalone Execution Result ---")
    print(final_response)
    print("------------------------------------")
