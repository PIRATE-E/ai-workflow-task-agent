# Minimal exports; avoid importing deprecated debug modules from old location
# Provide backward-compatible re-exports to new diagnostics package when available

from importlib import import_module
import sys

__all__ = []

# Backward compatibility: expose debug_helpers & debug_message_protocol from new path
try:
    _dh_mod = import_module('src.ui.diagnostics.debug_helpers')
    debug_helpers = _dh_mod  # type: ignore
    sys.modules.setdefault('src.utils.debug_helpers', _dh_mod)
    __all__.append('debug_helpers')
except Exception:
    pass

try:
    _dmp_mod = import_module('src.ui.diagnostics.debug_message_protocol')
    debug_message_protocol = _dmp_mod  # type: ignore
    sys.modules.setdefault('src.utils.debug_message_protocol', _dmp_mod)
    __all__.append('debug_message_protocol')
except Exception:
    pass

# Legacy alias for rich_traceback_manager
try:
    _rtm_mod = import_module('src.ui.diagnostics.rich_traceback_manager')
    rich_traceback_manager = _rtm_mod  # type: ignore
    sys.modules.setdefault('src.utils.rich_traceback_manager', _rtm_mod)
    __all__.append('rich_traceback_manager')
except Exception:
    pass

# Other optional utility modules (kept lightweight)
for _mod_name in [
    'open_ai_integration',
    'model_manager',
    'socket_manager',
    'structured_triple_prompt',
]:
    try:
        _mod = import_module(f'src.utils.{_mod_name}')
        globals()[_mod_name] = _mod  # type: ignore
        __all__.append(_mod_name)
    except Exception:
        continue