from typing import Any


class ContextRegistry:
    """Process-wide singleton holding the active ``RuntimeContextInterface``.

    Lifecycle invariant: exactly one active context once
    :meth:`activate_context` has run at boot. Getting the registry before a
    context is activated is a real boot-order bug, not a recoverable condition
    — callers should not be expected to guard for it.
    """

    # -------------------------------------------------------------------------
    # Class-level state for process-wide runtime context.
    # WHAT CHANGED: Initialized _instance and _active_context directly on the class body.
    # WHY: activate_context and get are classmethods called directly as
    # ContextRegistry.activate_context(ctx) during boot without calling ContextRegistry().
    # Without class-level initialization, accessing cls._active_context raised
    # AttributeError when called prior to any __new__ invocation.
    # -------------------------------------------------------------------------
    _instance: Any = None
    _active_context: Any = None

    def __new__(cls) -> "ContextRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def activate_context(cls, context: Any, force: bool = False) -> None:
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
    def get(cls) -> Any:
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
