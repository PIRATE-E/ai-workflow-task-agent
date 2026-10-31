from coldwind.core.interfaces.ui_interface import print_message
from coldwind.core.models.state import StateAccessor


def route_message(state):
    """Determines the next node in the workflow based on the classified message type.
    """
    # -------------------------------------------------------------------------
    # WHAT CHANGED & WHY:
    # Replaced console.print with print_message(sender="system") contract.
    # WHY: Purges direct console dependency so node executes cleanly across all
    # platforms (Desktop, GUI, Server) via MessageDisplayInterface.
    # -------------------------------------------------------------------------
    print_message("----Node is router", sender="system")
    state_accessor = StateAccessor()
    # 🔄 Sync StateAccessor with current LangGraph state
    state_accessor.sync_with_langgraph(state)
    message_type = state.get("message_type", "llm")
    return {"message_type": message_type}
