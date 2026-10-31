from typing import Any, Callable

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry


class ChatDestructor:
    """Handles graceful cleanup of chat and engine resources upon shutdown.

    Ensures that background models, MCP client subprocesses, and browser
    sessions are cleanly released. Emits structured diagnostics through
    the active platform logger and dispatches any hook failures to
    the runtime ExceptionHandlerInterface.
    """

    _cleanup_executed: bool = False
    _all_functions: list[Callable[[], Any]] = []

    @classmethod
    def add_destroyer_function(cls, function: Callable[[], Any]) -> None:
        """Add a cleanup function to be called during the cleanup process.

        :param function: A callable that performs resource cleanup.
        """
        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Separated callable validation from duplicate-membership check.
        # WHY: Registration is idempotent; prevents false ValueError crashes
        # when both engine boot and orchestrator register the same hook.
        # ---------------------------------------------------------------------
        if not function or not callable(function):
            raise ValueError("Provided function is not callable")
        if function not in cls._all_functions:
            cls._all_functions.append(function)

    @classmethod
    def call_all_cleanup_functions(cls) -> None:
        """Execute all registered cleanup functions sequentially.

        Guarantees that an exception in one cleanup hook does not prevent
        remaining hooks from executing. Dispatches diagnostic logs and
        tracebacks via the active runtime context.
        """
        if cls._cleanup_executed:
            return

        cls._cleanup_executed = True

        try:
            context = ContextRegistry.get()
            logger = context.get_logger()
            error_handler = context.get_error_handler()
        except Exception:
            context = logger = error_handler = None

        if len(cls._all_functions) == 0:
            if logger:
                logger.log_info("CLEANUP • EMPTY", "No cleanup functions registered.")
            return

        if logger:
            logger.log_info("CLEANUP • START", "Starting resource cleanup process.")

        terminated_count = 0
        for func in cls._all_functions:
            func_name = getattr(func, "__name__", str(func))
            try:
                if callable(func):
                    if logger:
                        logger.log_info(
                            "CLEANUP • HOOK_RUN",
                            f"Executing cleanup: {func_name}",
                            metadata={"hook": func_name},
                        )
                    func()
                    terminated_count += 1
                else:
                    if logger:
                        logger.log_warning(
                            "CLEANUP • INVALID",
                            f"Function {func} is not callable, skipping.",
                        )
            except Exception as e:
                # -------------------------------------------------------------
                # WHAT CHANGED & WHY:
                # Dispatched cleanup exception to ContextRegistry host error handler.
                # WHY: Replaced legacy raw-socket sends and unformatted print statements.
                # Passes live Exception object to host error handler for rich diagnostics
                # while emitting structured log events to OnTimeRegistry.
                # -------------------------------------------------------------
                if error_handler:
                    try:
                        error_handler.handle_exception(
                            e,
                            context=f"ChatDestructor Cleanup: {func_name}",
                            extra_context={"hook": func_name, "phase": "teardown"},
                        )
                    except Exception:
                        pass

                if logger:
                    logger.log_error(
                        "CLEANUP • HOOK_ERROR",
                        f"Error during cleanup hook {func_name}: {e}",
                        metadata={"hook": func_name, "error": str(e)},
                    )
                else:
                    print(f"[CLEANUP ERROR] {func_name}: {e}")

        if logger:
            logger.log_info(
                "CLEANUP • DONE",
                f"Cleanup completed. {terminated_count} functions executed.",
                metadata={"executed_count": terminated_count},
            )
