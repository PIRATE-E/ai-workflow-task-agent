"""
package that handles the platform level logging and transport to destination whether it is rich  logging dashboard
abstract class but hold control,keep eye on over flow of logs and define contracts of creating that dashboard
and launching dashboard process or transport of logs ...
"""

from abc import ABC, abstractmethod, ABCMeta
from typing import override

from coldwind.core.system_logging.debug_protocol import LogEntry


class dashboard_meta(ABCMeta):
    """
    META CLASS TO CONTROL THE DASHBOARD classes AVAILABLE IN THE PLATFORM
    """

    # @override
    # def __call__(cls): ...


class DashboardManager(ABC):
    """
    that class defines the few concrete methods for the platform to must implements them

    Extension point: how a platform hosts a debug dashboard.

    Core never knows whether a dashboard window exists. A platform (desktop)
    implements this to start/stop its own dashboard process and push
    dispatched LogEntries to it.
    """

    @classmethod
    @abstractmethod
    def start_dashboard(cls):
        ## state the server or dashboard where the logs are going to display
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def stop_dashboard(cls):
        ## stop the dashboard where the logs where getting headed
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def send_to_dashboard(cls, log_entry: LogEntry, **kwargs):
        ## send logs to the dashboard it would expect argument to
        raise NotImplementedError


__all__ = ["DashboardManager"]
