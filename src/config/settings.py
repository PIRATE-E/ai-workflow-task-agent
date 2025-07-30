"""
Configuration settings for AI LLM project.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent  # src directory

# Server configuration
SOCKET_HOST = os.getenv("SOCKET_HOST", "localhost")
SOCKET_PORT = int(os.getenv("SOCKET_PORT", 5390))

# Model configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llava-llama3:latest")
CYPHER_MODEL = os.getenv("CYPHER_MODEL", "deepseek-r1:8b")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "llama3.1:8b")

# API endpoints
TRANSLATION_API_URL = os.getenv("TRANSLATION_API_URL", "http://localhost:5560/translate")

# Default paths
DEFAULT_RAG_EXAMPLE_FILE_PATH = BASE_DIR / "RAG" / "RAG_FILES" / "kafka.pdf"
DEFAULT_RAG_FILES_HASH_TXT_PATH = BASE_DIR / "RAG" / "RAG_FILES" / "processed_hash_chunks.txt"
DEFAULT_RAG_FILES_PROCESSED_TRIPLES_PATH = BASE_DIR / "RAG" / "RAG_FILES" / "processed_triple.json"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Feature flags
ENABLE_SOCKET_LOGGING = os.getenv("ENABLE_SOCKET_LOGGING", "true").lower() == "true"
ENABLE_SOUND_NOTIFICATIONS = os.getenv("ENABLE_SOUND_NOTIFICATIONS", "true").lower() == "true"

# Log display mode options:
# 'separate_window' - Opens log server in separate console window (recommended)
# 'background' - Runs log server in background (logs not visible)
# 'file' - Logs to file (socket_server.log)
# 'console' - Shows logs in same console (can be messy)
LOG_DISPLAY_MODE = os.getenv("LOG_DISPLAY_MODE", "file")

# Development/Production mode
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# SEMAPHORE SETTINGS
SEMAPHORE_CLI = int(os.getenv("SEMAPHORE_LIMIT_CLI", 15))
SEMAPHORE_API = int(os.getenv("SEMAPHORE_LIMIT_API", 5))

# PNG FILE PATH
PNG_FILE_PATH = BASE_DIR.parent / "basic_logs" / "graph.png"

console = None  # Placeholder for console object, to be initialized in main_orchestrator.py

# Message class placeholders - to be initialized in chat_initializer.py
HumanMessage = None  # Placeholder for HumanMessage class
AIMessage = None     # Placeholder for AIMessage class  
BaseMessage = None   # Placeholder for BaseMessage class

if __name__ == '__main__':
    # true
    # print(Path(Path().resolve().parent / "RAG" / "RAG_FILES" / "kafka.pdf").resolve().exists())
    print(Path(Path().resolve().parent / "RAG" / "RAG_FILES" / "kafka.pdf").exists())