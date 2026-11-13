# Configuration module
# Contains settings and configuration utilities

# WHAT: Export both CoreSettinngs and CoreSettings.
# WHY: Supports corrected spelling while preserving backward compatibility across all modules.
from .coreSettings import CoreSettings, CoreSettinngs

__all__ = ["CoreSettings", "CoreSettinngs"]
