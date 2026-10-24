from coldwind.core.interfaces import PlatformRuntimeContextInterface


class ContextRegistry:
    """Process-wide singleton holding the active ``RuntimeContextInterface``.

    Lifecycle invariant: exactly one active context once
    :meth:`activate_context` has run at boot. Getting the registry before a
    context is activated is a real boot-order bug, not a recoverable condition
    — callers should not be expected to guard for it.
    """

    # -------------------------------------------------------------------------
    # WHAT CHANGED & WHY:
    # 1. Removed PEP 695 unspecialized class type parameter `[T: Interface]`:
    #    ContextRegistry is a process-wide singleton, not an instantiated generic container.
    #    Calling ContextRegistry.get() without type subscripting left T unbound at the callsite,
    #    causing IDEs (Pylance/Pyright) to drop all type hints to Unknown/Any.
    # 2. Directly typed _active_context and get() return as PlatformRuntimeContextInterface:
    #    Core code only depends on the core interface contract (never concrete platform types).
    #    This gives full IDE auto-completion for all 14 interface methods across the entire repo.
    # 3. Modernized to Python 3.13+ syntax:
    #    Removed legacy typing imports (Any, Optional, Union) in favor of native union syntax (`| None`).
    # -------------------------------------------------------------------------
    _instance: "ContextRegistry | None" = None
    _active_context: PlatformRuntimeContextInterface | None = None

    def __new__(cls) -> "ContextRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def activate_context(
        cls, context: PlatformRuntimeContextInterface, force: bool = False
    ) -> None:
        """Bind the active runtime context. Called once at boot.

        Second-call policy: re-activating over an already-bound context is a
        boot-order / double-init bug and is rejected by default. Pass
        ``force=True`` to replace the active context (use only for tests or
        hot-reload scenarios where you intentionally tear the old context down
        first).
        """
        if cls._active_context is not None and not force:
            raise RuntimeError(
                "ContextRegistry already active. Pass force=True to override."
            )
        cls._active_context = context

    @classmethod
    def get(cls) -> PlatformRuntimeContextInterface:
        """Retrieve the active platform runtime context.

        Guarantees full IDE type hints across Core for all interface methods:
        get_logger(), get_settings(), get_message_display(), register_service(), etc.
        """
        # NOTE: deliberately a real ``RuntimeError`` (not ``assert``) so the
        # invariant survives ``python -O`` (stripped-asserts) production runs.
        if not hasattr(cls, "_active_context"):
            raise RuntimeError("Context registry is not instantiated")
        if cls._active_context is None:
            raise RuntimeError(
                "No active context is set. Call "
                "ContextRegistry.activate_context(...) at boot."
            )
        return cls._active_context
