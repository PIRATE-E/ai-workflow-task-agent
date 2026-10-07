from langchain_core.messages import AIMessage

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry


class RagSearchClassifierWrapper:
    """
    A wrapper for the RAG Search Classifier.
    This class is used to handle the RAG Search Classifier functionality.
    """

    def __init__(self, query):
        """
        Initialize the RagSearchClassifierWrapper with a search query.
        :param query: The search query for the RAG Search Classifier Tool.
        """
        from coldwind.core.tools.lggraph_tools.tools.rag_search_classifier_tool import (
            rag_search_classifier_tool,
        )
        from coldwind.core.tools.lggraph_tools.tool_response_manager import ToolResponseManager

        self.query = query

        try:
            # Call the rag_search_classifier_tool function with the query and get the result
            result = rag_search_classifier_tool(self.query)

            # ✅ ENHANCED ERROR HANDLING WITH DETAILED LOGGING
            if result is not None and isinstance(result, str) and result.strip():
                # Check if result contains error message
                if result.startswith("[ERROR]"):
                    print(f"[WARNING] RAG tool returned error: {result}")

                # Create AIMessage with the string result
                ai_message = AIMessage(content=result)
                ToolResponseManager().set_response([ai_message])
            else:
                # Handle None or empty result
                error_message = (
                    f"[ERROR] RAG search returned no results for query: '{self.query}'"
                )
                print(f"[ERROR] Empty result from RAG tool for query: '{self.query}'")
                ai_message = AIMessage(content=error_message)
                ToolResponseManager().set_response([ai_message])

        except Exception as e:
            # WHAT: Route exception through ContextRegistry error handler.
            # WHY: Preserves Layering Invariant by eliminating direct desktop import.
            import traceback
            from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

            error_details = traceback.format_exc()
            try:
                ContextRegistry.get().get_error_handler().handle_exception(
                    e,
                    context="RAG Search Classifier Wrapper Execution",
                    extra_context={"traceback": error_details},
                )
            except Exception:
                pass

            ai_message = AIMessage(
                content=f"[ERROR] An error occurred while executing the RAG search: {str(e)} full traceback: {error_details}"
            )
            ToolResponseManager().set_response([ai_message])
