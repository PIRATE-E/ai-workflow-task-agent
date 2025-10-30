"""
Standalone subprocess runner for browser_use tool.
This script is executed as a separate process via subprocess.Popen.

It receives arguments via command line (JSON), executes the browser agent,
and writes the result to a specified output file.

All stdout/stderr is redirected by the parent process via Popen, so Playwright
and Chromium can function normally without os.dup2() interference.
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path


def main():
    """Main entry point for the subprocess runner."""
    args_dict = {}  # Initialize to avoid reference errors


    if len(sys.argv) < 2:
        error_result = {
            "status": "error",
            "error": "No arguments provided to subprocess runner",
            "traceback": ""
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)

    try:
        # Parse arguments from command line
        args_json = sys.argv[1]
        args_dict = json.loads(args_json)

        query = args_dict['query']
        headless = args_dict['headless']
        keep_alive = args_dict['keep_alive']
        result_file = args_dict['result_file']

        print(f"[SUBPROCESS] Starting browser agent with query: {query}")
        print(f"[SUBPROCESS] Headless: {headless}, Keep Alive: {keep_alive}")
        print(f"[SUBPROCESS] Result file: {result_file}")
        sys.stdout.flush()

        # Import browser_use and dependencies (after stdout is already redirected by parent)
        from browser_use import Agent, Browser
        from browser_use.agent.views import AgentHistoryList

        # Import project dependencies
        # Add project root to path
        project_root = Path(__file__).resolve().parents[4]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from src.config import settings
        from src.utils.model_manager import ModelManager

        # Import the BrowserUseCompatibleLLM from the parent module
        # We need to be careful here - let's inline it to avoid import issues
        from browser_use.llm.messages import BaseMessage, UserMessage, SystemMessage, AssistantMessage
        from browser_use.llm.views import ChatInvokeCompletion
        from pydantic import BaseModel
        from typing import List, Optional, TypeVar, overload

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
                ...

            @overload
            async def ainvoke(self, messages: List[BaseMessage], output_format: type[T]) -> ChatInvokeCompletion[T]:
                ...

            async def ainvoke(
                    self,
                    messages: List[BaseMessage],
                    output_format: Optional[type[T]] = None
            ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
                """Convert browser_use messages to LangChain format and invoke the model"""
                langchain_messages = []
                for msg in messages:
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
                            usage = ChatInvokeUsage(
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens
                            )

                    if output_format is None:
                        completion = response.content if hasattr(response, 'content') else str(response)
                        return ChatInvokeCompletion[str](completion=completion, usage=usage)
                    else:
                        try:
                            if hasattr(response, 'content') and isinstance(response.content, str):
                                import json as json_module
                                try:
                                    json_content = json_module.loads(response.content)
                                    completion = output_format.model_validate(json_content)
                                    return ChatInvokeCompletion[T](completion=completion, usage=usage)
                                except (json_module.JSONDecodeError, Exception):
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

        # Run the browser agent
        async def run_browser_agent():
            """Execute the browser agent and return the result."""
            if settings.AIMessage is None and settings.HumanMessage is None:
                from langchain_core.messages import AIMessage as LangChainAIMessage
                from langchain_core.messages import HumanMessage as LangChainHumanMessage
                settings.AIMessage = LangChainAIMessage
                settings.HumanMessage = LangChainHumanMessage

            print("[SUBPROCESS] Initializing ModelManager and BrowserUseCompatibleLLM...")
            sys.stdout.flush()

            model_manager = ModelManager(model="moonshotai/kimi-k2-instruct")
            browser_use_llm = BrowserUseCompatibleLLM(model_manager)

            print("[SUBPROCESS] Starting Browser instance...")
            sys.stdout.flush()

            browser = Browser(
                headless=headless,
                keep_alive=keep_alive,
                record_video_dir=settings.BASE_DIR / "basic_logs" / "browser_videos" if result_file else None,
            )

            print("[SUBPROCESS] Creating Agent...")
            sys.stdout.flush()

            agent = Agent(
                task=query,
                llm=browser_use_llm,
                browser=browser,
                max_failures=5,
                max_steps=500,
                vision_detail_level='high'
            )

            print("[SUBPROCESS] Starting agent execution...")
            sys.stdout.flush()

            try:
                result: AgentHistoryList = await agent.run()
                print("[SUBPROCESS] Agent execution completed!")
                sys.stdout.flush()
            except Exception as agent_error:
                print(f"[SUBPROCESS] CRITICAL: agent.run() failed: {agent_error}")
                print(traceback.format_exc())
                sys.stdout.flush()
                raise

            print("[SUBPROCESS] Closing agent and browser...")
            sys.stdout.flush()

            await agent.close()
            await browser.stop()

            print("[SUBPROCESS] Cleanup completed!")
            sys.stdout.flush()

            final_result = str(result.final_result())
            print(f"[SUBPROCESS] Final result: {final_result}..." if len(final_result) > 200 else f"[SUBPROCESS] Final result: {final_result}")
            sys.stdout.flush()

            return final_result

        # Execute the agent
        try:
            result_str = asyncio.run(run_browser_agent())
        except Exception as asyncio_error:
            print(f"[SUBPROCESS] Asyncio execution failed: {asyncio_error}")
            sys.stdout.flush()
            raise

        # Write success result to file
        result_data = {
            "status": "success",
            "result": result_str
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"[SUBPROCESS] Result written to {result_file}")
        sys.stdout.flush()

        sys.exit(0)

    except Exception as e:
        # Write error result to file
        error_result = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

        print(f"[SUBPROCESS] ERROR: {e}")
        print(traceback.format_exc())
        sys.stderr.flush()

        try:
            # Try to write error to result file
            result_file = args_dict.get('result_file') if args_dict else None
            if result_file:
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(error_result, f, ensure_ascii=False, indent=2)
        except:
            pass  # If we can't write to file, error is already printed to stderr

        sys.exit(1)


if __name__ == '__main__':
    main()
