"""
work in progress set up the infrastructure for
slint first bootin up !!

also check the slint gui environment set up or read env.slint-gui file !!
this would be indeed called by slint because the execution started from

slint gui executable !! this is helper class which takes the input from the slint gui

instead of making it act as the main entry point this is basic orchestrator !!

got inputs from slint gui !! directly !! expose well setten up
environment api like

so native rust could make submit their tickets to core
this is more like 3rd wheel bridge class or module !!

"""

# NOTE:
# this is the python based representation which would be happen in the rust !! in order to make the slint-gui work !!
# class SlintEngineBridge:
#     """Thread-safe engine facade held by Rust."""
#
#     def __init__(self, engine: ColdWindEngine, context: SlintRuntimeContext):
#         self._engine = engine
#         self._context = context
#         ## this is also stateless the rust have to maintain the session_state outside !!
#         self._session_state: dict[str, Any] = {"messages": [], "message_type": None}
#
#     def execute_turn(self, user_message: str) -> dict[str, Any]:
#         """Executes a single turn statelessly, shielding Rust from TicketIn boilerplate."""
#         allowed_tools = [
#             getattr(tool, "name", "")
#             for tool in (self._engine.tools or [])
#             if getattr(tool, "name", None)
#         ]
#
#         ticket = TicketIn(
#             ticket_id=f"slint-{uuid.uuid4().hex[:8]}",
#             session_id="slint-session",
#             user_id="slint-user",
#             user_message=user_message,
#             working_state=self._session_state,
#             allowed_tools=allowed_tools,
#             limits={"timeout_seconds": 60},
#         )
#
#         ticket_out = self._engine.process_ticket(ticket)
#         if ticket_out.status == "COMPLETED":
#             self._session_state = ticket_out.new_working_state
#
#         return {
#             "status": ticket_out.status,
#             "transcript": ticket_out.transcript,
#             "error": ticket_out.error_info,
#         }
#
#     def shutdown(self) -> None:
#         self._engine.shutdown()
import sys
from pathlib import Path
from typing import Any

from coldwind.core.engine.coldwind_engine import ColdWindEngine
from coldwind.core.runtime import ContextRegistry
from coldwind.core.system_logging import OnTimeRegistry
from coldwind.slint_gui.config.SlintGuiConfig import SlintGuiConfig
from coldwind.slint_gui.runtime.slint_event_handler import RustGuiEventHandler
from coldwind.slint_gui.runtime.SlintGuiContext import SlintRuntimeContext

project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# called by slint gui at runtime on boot of slint it self !
def boot_slint_py_runtime() -> (
    tuple[ColdWindEngine, SlintRuntimeContext, dict[str, Any]]
):
    """One-shot bootloader called by Rust at application startup."""
    # root is direct current working dir of python file !!
    # 1. Platform configuration & Runtime Context
    config = SlintGuiConfig(project_root=project_root)
    context = SlintRuntimeContext(config)
    ContextRegistry.activate_context(context, force=True)

    # 2. Register native Rust logging sink into Core
    handler_registry = OnTimeRegistry()
    handler_registry.register(RustGuiEventHandler())

    # 3. Boot Core LangGraph Engine
    engine = ColdWindEngine()
    engine.boot()

    # session state initialize to the rust slint !!
    session_state: dict[str, Any] = {"messages": [], "message_type": None}

    return (engine, context, session_state)


if __name__ == "__main__":
    """
    this is intractive environment check up and basic test checking up file
    because the slint-gui could be vary in the installed poth we have to test few scripts or offer installation script
    to run if tests failed to detect that all the required configuration is satisfy or not for slint-gui !!
    """
    print("null")
