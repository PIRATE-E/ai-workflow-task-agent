# this class is used to manage the loading models of ollama
import os
import subprocess
import signal
import atexit
from typing import ClassVar, Optional, Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama

from src.config import settings
# Import socket manager for logging
from .socket_manager import SocketManager

def get_socket_con():
    """Get socket connection only when needed"""
    return SocketManager().get_socket_connection() if settings.ENABLE_SOCKET_LOGGING else None

class ModelManager(ChatOllama):
    """
    Singleton class for managing Ollama model loading and switching.

    Inherits from ChatOllama and provides methods to load, stop, and invoke models.
    Ensures only one model is active at a time and manages the current model state.
    """

    instance : ClassVar[Optional['ModelManager']] = None
    current_model : ClassVar[Optional[str]] = None

    model_list: ClassVar[list[str]] = [settings.DEFAULT_MODEL,
                  settings.CYPHER_MODEL,
                  settings.CLASSIFIER_MODEL]

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
        super().__init__(*args, **kwargs)
        ModelManager.load_model(kwargs.get('model', settings.DEFAULT_MODEL))

    @classmethod
    def cleanup_all_models(cls):
        """
        Public method to explicitly clean up all models.
        Can be called manually or by signal handlers.
        """
        try:
            if cls.current_model:
                socket_con = get_socket_con()
                if socket_con:
                    socket_con.send_error(f"🧹 Cleaning up model: {cls.current_model}")
                cls._stop_model()
                cls.current_model = None
                socket_con = get_socket_con()
                if socket_con:
                    socket_con.send_error("✅ Model cleanup completed")
        except Exception as e:
            socket_con = get_socket_con()
            if socket_con:
                socket_con.send_error(f"❌ Error during model cleanup: {e}")


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
            socket_con = get_socket_con()
            if socket_con:
                socket_con.send_error(f"\t[log]current model {ModelManager.current_model}, loading model {model_name}")
            if not ModelManager.current_model is None:
                if ModelManager.current_model == model_name:
                    socket_con = get_socket_con()
                    if socket_con:
                        socket_con.send_error(f"\t[log]Model {model_name} is already loaded.")
                else:
                    ModelManager._stop_model()
                    ModelManager.current_model = model_name
                    # Here you would add the actual loading logic
            else:
                ModelManager.current_model = model_name
                socket_con = get_socket_con()
                if socket_con:
                    socket_con.send_error(f"Model {model_name} loaded successfully.")

    @classmethod
    def _stop_model(cls):
        """
        Stops the currently running model using the Ollama CLI.
        """
        if cls.current_model:
            socket_con = get_socket_con()
            if socket_con:
                socket_con.send_error(f"Stopping previous model: {cls.current_model}")
            os.system(f"ollama stop {cls.current_model}")
        pass

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
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
        return super().invoke(input=input, config=config, stop=stop, **kwargs)

if __name__ == '__main__':
    # Example usage
    manager = ModelManager(model=settings.DEFAULT_MODEL, temperature=0.7, format="json")
    response = manager.invoke([HumanMessage(content="Hello, how are you?")])
    socket_con = get_socket_con()
    if socket_con:
        socket_con.send_error(response.content if response else "No response received.")
    else:
        print(response.content if response else "No response received.", type(manager))

    manager2 = ModelManager(model=settings.CLASSIFIER_MODEL, temperature=0.5, format="json")
    response = manager2.invoke([HumanMessage(content="What is the capital of France?")])
    socket_con = get_socket_con()
    if socket_con:
        socket_con.send_error(response.content if response else "No response received.")
    else:
        print(response.content if response else "No response received.", type(manager2))

    manager2 = ModelManager(model=settings.CLASSIFIER_MODEL, temperature=0.5, format="json")
    response = manager2.invoke([HumanMessage(content="What is the capital of France?")])
    socket_con = get_socket_con()
    if socket_con:
        socket_con.send_error(response.content if response else "No response received.")
    else:
        print(response.content if response else "No response received.", type(manager2))
