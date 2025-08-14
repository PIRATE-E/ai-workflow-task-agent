# Minimal exports; avoid importing deprecated debug modules from old location
# Provide backward-compatible re-exports to new diagnostics package when available

from importlib import import_module

__all__ = []

# Backward compatibility: expose debug_helpers & debug_message_protocol from new path
try:
    debug_helpers = import_module('src.ui.diagnostics.debug_helpers')
    __all__.append('debug_helpers')
except Exception:
    pass

try:
    debug_message_protocol = import_module('src.ui.diagnostics.debug_message_protocol')
    __all__.append('debug_message_protocol')
except Exception:
    pass

# Other optional utility modules
for _mod_name in [
    'open_ai_integration',
    'model_manager',
    'socket_manager',
    'structured_triple_prompt',
]:
    try:
        globals()[_mod_name] = import_module(f'src.utils.{_mod_name}')
        __all__.append(_mod_name)
    except Exception:
        continue