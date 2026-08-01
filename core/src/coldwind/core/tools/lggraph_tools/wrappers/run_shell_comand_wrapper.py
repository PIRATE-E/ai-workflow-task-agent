# MIGRATED: direct langchain import for AIMessage (response-construction wrapper).
# Runtime context access (when needed) via ContextRegistry.get().get_settings().
from langchain_core.messages import AIMessage

from coldwind.core.tools.lggraph_tools.tool_response_manager import ToolResponseManager
from coldwind.core.tools.lggraph_tools.tools.run_shell_command_tool import run_shell_command


class ShellCommandWrapper:
    def __init__(
        self, command: str, capture_output: bool = True, creation_flag: bool = False
    ):
        self.command = command
        self.capture_output = capture_output
        self.creation_flag = creation_flag

        self.run_command()

    def run_command(self):
        """
        Executes the shell command stored in `self.command` and appends the result to the ToolResponseManager.

        If the command executes successfully, the output is appended as a response.
        If the command fails, an error message is appended to help diagnose the issue.

        :return: None. The result is managed by ToolResponseManager.
        """
        response = run_shell_command(self.command, self.creation_flag)
        if self.capture_output:
            ToolResponseManager().set_response([AIMessage(content=response)])
        else:
            ToolResponseManager().set_response(
                [
                    AIMessage(
                        content="Command executed without capturing output."
                    )
                ]
            )
