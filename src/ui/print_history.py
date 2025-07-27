from langchain_core.messages import HumanMessage, AIMessage

from src.ui.print_message_style import print_message


def print_history(messages):
    for msg in messages:
        if isinstance(msg, HumanMessage):
            print_message(msg.content, sender="user")
        elif isinstance(msg, AIMessage):
            print_message(msg.content, sender="ai")
        else:
            print_message(str(msg), sender="tool")