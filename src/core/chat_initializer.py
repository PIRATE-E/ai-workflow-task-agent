import gc
import json
import platform
from threading import Thread

from src.config import settings
from langgraph.graph.state import CompiledStateGraph
from rich import console, prompt, inspect

from src.config.settings import PNG_FILE_PATH
from src.models.state import StateAccessor, State
from src.ui.print_message_style import print_message
from src.utils.socket_manager import SocketManager


class ChatInitializer:
    def __init__(self):
        self.break_loop = None  # This will be used to break the chat loop
        self._exit_function = None
        self.os = platform.system()
        self.console = console.Console()
        self._set_core_classes()  # set core classes for messages
        # Initialize state with empty messages and no message type
        self._state: State = {"messages": [], "message_type": None}
        self.state_accessor = StateAccessor()
        self.graph = None  # graph.compile() will be called later
        self.tools = None


    def _set_core_classes(self):
        # Import here to avoid circular imports
        from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
        import sentry_sdk
        sentry_sdk.init(
            dsn="https://1df631d527493b6f96c55ffe9d42cc32@o4509761254981632.ingest.us.sentry.io/4509761281458176",
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
        
        # we must set the console for rich console to use it in different classes to the settings
        settings.console = self.console
        
        # Set message classes for centralized access
        settings.HumanMessage = HumanMessage
        settings.AIMessage = AIMessage
        settings.BaseMessage = BaseMessage
        # Set the socket connection for logging
        settings.socket_con = SocketManager.get_socket_con()

    def set_graph(self, graph):
        if not isinstance(graph, CompiledStateGraph):
            raise ValueError("Provided graph is not a valid CompiledStateGraph instance")
        self.graph = graph
        return self

    def set_exit(self, func):
        if hasattr(func, '__call__'):
            self._exit_function = func
            return self
        else:
            raise ValueError("Provided exit function is not callable")

    def on_exit(self):
        """
        Handles cleanup and saving of conversation history when the chatbot session ends.
        """
        self.console.print("\t\t----[bold][red]Node is onExit[/bold][red]")
        # 🔄 Sync StateAccessor with final LangGraph state
        self.state_accessor.sync_with_langgraph(self._state)
        history = []
        messages = self.state_accessor.get_messages()
        for msg in messages:
            history.append(
                {
                    "type": msg.type,
                    "content": msg.content
                }
            )
        json.dump(history, open("conversation_history.json", "w"), indent=2)
        # Let ChatDestructor handle socket cleanup - don't close prematurely
        # run the exit function if it is set in the another thread
        if self._exit_function:
            # run the exit function in another thread
            t = Thread(target=self._exit_function)
            t.start()
        else:
            self.console.print("[bold red]No exit function set. Exiting without cleanup.[/bold red]")
        # print the final state for debugging
        inspect(self._state)
        return {"messages": [settings.AIMessage(content="Thank you for using the LangGraph Chatbot!")]}

    def save_graph_png(self):
        import os
        if self.graph is None:
            raise ValueError("Graph is not initialized. Please compile the graph first.")
        path = PNG_FILE_PATH
        with open(path, "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())
        if self.os == 'Linux':

            os.system(f'xdg-open {path}')
        elif self.os == 'Darwin':

            os.system(f'open {path}')
        elif self.os == 'Windows':
            os.startfile(path)
        return self

    def tools_register(self):
        """
        Register tools for the chat application.
        This method can be extended to register any tools needed for the chat.
        """
        from src.tools.lggraph_tools.tool_assign import ToolAssign
        from src.tools.lggraph_tools.wrappers.google_wrapper import GoogleSearchToolWrapper
        from src.tools.lggraph_tools.wrappers.translate_wrapper import TranslateToolWrapper
        from src.tools.lggraph_tools.wrappers.rag_search_classifier_wrapper import RagSearchClassifierWrapper
        # schema
        from src.tools.lggraph_tools.tool_schemas.tools_structured_classes import google_search, rag_search_message, \
            TranslationMessage
        tools = [
            # google search tool assigning
            ToolAssign(func=GoogleSearchToolWrapper,
                       name="GoogleSearch",
                       description="For general web searches (recent info, facts, news).",
                       args_schema=google_search, ),
            # rag search tool assigning
            ToolAssign(func=RagSearchClassifierWrapper,
                       name="RAGSearch",
                       description="For searching the knowledge base (RAG search).",
                       args_schema=rag_search_message, ),
            # translate tool assigning
            ToolAssign(func=TranslateToolWrapper,
                       name="Translatetool",
                       description="For translating messages into different languages.",
                       args_schema=TranslationMessage, )
        ]
        ToolAssign.set_tools_list(tools)
        self.tools = ToolAssign.get_tools_list()
        return self

    def run_chat(self):
        # make sure all the fields are initialized
        if not self._state or not self.graph or not self.tools:
            raise ValueError("Chat is not properly initialized. Please ensure all components are set up.")

        user_input = prompt.Prompt.ask("[bold cyan]You[/bold cyan]", default="", show_default=False)
        if user_input.lower() == "exit":
            self.console.print("[bold red]Exiting the chat...[/bold red]")
            self.on_exit()
            self.break_loop = True
        else:
            self._state["messages"].append(settings.HumanMessage(content=user_input))
            print_message(user_input, sender="user")
            self._state = self.graph.invoke(self._state)
            self.state_accessor.sync_with_langgraph(self._state)
        gc.collect()
