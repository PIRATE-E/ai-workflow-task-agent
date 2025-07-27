from langchain_core.tools.structured import StructuredTool


class ToolAssign(StructuredTool):
    _tool_list = []

    def __init__(self, name: str, description: str, func=None, args_schema=None):
        """
        Initialize the ToolAssign with a name and description.

        :param name: The name of the tool.
        :param description: A brief description of what the tool does.
        """
        super().__init__(name=name, description=description, function=func, args_schema=args_schema)
        self.name = name
        self.description = description
        self.func = func
        self.args_schema = args_schema

    @classmethod
    def set_tools_list(cls, tools_list: list):
        """
        Set the list of tools available for selection.

        :param tools_list: List of tool instances to be used in the tool selection process.
        """
        ToolAssign._tools_list = tools_list

    @classmethod
    def get_tools_list(cls):
        """
        Get the list of tools available for selection.

        :return: List of tool instances.
        """
        return cls._tools_list
