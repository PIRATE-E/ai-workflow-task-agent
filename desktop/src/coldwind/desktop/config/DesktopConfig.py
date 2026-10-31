from pathlib import Path

from pydantic import Field
from coldwind.core.config.coreSettings import CoreSettinngs


class DesktopConfig(CoreSettinngs):
    """Desktop platform settings — extends CoreSettings with desktop-only config.

    Inherits ALL core fields (socket_host, default_model, etc.)
    Adds desktop-only fields (log_display_mode, paths, etc.)
    Can override core defaults for desktop-specific values
    """

    # ── Desktop Display Settings ──
    log_display_mode: str = "separate_window"
    # Options: "separate_window" | "background" | "file" | "console"

    # ── Advanced Logging Configs ──
    log_text_handler_rotation_size_limit_mb: int = 5 * 1024 * 1024
    log_text_handler_rotation_time_limit_hours: int = 24 * 60 * 60
    log_rotation_always_on: bool = True
    browser_use_log_file: str = "browser.txt"

    # ── Desktop Path Settings ──
    # WHAT: Explicitly declare project_root as a Path field on DesktopConfig.
    # WHY: Handlers and cleanup routines query `ContextRegistry.get().get_settings().project_root`.
    # Purged unused `rag_example_file_path` (pointed to non-existent kafka.pdf),
    # `rag_hash_file_path`, and `rag_triples_file_path` to avoid ghost configs.
    project_root: Path
    png_file_path: Path
    browser_use_user_profile_path: str
    mcp_config_path: Path

    # -- dashboard terminal ---
    dashboard_terminal_bin: str = "auto"
    dashboard_terminal_flags_before: list[str] = Field(default_factory=list)
    dashboard_terminal_flags_after: list[str] = Field(default_factory=list)

    def __init__(self, project_root: Path, **kwargs):
        """
        Initialize DesktopConfig by calculating platform-specific absolute paths
        relative to the provided project_root.
        """
        if project_root is None:
            raise ValueError("project_root cannot be None")
        if not project_root.exists():
            raise ValueError(f"project_root path does not exist: {project_root}")

        # WHAT: Pass project_root into kwargs.
        # WHY: Pydantic BaseSettings consumes kwargs to initialize and validate fields.
        # Storing project_root here guarantees that `self.project_root` exists on the instance.
        kwargs["project_root"] = project_root

        # Calculate dynamic absolute paths based on project_root
        kwargs["png_file_path"] = project_root / "basic_logs" / "graph.png"
        kwargs["browser_use_user_profile_path"] = str(
            project_root / "profiles" / "main_profile"
        )
        kwargs["mcp_config_path"] = project_root / ".mcp.json"

        # Explicitly pass the .env file from the project root using pydantic-settings _env_file
        kwargs["_env_file"] = project_root / ".env"

        super().__init__(**kwargs)
