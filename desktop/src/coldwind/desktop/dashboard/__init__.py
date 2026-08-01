"""
package for defining the transport implementation along with creating desktop log handler
that gonna register as handler and make those logs gone through the
dashboard transport
"""

from coldwind.core.utils.socket_manager import SocketManager

__all__ = ["SocketManager"]
