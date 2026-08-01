from time import sleep
from typing import override

from coldwind.core.system_logging.debug_protocol import LogEntry
from coldwind.core.system_logging.handlers.handler_base import Handler
from .dashboard_transport import SocketManager
from coldwind.desktop.dashboard.dashboard_transport import DesktopDashboardManager


class DashBoardHandler(Handler):
    name: str = "DashBoardHandler"
    _started = False

    @override
    def should_handle(self, log_entry: LogEntry, *args) -> bool:
        return True  ## we would make this recieve all the logs

    @override
    def handle(self, log_entry: LogEntry, *args) -> None:

        ## first check the health of the DashBoardHandler that is it started and connected or not
        ## if not connected just connected just skip for now
        ## if the connection is present use the send_to_dashboard method to actually send the log entry to there
        ## would be convert that log entry to json for easy to dashboard_transporter to actually make it ship to the debugging window or panel ..

        if not DashBoardHandler._started:
            DesktopDashboardManager.start_dashboard()
            DashBoardHandler._started = True
            sleep(3)
            SocketManager.ClientSocketManager().connect_to_server()
        DesktopDashboardManager.send_to_dashboard(log_entry)
