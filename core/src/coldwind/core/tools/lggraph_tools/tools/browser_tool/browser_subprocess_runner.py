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
import queue
import sys
from pathlib import Path


def main():
    """Main entry point for the subprocess runner."""
    args_dict = {}  # Initialize to avoid reference errors

    # keep_alive monitoring queue (set when keep_alive=True inside the async runner)
    monitor_queue: queue.Queue | None = None

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

        # Import project dependencies
        # Add project root to path
        project_root = Path(__file__).resolve().parents[5]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
        from coldwind.core.utils.model_manager import ModelManager

        # Import the BrowserUseCompatibleLLM from the parent module
        # We need to be careful here - let's inline it to avoid import issues
        from browser_use.llm.messages import BaseMessage, UserMessage, SystemMessage, AssistantMessage
        from browser_use.llm.views import ChatInvokeCompletion
        from pydantic import BaseModel
        from typing import List, Optional, TypeVar, overload

        async def run_browser_agent():
            """Execute the browser agent and return the result."""
            # MIGRATED: the dead `settings.AIMessage = ...` / `settings.HumanMessage = ...`
            # bootstrap block was removed. It was a legacy writer to the deprecated
            # `settings.*` globals, AND it had no backing `settings` import in this
            # subprocess file (would have raised NameError). browser_use ships its
            # own message classes (browser_use.llm.messages), and the
            # BrowserUseCompatibleLLM (events_drivers.py) imports langchain's
            # HumanMessage/AIMessage inline at call sites — so this module has no
            # need to publish langchain message classes onto any global.

            from coldwind.core.tools.lggraph_tools.tools.browser_tool.runner import Runner
            from coldwind.core.tools.lggraph_tools.tools.browser_tool.config import BrowserRequiredConfig
            runner = Runner(BrowserRequiredConfig(
                query=query,
                headless=headless,
                keep_alive=keep_alive,
                file_path=Path(result_file)
            ))

            print("[SUBPROCESS] Creating Agent...")
            sys.stdout.flush()

            result_dict = await runner.run()

            print("[SUBPROCESS] got result from runner into the subprocess runner script", flush=True)

            return result_dict

        # Execute the runner
        try:
            runner = asyncio.Runner()
            main_result = runner.run(run_browser_agent())
            print(f"[SUBPROCESS] Runner completed successfully, extracting results...", flush=True)

            # Safer extraction with explicit error handling
            browser_close = False
            results_list = main_result.get('results', [])

            for item in results_list:
                if item.get('attr_name') == 'handle_keep_alive':
                    result_dict = item.get('result', {})
                    browser_close = result_dict.get('browser_closed', False)
                    print(f"[SUBPROCESS] Found handle_keep_alive result: browser_closed={browser_close}", flush=True)
                    break

            print(f"[SUBPROCESS] Final browser_closed value: {browser_close}", flush=True)

            if browser_close:
                print("[SUBPROCESS] Browser closed successfully, exiting subprocess with code 0...", flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
                sys.exit(0)
            else:
                print("[SUBPROCESS] Browser not closed or keep_alive=False, exiting subprocess with code 0...", flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
                sys.exit(0)

        except Exception as e:
            print(f"[SUBPROCESS] CRITICAL ERROR: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            sys.exit(1)

    except Exception as e:
        print(f"[SUBPROCESS] Unexpected error: {e}", flush=True)


if __name__ == '__main__':
    main()
