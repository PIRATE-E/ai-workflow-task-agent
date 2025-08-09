import json
import os
import subprocess
import time
from typing import ClassVar, Optional, Any, Iterator, Union

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessageChunk, BaseMessage, AIMessageChunk
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama

from src.config import settings
from src.utils.open_ai_integration import OpenAIIntegration


class ModelManager(ChatOllama):
    """
    Singleton class for managing Ollama model loading and switching.

    Inherits from ChatOllama and provides methods to load, stop, and invoke models.
    Ensures only one model is active at a time and manages the current model state.
    """

    instance: ClassVar[Optional['ModelManager']] = None
    current_model: ClassVar[Optional[str]] = None
    _openai_integration: ClassVar[Optional[OpenAIIntegration]] = None
    _is_openai_mode: ClassVar[bool] = False

    model_list: ClassVar[list[str]] = [settings.DEFAULT_MODEL,
                                       settings.CYPHER_MODEL,
                                       settings.CLASSIFIER_MODEL]
    api_model_list: ClassVar[list[str]] = [settings.GPT_MODEL]

    def __new__(cls, *args: Any, **kwargs: Any) -> 'ModelManager':
        """
        Ensures only one instance of ModelManager exists (Singleton pattern).
        """
        if cls.instance is None:
            cls.instance = super(ModelManager, cls).__new__(cls)
        return cls.instance

    def __init__(self, *args, **kwargs):
        """
        Initializes the ModelManager and loads the specified model.

        Args:
            model (str): The model to load (default is config.DEFAULT_MODEL).
            Other keyword arguments are passed to the parent ChatOllama class.
        """
        if getattr(self, "_initialized", False):
            # If instance already exists, skip re-initialization
            return

        self._initialized = True

        # Check if this should use OpenAI integration
        if kwargs.get("model") in ModelManager.api_model_list:
            # For OpenAI models, create integration and mark as OpenAI mode
            ModelManager._openai_integration = OpenAIIntegration(
                api_key=kwargs.get("api_key", settings.OPEN_AI_API_KEY),
                model=kwargs.get("model", settings.GPT_MODEL)
            )
            ModelManager._is_openai_mode = True
            # Still initialize ChatOllama with a default model to avoid issues
            super().__init__(model=settings.DEFAULT_MODEL, **{k: v for k, v in kwargs.items() if k != 'model'})
        else:
            # Initialize as regular ChatOllama instance
            ModelManager._openai_integration = None
            ModelManager._is_openai_mode = False
            super().__init__(*args, **kwargs)
            ModelManager.load_model(kwargs.get('model', settings.DEFAULT_MODEL))

    @property
    def openai_chat(self) -> Optional[OpenAIIntegration]:
        """Property to access the OpenAI integration."""
        return ModelManager._openai_integration

    @classmethod
    def cleanup_all_models(cls):
        """
        Public method to explicitly clean up all models.
        Can be called manually or by signal handlers.
        """
        try:
            if cls._openai_integration is not None:
                if settings.socket_con:
                    settings.socket_con.send_error("≡ƒº╣ Cleaning up OpenAI integration")
                OpenAIIntegration.cleanup()
                cls._openai_integration = None
                cls._is_openai_mode = False
                if settings.socket_con:
                    settings.socket_con.send_error("Γ£à OpenAI integration cleanup completed")
                    return  # Exit early if OpenAI integration is cleaned up
        except Exception as e:
            if settings.socket_con:
                settings.socket_con.send_error(f"Γ¥î Error during OpenAI integration cleanup: {e}")
        try:
            if cls.current_model:
                if settings.socket_con:
                    settings.socket_con.send_error(f"≡ƒº╣ Cleaning up model: {cls.current_model}")
                cls._stop_model()
                cls.current_model = None
                if settings.socket_con:
                    settings.socket_con.send_error("Γ£à Model cleanup completed")
        except Exception as e:
            if settings.socket_con:
                settings.socket_con.send_error(f"Γ¥î Error during model cleanup: {e}")

    @staticmethod
    def load_model(model_name: str):
        """
        Loads the specified model if available and manages switching between models.

        Args:
            model_name (str): The name of the model to load.

        Raises:
            ValueError: If the model_name is not in the list of available models.
        """
        running_one = subprocess.Popen("ollama ps", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r_read = running_one.stdout.read().decode('utf-8')

        for i in ModelManager.model_list:
            if r_read.__contains__(i):
                ModelManager.current_model = i

        if model_name not in ModelManager.model_list:
            raise ValueError(f"Model {model_name} is not available. Available models: {ModelManager.model_list}")
        else:
            if settings.socket_con:
                settings.socket_con.send_error(
                    f"\t[log]current model {ModelManager.current_model}, loading model {model_name}")
            if not ModelManager.current_model is None:
                if ModelManager.current_model == model_name:
                    if settings.socket_con:
                        settings.socket_con.send_error(f"\t[log]Model {model_name} is already loaded.")
                else:
                    ModelManager._stop_model()
                    ModelManager.current_model = model_name
                    # Here you would add the actual loading logic
            else:
                ModelManager.current_model = model_name
                if settings.socket_con:
                    settings.socket_con.send_error(f"Model {model_name} loaded successfully.")

    @classmethod
    def _stop_model(cls):
        """
        Stops the currently running model using the Ollama CLI.
        """
        if cls.current_model:
            if settings.socket_con:
                settings.socket_con.send_error(f"Stopping previous model: {cls.current_model}")
            os.system(f"ollama stop {cls.current_model}")
        pass

    def invoke(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> BaseMessage | Any:
        """
        Invokes the loaded model with the given input.

        Args:
            input (LanguageModelInput): The input message(s) for the model.
            config (Optional[RunnableConfig]): Optional configuration for the run.
            stop (Optional[list[str]]): Optional stop sequences.
            **kwargs: Additional keyword arguments.

        Returns:
            BaseMessage: The response from the model.
        """
        if ModelManager._is_openai_mode and ModelManager._openai_integration is not None:
            # If using OpenAIIntegration, delegate to it
            # if input is a list, treat the first element as system message then the rest as user messages
            if isinstance(input, list) and len(input) > 0:
                system_message = input[0].content if hasattr(input[0], 'content') else str(input[0])
                user_messages = [msg.content if hasattr(msg, 'content') else str(msg) for msg in input[1:]]
                messages = ([{"role": "system", "content": system_message}] +
                            [{"role": "user", "content": msg} for msg in user_messages])
                open_ai_response = ModelManager._openai_integration.generate_text(messages=messages)
            else:
                # If input is not a list, treat it as a single user message
                open_ai_response = ModelManager._openai_integration.generate_text(
                    prompt=getattr(input, 'content', str(input))
                )
            return settings.AIMessage(content=str(open_ai_response))
        else:
            return super().invoke(input=input, config=config, stop=stop, **kwargs)

    def stream(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> Iterator[BaseMessageChunk]:
        """
        Streams the response from the model for the given input.

        Args:
            input (LanguageModelInput): The input message(s) for the model.
            config (Optional[RunnableConfig]): Optional configuration for the run.
            stop (Optional[list[str]]): Optional stop sequences.
            **kwargs: Additional keyword arguments.

        Returns:
            Iterator[BaseMessageChunk]: An iterator yielding message chunks.
        """
        if ModelManager._is_openai_mode and ModelManager._openai_integration is not None:
            # If using OpenAIIntegration, delegate to it
            open_ai_response = ModelManager._openai_integration.generate_text(
                prompt=getattr(input[0], 'content')
                if isinstance(input, list) and not isinstance(input[0], dict) else input.content,
                stream=True,
            )
            return self._normalize_streaming_response(open_ai_response)
        return super().stream(input=input, config=config, stop=stop, **kwargs)

    @classmethod
    def _normalize_streaming_response(cls, response_to_parse: Iterator[str]) -> Iterator[AIMessageChunk]:
        """
        Normalizes the streaming response from OpenAIIntegration to AIMessageChunk format.

        Args:
            response_to_parse (Iterator[str]): The streaming response generator (yields content strings).

        Returns:
            Iterator[AIMessageChunk]: An iterator yielding AIMessageChunk objects with content only.
        """
        last_time = time.time()
        buffer = ""
        for chunk in response_to_parse:
            buffer += chunk
            current_time = time.time()
            if current_time - last_time >= 0.1:  # Yield every 100 milliseconds
                if buffer:
                    yield AIMessageChunk(content=buffer)
                    buffer = ""
                last_time = current_time
        if buffer:
            yield AIMessageChunk(content=buffer)

    @classmethod
    def convert_to_json(cls, response: Union[str, dict, list, BaseMessage]) -> Union[dict, list]:
        """
        🔧 ENHANCED: JSON extraction with proper type handling for async responses and reasoning content
        
        Args:
            response: Response to convert (can be string, dict, list, or BaseMessage)

        Returns:
            dict or list: The extracted JSON object or fallback structure
        """
        # Handle already parsed objects (most common case for async responses)
        if isinstance(response, (dict, list)):
            return response
        
        # Handle BaseMessage objects with priority-based content extraction
        if isinstance(response, BaseMessage):
            content = response.content
        else:
            content = str(response)

        # Handle empty or None responses
        if not content or content.strip() == "":
            return {"content": "empty_response"}

        # Try 1: Direct JSON parsing
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try 2: Extract from markdown code blocks
        import re
        markdown_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
        markdown_match = re.search(markdown_pattern, content, re.DOTALL)
        if markdown_match:
            try:
                return json.loads(markdown_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try 3: Find JSON objects or arrays with proper brace/bracket matching
        json_objects = []
        
        # Look for JSON arrays first (priority for RAG triple extraction)
        bracket_count = 0
        start_pos = -1
        for i, char in enumerate(content):
            if char == '[':
                if bracket_count == 0:
                    start_pos = i
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0 and start_pos != -1:
                    try:
                        json_str = content[start_pos:i + 1]
                        parsed = json.loads(json_str)
                        json_objects.append(parsed)
                    except json.JSONDecodeError:
                        pass
                    start_pos = -1

        # If no arrays found, look for JSON objects
        if not json_objects:
            brace_count = 0
            start_pos = -1
            for i, char in enumerate(content):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        try:
                            json_str = content[start_pos:i + 1]
                            parsed = json.loads(json_str)
                            json_objects.append(parsed)
                        except json.JSONDecodeError:
                            pass
                        start_pos = -1

        # Return first valid JSON object found (prefer arrays for RAG)
        if json_objects:
            return json_objects[0]

        # Fallback: wrap content
        if settings.socket_con:
            settings.socket_con.send_error("[warning] json conversion failed, returning content as fallback : " + content[:100])
        return {"content": content}
