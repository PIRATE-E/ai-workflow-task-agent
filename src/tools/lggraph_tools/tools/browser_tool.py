"""
this is to use browser use as a single called tool and the browser use would use our llm and take actions on its own
we have created this because it requires sampling !!
"""

import asyncio
from typing import List, Optional, TypeVar, overload

from browser_use.llm.messages import BaseMessage, UserMessage, SystemMessage, AssistantMessage
from browser_use.llm.views import ChatInvokeCompletion
from pydantic import BaseModel

from src.config import settings
from src.utils.model_manager import ModelManager

T = TypeVar('T', bound=BaseModel)


class BrowserUseCompatibleLLM:
    """Adapter to make ModelManager compatible with browser_use's BaseChatModel protocol"""

    def __init__(self, model_manager: ModelManager):
        self._model_manager = model_manager
        # Get the model name from the model manager's class variable
        self.model = ModelManager.current_model or 'default'
        self._verified_api_keys = getattr(model_manager, '_verified_api_keys', False)
    
    @property
    def provider(self) -> str:
        # Extract provider from model name or use a default
        model_name = getattr(self, 'model', 'default').lower()
        if 'gpt' in model_name:
            return 'openai'
        elif 'claude' in model_name:
            return 'anthropic'
        elif 'llama' in model_name or 'mistral' in model_name:
            return 'ollama'
        else:
            return 'unknown'
    
    @property
    def name(self) -> str:
        return getattr(self, 'model', 'default_model')
    
    @property
    def model_name(self) -> str:
        return getattr(self, 'model', 'default')
    
    @overload
    async def ainvoke(self, messages: List[BaseMessage], output_format: None = None) -> ChatInvokeCompletion[str]: ...
    
    @overload
    async def ainvoke(self, messages: List[BaseMessage], output_format: type[T]) -> ChatInvokeCompletion[T]: ...
    
    async def ainvoke(
        self, 
        messages: List[BaseMessage], 
        output_format: Optional[type[T]] = None
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        """
        Convert browser_use messages to LangChain format and invoke the model
        """
        # Convert browser_use messages to LangChain format
        langchain_messages = []
        for msg in messages:
            # Handle different message types
            if isinstance(msg, UserMessage):
                from langchain_core.messages import HumanMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(HumanMessage(content=content))
            elif isinstance(msg, SystemMessage):
                from langchain_core.messages import SystemMessage as LangChainSystemMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(LangChainSystemMessage(content=content))
            elif isinstance(msg, AssistantMessage):
                from langchain_core.messages import AIMessage
                content = msg.text if hasattr(msg, 'text') else str(msg.content)
                langchain_messages.append(AIMessage(content=content or ""))
            else:
                # Fallback for any other message type
                from langchain_core.messages import HumanMessage
                langchain_messages.append(HumanMessage(content=str(msg)))
        
        # Invoke the model using the model manager
        try:
            # Run the synchronous invoke method in a thread to avoid blocking the event loop
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._model_manager.invoke, langchain_messages
            )
            
            # Create usage information if available
            usage = None
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                # Try to extract token usage information
                prompt_tokens = metadata.get('prompt_eval_count', 0) or metadata.get('prompt_tokens', 0)
                completion_tokens = metadata.get('eval_count', 0) or metadata.get('completion_tokens', 0)
                total_tokens = prompt_tokens + completion_tokens
                
                if prompt_tokens > 0 or completion_tokens > 0:
                    from browser_use.llm.views import ChatInvokeUsage
                    usage = ChatInvokeUsage(
                        prompt_tokens=prompt_tokens,
                        prompt_cached_tokens=metadata.get('prompt_cached_tokens', None),
                        prompt_cache_creation_tokens=metadata.get('prompt_cache_creation_tokens', None),
                        prompt_image_tokens=metadata.get('prompt_image_tokens', None),
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens
                    )
            
            # Convert response back to browser_use format
            if output_format is None:
                # Return string response
                completion = response.content if hasattr(response, 'content') else str(response)
                return ChatInvokeCompletion[str](
                    completion=completion,
                    usage=usage
                )
            else:
                # Try to parse as the specified Pydantic model
                try:
                    # If response.content is a string that looks like JSON, try to parse it
                    if hasattr(response, 'content') and isinstance(response.content, str):
                        import json
                        try:
                            # Try to parse as JSON first
                            json_content = json.loads(response.content)
                            completion = output_format.model_validate(json_content)
                            return ChatInvokeCompletion[T](
                                completion=completion,
                                usage=usage
                            )
                        except (json.JSONDecodeError, Exception):
                            # If that fails, try to validate the string directly
                            completion = output_format.model_validate(response.content)
                            return ChatInvokeCompletion[T](
                                completion=completion,
                                usage=usage
                            )
                    else:
                        completion = output_format.model_validate(response.content)
                        return ChatInvokeCompletion[T](
                            completion=completion,
                            usage=usage
                        )
                except Exception:
                    # Fallback to string if parsing fails
                    completion = response.content if hasattr(response, 'content') else str(response)
                    return ChatInvokeCompletion[str](
                        completion=completion,
                        usage=usage
                    )
        except Exception as e:
            # If invocation fails, re-raise the exception
            raise e


def browser_use_tool(query: str, head_less_mode: bool = True) -> str:
    import asyncio
    from browser_use import Agent

    async def main():
        # Get the current ModelManager instance or create a new one
        try:
            # Try to get existing instance
            if settings.AIMessage is None and settings.HumanMessage is None:
                from langchain_core.messages import AIMessage as LangChainAIMessage
                from langchain_core.messages import HumanMessage as LangChainHumanMessage
                settings.AIMessage = LangChainAIMessage
                settings.HumanMessage = LangChainHumanMessage
            model_manager = ModelManager(model="moonshotai/kimi-k2-instruct")
        except Exception:
            # If that fails, create a new instance with default model
            model_manager = ModelManager(model="moonshotai/kimi-k2-instruct")
        
        # Create adapter for browser_use
        browser_use_llm = BrowserUseCompatibleLLM(model_manager)
        
        agent = Agent(
            task=query, 
            llm=browser_use_llm,
            headless=head_less_mode
        )
        result = await agent.run()
        return str(result)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(main())

if __name__ == '__main__':
    # Example usage of the browser_use_tool function
    query = "open youtube and play some music"
    print(f"Tool invoked for query: {query} : result: {browser_use_tool(query)}")