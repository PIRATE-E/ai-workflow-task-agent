from pathlib import Path

from coldwind.core.config import CoreSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class SlintGuiConfig(CoreSettings):
    """
    platform configuration of Slint-GUi
    """

    # slint got its own platform specific env configuration file
    model_config = SettingsConfigDict(
        env_file=".env.slint",
        env_file_encoding="utf-8",
        extra="ignore",  # Ensures desktop-only .env keys never fail Pydantic validation
    )

    # ── Slint GUI Display & Audio Settings ──
    log_display_mode: str = "slint_gui"
    enable_sound_notifications: bool = False

    # ── TextHandler Rotation Configs (Required by core/system_logging/handlers/handler_base.py) ──
    log_text_handler_rotation_size_limit_mb: int = 5 * 1024 * 1024
    log_text_handler_rotation_time_limit_hours: int = 24 * 60 * 60
    log_rotation_always_on: bool = True
    browser_use_log_file: str = "browser.txt"

    # ── Platform Path Settings (Required by TextHandler, McpConfigFile, BrowserHandler) ──
    project_root: Path
    png_file_path: Path
    browser_use_user_profile_path: str
    mcp_config_path: Path

    # ── Optional Legacy Compatibility (Ifrag.py is imported before Report 04 patch) ──
    DEFAULT_RAG_EXAMPLE_FILE_PATH: str = ""
    DEFAULT_RAG_FILES_HASH_TXT_PATH: str = ""
    DEFAULT_RAG_FILES_PROCESSED_TRIPLES_PATH: str = ""

    # ── Desktop .env Compatibility Fields ──
    dashboard_terminal_bin: str = "auto"
    dashboard_terminal_flags_before: list[str] = Field(default_factory=list)
    dashboard_terminal_flags_after: list[str] = Field(default_factory=list)

    def __init__(self, project_root: Path, **kwargs):
        if project_root is None:
            raise ValueError("project_root cannot be None")
        project_root = Path(project_root).resolve()
        if not project_root.exists():
            raise ValueError(f"project_root path does not exist: {project_root}")

        kwargs["project_root"] = project_root
        kwargs["png_file_path"] = project_root / "basic_logs" / "graph.png"
        kwargs["browser_use_user_profile_path"] = str(
            project_root / "profiles" / "main_profile"
        )
        kwargs["mcp_config_path"] = project_root / ".mcp.json"

        rag_dir = (
            project_root / "core" / "src" / "coldwind" / "core" / "RAG" / "RAG_FILES"
        )
        kwargs.setdefault("DEFAULT_RAG_EXAMPLE_FILE_PATH", str(rag_dir / "kafka.pdf"))
        kwargs.setdefault(
            "DEFAULT_RAG_FILES_HASH_TXT_PATH",
            str(rag_dir / "processed_hash_chunks.txt"),
        )
        kwargs.setdefault(
            "DEFAULT_RAG_FILES_PROCESSED_TRIPLES_PATH",
            str(rag_dir / "processed_triple.json"),
        )
        kwargs["_env_file"] = project_root / ".env.slint"

        super().__init__(**kwargs)
