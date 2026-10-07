"""Unified utils package initializer for ColdWind core.

Provides a stable, minimal public API and defers heavy imports until
first attribute access to reduce circular import risk and startup cost.

Public API:
    open_ai_integration (lazy)
    model_manager (lazy)
    timestamp_util
    argument_schema_util
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Dict

# WHAT: Explicitly expose core-only utility modules without platform monkey-patching.
# WHY: Invariant: "Core NEVER imports Desktop". Removed former monkey-patching of
# `coldwind.desktop.ui.diagnostics.*` into `sys.modules["coldwind.core.utils.*"]`
# and removed legacy `socket_manager` which moved to desktop dashboard transport.
from coldwind.core.utils import timestamp_util
from coldwind.core.utils import argument_schema_util

__all__ = [
    "open_ai_integration",
    "model_manager",
    "timestamp_util",
    "argument_schema_util",
]

_LAZY_MODULES: Dict[str, str] = {
    "open_ai_integration": "coldwind.core.utils.open_ai_integration",
    "model_manager": "coldwind.core.utils.model_manager",
}


def __getattr__(name: str) -> ModuleType:  # noqa: D401
    """Lazily load registered heavy utility submodules."""
    if name in _LAZY_MODULES:
        path = _LAZY_MODULES[name]
        try:
            mod = import_module(path)
            globals()[name] = mod  # cache
            return mod  # type: ignore
        except Exception as e:  # pragma: no cover
            raise AttributeError(f"Failed lazy import '{name}' ({path}): {e}") from e
    raise AttributeError(f"module 'coldwind.core.utils' has no attribute '{name}'")


def __dir__():  # pragma: no cover
    return sorted(set(__all__ + [k for k in globals().keys() if not k.startswith("_")]))

