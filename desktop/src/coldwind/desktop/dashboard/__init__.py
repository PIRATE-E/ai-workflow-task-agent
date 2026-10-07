"""
package for defining the transport implementation along with creating desktop log handler
that gonna register as handler and make those logs gone through the
dashboard transport
"""

# WHAT: Import SocketManager and DesktopDashboardManager from .dashboard_transport.
# WHY: Decouples desktop dashboard package from legacy core/utils/socket_manager.py,
# preserving the Layering Invariant (Desktop defines desktop-specific dashboard transports).
from .dashboard_transport import SocketManager, DesktopDashboardManager

__all__ = ["SocketManager", "DesktopDashboardManager"]
