from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from src.config import settings
from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
from src.tools.lggraph_tools.tools.google_search_tool import search_google_tool
from src.utils.model_manager import ModelManager


class GoogleSearchToolWrapper:
    """
    Wrapper for the Google Search Tool.
    This class is used to manage the response from the Google Search Tool.
    """

    def _parse_response(self) -> BaseMessage | None:
        """
        CONVERT the response from the Google Search Tool into a human-readable format by extracting the snippets and process it using llm.
        :return: Parsed response.
        """
        # Implement parsing logic if needed
        result = search_google_tool(self.query)
        if result is not None:
            # Assuming the result is a dictionary with 'items' key containing search results
            snippets = ""
            if 'items' in result:
                for item in result['items']:
                    title = item.get('title', 'No title')
                    link = item.get('link', 'No link')
                    snippet = item.get('snippet', 'No snippet')
                    snippets += f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n\n"
            # ✅ Use centralized prompt management
            from src.prompts.system_prompts import prompt_manager
            system_prompt = prompt_manager.get_web_search_prompt()
            response = ModelManager(model=settings.CLASSIFIER_MODEL, temperature=0.7, format="json").invoke(
                [HumanMessage(content=system_prompt), HumanMessage(content=snippets)])
        else:
            response = None
        return response

    def __init__(self, query: str):
        """
        Initialize the GoogleSearchToolWrapper with a search query.

        :param query: The search query for the Google Search Tool.
        """
        self.query = query
        # Call the search_google_tool function within the parse method which return the snippets from the search results
        response = self._parse_response()
        if response is not None:
            # If the response is a dictionary, we can assume it's a valid response
            ToolResponseManager().set_response(
                [AIMessage(content=response.content, additional_kwargs=response.additional_kwargs,
                           response_metadata=getattr(response, "response_metadata", {}),
                           id=getattr(response, "id", None))
                 ]
            )
        else:
            # If the response is None, we can set an empty response
            ToolResponseManager().set_response([AIMessage(content="No results found for the query.")])
