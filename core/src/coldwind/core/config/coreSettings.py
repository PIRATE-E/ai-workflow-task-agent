from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class CoreSettinngs(BaseSettings):
    """Pure configuration for the ColdWind core engine.

    This class defines EVERY configuration key that core needs.
    Platform-specific settings inherit from this and add their own fields.
    Core NEVER imports platform-specific settings classes.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Server Configuration ──
    socket_host: str = "localhost"
    socket_port: int = 5390

    # ── Model Configuration ──
    default_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    cypher_model: str = "deepseek-r1:8b"
    classifier_model: str = "llama3.1:8b"
    gpt_model: str = "openai/gpt-oss-120b"
    kimi_model: str = "moonshotai/kimi-k2.6"
    api_default_api_model: str = "moonshotai/kimi-k2.6"

    # ── API Configuration ──
    openai_api_key: str = "your_openai_api_key_here"
    translation_api_url: str = "http://localhost:5560/translate"

    # ── Task Management ──
    skip_threshold: int = 70

    # ── Logging Configuration ──
    log_level: str = "INFO"
    enable_socket_logging: bool = True
    enable_sound_notifications: bool = True

    # ── Feature Flags ──
    debug: bool = False
    browser_use_enabled: bool = True

    # ── Timeout Settings ──
    openai_timeout: int = 60
    openai_connect_timeout: int = 10

    # ── Neo4j Settings ──
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "your_password_here"
    neo4j_database: str = "neo4j"

    # ── Aura (Neo4j cloud) Settings ──
    # These come from the .env file used by the Aura-hosted Neo4j instance; included
    # here so `extra="forbid"` validation doesn't reject the real .env. Core itself
    # may or may not read them — the driver-build site can use them when needed.
    aura_instanceid: str = ""
    aura_instancename: str = ""

    # ── Release ──
    # Project release tag, surfaced in the .env as `release=...`. Stored but not
    # used by core logic today; available for diagnostics/banner version displays.
    release: str = "1.0.0"

    # ── Concurrency Limits ──
    semaphore_limit_cli: int = 15
    semaphore_limit_api: int = 5
    semaphore_limit_openai: int = 15

    # ── Recursion ──
    recursion_limit: int = 500

    # ── MCP Configuration ──
    mcp_enabled: bool = True
    mcp_host: str = "localhost"
    mcp_port: int = 5000
    mcp_api_key: str = "your_api_key_here"
    mcp_timeout: int = 30
    mcp_start_timeout: int = 30

    # ── Browser Use ──
    browser_use_timeout: int = 1300
