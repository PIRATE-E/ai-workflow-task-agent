"""
description:
            -this is wrapper of the tool means after the response generate by the tool this will be wrapped around the response
            -this is most likely to the manager of the tools, the calling and the final response from the tool will be handled by this class
"""

from typing import Optional, List

from src.config import settings


class ToolResponseManager:
    instance = None
    _tool_response: Optional[
        List[settings.HumanMessage | settings.AIMessage]] = None  # because the response always be human or AI message list

    def __new__(cls):
        """
        Singleton pattern to ensure only one instance of ToolResponseManager exists.

        :return: The single instance of ToolResponseManager.
        """
        if cls.instance is None:
            cls.instance = super(ToolResponseManager, cls).__new__(cls)
            cls.instance._tool_response = None

        return cls.instance

    def get_response(self):
        """
        Get the response from the tool.

        :return: The response from the tool.
        """
        return self._tool_response

    def set_response(self, new_response: list[settings.HumanMessage | settings.AIMessage]):
        """
        Set a new response for the tool.
        :param new_response: The new response to set for the tool.
        """
        # ✅ PROFESSIONAL ERROR HANDLING: Check for None and empty inputs
        if new_response is None:
            raise ValueError("new_response cannot be None")
        
        if not new_response:
            raise ValueError("new_response cannot be empty")
        
        # ✅ TYPE VALIDATION: Ensure all items are correct message types
        if not all(isinstance(msg, (settings.HumanMessage, settings.AIMessage)) for msg in new_response):
            raise TypeError("All messages must be HumanMessage or AIMessage instances")
        
        if self._tool_response is not None:
            self._tool_response.extend(new_response)
        else:
            self._tool_response = new_response

    def set_response_base(self, new_message: list[settings.BaseMessage], type: int = 0):
        """
        Set a new response for the tool.

        :param new_message: The new message to set for the tool.
        :param type: 0 for HumanMessage, 1 for AIMessage.
        """
        if self._tool_response is None:
            self._tool_response = []
        message_class = settings.HumanMessage if type == 0 else settings.AIMessage if type == 1 else None
        if message_class is None:
            raise ValueError("Invalid type specified. Use 0 for HumanMessage or 1 for AIMessage.")
        self._tool_response.extend(
            message_class(
                content=msg.content,
                additional_kwargs=msg.additional_kwargs,
                response_metadata=getattr(msg, "response_metadata", {}),
                id=getattr(msg, "id", None)
            ) for msg in new_message
        )

    def clear_response(self):
        """
        Clear the current response from the tool.
        """
        self._tool_response = None
