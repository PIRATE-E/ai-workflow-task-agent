import gc
import asyncio
from typing import Any, Optional, Iterator, Union, overload, List, Dict

from openai import OpenAI, AsyncOpenAI

from src.config.settings import OPEN_AI_API_KEY


class OpenAIIntegration:
    """
    Integrates with OpenAI's API for text generation.

    This class provides methods to generate text using OpenAI's models, supporting both streaming and non-streaming responses.
    Enhanced with proper async support for RAG and Neo4j integration.

    IMPORTANT: The API responses from this integration do NOT return a separate 'reasoning' field. If reasoning is required, you must explicitly instruct the model in the system prompt to include reasoning in the content.
    """

    instance: Optional['OpenAIIntegration'] = None
    _async_client: Optional[AsyncOpenAI] = None
    _client_lock = asyncio.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> 'OpenAIIntegration':
        """
        Ensures only one instance of OpenAIIntegration exists (Singleton pattern).
        """
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        """
        Initialize the OpenAIIntegration instance.

        Args:
            api_key (Optional[str]): The OpenAI API key. If not provided, uses OPEN_AI_API_KEY from settings.
            model (Optional[str]): The model name to use. Defaults to 'openai/gpt-oss-120b'.
        """
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        key = api_key or OPEN_AI_API_KEY
        self.model = model or "openai/gpt-oss-120b"
        self.base_url = "https://integrate.api.nvidia.com/v1"

        if not key:
            raise ValueError(
                "API key must be provided either as an argument or through the OPEN_AI_API_KEY environment variable.")

        self.api_key = key
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=key
        )

    async def _get_async_client(self) -> AsyncOpenAI:
        """
        Get or create async client with proper lifecycle management.

        Returns:
            AsyncOpenAI: The async client instance
        """
        async with self._client_lock:
            if self._async_client is None:
                self._async_client = AsyncOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key
                )
        return self._async_client

    async def _close_async_client(self) -> None:
        """
        Properly close the async client.
        """
        async with self._client_lock:
            if self._async_client is not None:
                await self._async_client.close()
                self._async_client = None

    @overload
    def generate_text(self, prompt: str, stream: bool = False) -> str:
        ...

    @overload
    def generate_text(self, prompt: str, stream: bool = True) -> Iterator[str]:
        ...

    @overload
    def generate_text(self, messages: list[dict[str, str]], stream: bool = False) -> str:
        ...

    @overload
    def generate_text(self, messages: list[dict[str, str]], stream: bool = True) -> Iterator[str]:
        ...

    def generate_text(self, prompt: Optional[str] = None, messages: Optional[list[dict[str, str]]] = None,
                      stream: bool = False) -> Union[str, Iterator[str]]:
        """
        Generate text from the OpenAI API.

        Args:
            prompt (str): The prompt to send to the model.
            stream (bool): Whether to stream the response. Defaults to False.
            messages (list[dict[str, str]]): Optional list of message dictionaries for chat completions.

        Returns:
            If stream is True: an iterator of response content strings (NO separate reasoning field).
            If stream is False: a single response content string (NO separate reasoning field).

        NOTE: The response does NOT include a separate 'reasoning' field. If you require reasoning, instruct the model in the system prompt to include reasoning in the content.
        """
        from src.config import settings

        if not prompt and not messages:
            raise ValueError("Prompt cannot be empty.")

        # Enhanced logging for debugging
        if settings.socket_con:
            if prompt:
                settings.socket_con.send_error(f"[DEBUG] OpenAI sync call with prompt: {prompt[:100]}...")
            if messages:
                settings.socket_con.send_error(f"[DEBUG] OpenAI sync call with {len(messages)} messages")

        if prompt or (messages and len(messages) < 2):
            prompt = messages[0]['content'] if messages else prompt
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                top_p=1,
                max_tokens=4096,
                stream=stream,
            )
        else:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                top_p=1,
                max_tokens=4096,
                stream=stream,
            )

        # Enhanced response logging
        if settings.socket_con:
            settings.socket_con.send_error(f"[DEBUG] OpenAI API call completed, stream={stream}")

        if stream:
            return self._handle_streaming_response(completion)
        else:
            return self._handle_non_streaming_response_with_debugging(completion)

    async def generate_text_async(self, prompt: str = None, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Asynchronously generate text from the OpenAI API with enhanced error handling.

        Args:
            prompt (str): The prompt to send to the model.
            messages (Optional[List[Dict[str, str]]]): Optional list of message dictionaries for chat completions.

        Returns:
            str: The generated text response.

        Raises:
            ValueError: If OpenAI integration not initialized or invalid parameters.
            Exception: If API call fails or no content found.
        """
        from src.config import settings

        if not hasattr(self, '_initialized'):
            raise ValueError("OpenAI integration not initialized")

        # Enhanced logging for debugging
        if settings.socket_con:
            if prompt:
                settings.socket_con.send_error(f"[DEBUG] OpenAI async call with prompt")
            if messages:
                settings.socket_con.send_error(f"[DEBUG] OpenAI async call with {len(messages)} messages")

        try:
            async_client = await self._get_async_client()

            # Prepare messages for API call
            if messages and len(messages) > 1:
                api_messages = messages
            elif messages and len(messages) == 1:
                api_messages = [{"role": "user", "content": messages[0]['content']}]
            else:
                api_messages = [{"role": "user", "content": prompt}]

            completion = await async_client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=0.7,
                top_p=1,
                max_tokens=4096,
                stream=False,
            )

            # Enhanced response logging
            # if settings.socket_con:
            #     settings.socket_con.send_error(f"[DEBUG] OpenAI async API call completed successfully")

            return self._handle_non_streaming_response_with_debugging(completion)

        except Exception as e:
            if settings.socket_con:
                settings.socket_con.send_error(f"[ERROR] OpenAI async call failed: {e}")
            raise Exception(f"OpenAI async API call failed: {e}")

    async def generate_text_async_streaming(self, prompt: str, messages: Optional[List[Dict[str, str]]] = None) -> Iterator[str]:
        """
        Asynchronously generate streaming text from the OpenAI API.

        Args:
            prompt (str): The prompt to send to the model.
            messages (Optional[List[Dict[str, str]]]): Optional list of message dictionaries for chat completions.

        Yields:
            str: Content chunks from the streaming response.

        Raises:
            ValueError: If OpenAI integration not initialized or invalid parameters.
            Exception: If API call fails.
        """
        from src.config import settings

        if not hasattr(self, '_initialized'):
            raise ValueError("OpenAI integration not initialized")

        try:
            async_client = await self._get_async_client()

            # Prepare messages for API call
            if messages and len(messages) > 1 and not prompt:
                # If multiple messages are provided, use them directly
                api_messages = messages
            elif messages and len(messages) == 1:
                # If only one message is provided, use its content
                api_messages = [{"role": "user", "content": messages[0]['content']}]
            else:
                # If no messages provided, use the prompt
                if not prompt:
                    raise ValueError("Either prompt or messages must be provided for async streaming.")
                api_messages = [{"role": "user", "content": prompt}]

            completion = await async_client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=0.7,
                top_p=1,
                max_tokens=4096,
                stream=True,
            )

            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            if settings.socket_con:
                settings.socket_con.send_error(f"[ERROR] OpenAI async streaming call failed: {e}")
            raise Exception(f"OpenAI async streaming API call failed: {e}")

    @classmethod
    async def generate_text_async_class(cls, prompt: str) -> str:
        """
        Class method for async text generation (backward compatibility).

        Args:
            prompt (str): The prompt to send to the model.

        Returns:
            str: The generated text response.
        """
        if not cls.instance:
            raise ValueError("OpenAI integration not initialized")

        return await cls.instance.generate_text_async(prompt)

    @staticmethod
    def _handle_streaming_response(completion) -> Iterator[str]:
        """
        Handle streaming responses from the OpenAI API.

        Args:
            completion: The streaming completion object from OpenAI.

        Yields:
            str: Content chunks from the response (NO separate reasoning field).
        """
        for chunk in completion:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                yield content

    @staticmethod
    def _handle_non_streaming_response(completion) -> str:
        """
        Handle non-streaming responses from the OpenAI API.

        Args:
            completion: The completion object from OpenAI.

        Returns:
            str: The content of the response (NO separate reasoning field).

        Raises:
            Exception: If no content is found in the response.
        """
        msg = completion.choices[0].delta
        content = getattr(msg, "content", None)
        if content:
            return content
        else:
            raise Exception("No content found in the response. Please check the prompt and try again.")

    @staticmethod
    def _handle_non_streaming_response_with_debugging(completion) -> str:
        """
        Enhanced response handler with debugging for NVIDIA API compatibility.
        """
        from src.config import settings

        # Try multiple content extraction methods
        if not completion.choices:
            raise Exception("No choices found in API response")

        msg = completion.choices[0].message

        # Method 1: Standard content field
        content = getattr(msg, "content", None)
        if content and content.strip():
            if settings.socket_con:
                settings.socket_con.send_error(f"[DEBUG] Content found via standard method. //{content}//\n")
            return content

        # Method 2: NVIDIA API specific - Check reasoning_content field
        reasoning_content = getattr(msg, "reasoning_content", None)
        if reasoning_content and reasoning_content.strip():
            if settings.socket_con:
                settings.socket_con.send_error(f"[DEBUG] Content found via reasoning_content now the message is [: {completion.choices[0]}]...\n")
            return reasoning_content

        # Method 3: Alternative field names for NVIDIA API
        for field_name in ["text", "message", "response", "output"]:
            alt_content = getattr(msg, field_name, None)
            if alt_content and str(alt_content).strip():
                if settings.socket_con:
                    settings.socket_con.send_error(
                        f"[DEBUG] Content found via {field_name}: {str(alt_content)[:10]}...")
                return str(alt_content)

        # Method 4: Check if message itself is the content
        if hasattr(msg, '__str__') and str(msg).strip():
            content_str = str(msg).strip()
            if settings.socket_con:
                settings.socket_con.send_error(f"[DEBUG] Using message string: {content_str[:10]}...")
            return content_str

        # If all methods fail, provide detailed error
        error_details = {
            "completion_type": type(completion).__name__,
            "choices_count": len(completion.choices) if completion.choices else 0,
            "message_type": type(msg).__name__,
            "message_attributes": [attr for attr in dir(msg) if not attr.startswith('_')],
            "message_content": str(msg) if hasattr(msg, '__str__') else "No string representation",
            "reasoning_content_length": len(reasoning_content) if reasoning_content else 0
        }

        if settings.socket_con:
            settings.socket_con.send_error(f"[ERROR] Complete failure analysis: {error_details}")

        raise Exception(f"No content found in response. Debug info: {error_details}")

    @classmethod
    async def cleanup_async(cls) -> None:
        """
        Clean up async resources.
        """
        if cls.instance:
            await cls.instance._close_async_client()

    @classmethod
    def cleanup(cls) -> None:
        """
        Clean up the OpenAI client instance and release resources.
        Enhanced with async cleanup.
        """
        if cls.instance and hasattr(cls.instance, 'client'):
            try:
                cls.instance.client.close()
            except Exception as e:
                from src.config import settings
                if settings.socket_con:
                    settings.socket_con.send_error(f"Error during OpenAI sync client cleanup: {e}")

        # Schedule async cleanup if needed
        if cls._async_client is not None:
            try:
                # Try to cleanup async client if we're in an async context
                loop = asyncio.get_running_loop()
                loop.create_task(cls.cleanup_async())
            except RuntimeError:
                # Not in async context, skip async cleanup
                pass

        cls.instance = None
        cls._async_client = None
        gc.collect()


if __name__ == '__main__':
    # Example usage
    openai_integration = OpenAIIntegration()
    # print(openai_integration.generate_text("What is the capital of France?", False))  # Non-streaming response
    for part in openai_integration.generate_text("What is the capital of France?", stream=True):
        if part: print(f"{part}", end='', )  # Print each part of the streamed response
