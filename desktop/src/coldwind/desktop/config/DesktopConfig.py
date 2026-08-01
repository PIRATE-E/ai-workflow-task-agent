from pathlib import Path
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
    png_file_path: Path
    browser_use_user_profile_path: str
    mcp_config_path: Path

    # ── Desktop RAG Paths ──
    rag_example_file_path: Path
    rag_hash_file_path: Path
    rag_triples_file_path: Path

    def __init__(self, project_root: Path, **kwargs):
        """
        Initialize DesktopConfig by calculating platform-specific absolute paths
        relative to the provided project_root.
        """
        if project_root is None:
            raise ValueError("project_root cannot be None")
        if not project_root.exists():
            raise ValueError(f"project_root path does not exist: {project_root}")

        # Calculate dynamic absolute paths based on project_root
        kwargs["png_file_path"] = project_root / "basic_logs" / "graph.png"
        kwargs["browser_use_user_profile_path"] = str(
            project_root / "profiles" / "main_profile"
        )
        kwargs["mcp_config_path"] = project_root / ".mcp.json"

        # RAG files located inside the core package
        core_dir = project_root / "core" / "src" / "coldwind" / "core"
        kwargs["rag_example_file_path"] = core_dir / "RAG" / "RAG_FILES" / "kafka.pdf"
        kwargs["rag_hash_file_path"] = (
            core_dir / "RAG" / "RAG_FILES" / "processed_hash_chunks.txt"
        )
        kwargs["rag_triples_file_path"] = (
            core_dir / "RAG" / "RAG_FILES" / "processed_triple.json"
        )

        # Explicitly pass the .env file from the project root using pydantic-settings _env_file
        kwargs["_env_file"] = project_root / ".env"

        super().__init__(**kwargs)
