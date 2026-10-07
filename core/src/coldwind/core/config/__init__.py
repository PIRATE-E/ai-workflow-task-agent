# Configuration module
# Contains settings and configuration utilities

# WHAT: Export both CoreSettinngs and CoreSettings.
# WHY: Supports corrected spelling while preserving backward compatibility across all modules.
from .coreSettings import CoreSettinngs, CoreSettings

__all__ = ["CoreSettinngs", "CoreSettings"]
