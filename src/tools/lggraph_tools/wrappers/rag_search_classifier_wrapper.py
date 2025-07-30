from src.config import settings


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
        from src.tools.lggraph_tools.tools.rag_search_classifier_tool import rag_search_classifier_tool
        from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
        
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
                ai_message = settings.AIMessage(content=result)
                ToolResponseManager().set_response([ai_message])
            else:
                # Handle None or empty result
                error_message = f"[ERROR] RAG search returned no results for query: '{self.query}'"
                print(f"[ERROR] Empty result from RAG tool for query: '{self.query}'")
                ai_message = settings.AIMessage(content=error_message)
                ToolResponseManager().set_response([ai_message])
                
        except Exception as e:
            # ✅ ENHANCED ERROR CATCHING WITH STACK TRACE
            import traceback
            error_details = traceback.format_exc()
            error_message = f"[ERROR] Exception during RAG search for '{self.query}': {str(e)}"
            
            print(f"[ERROR] Full traceback:\n{error_details}")
            ai_message = settings.AIMessage(content=error_message)
            ToolResponseManager().set_response([ai_message])
