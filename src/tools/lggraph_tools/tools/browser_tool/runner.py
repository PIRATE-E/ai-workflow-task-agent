"""
this only contains the orchestration logic for the browser tool to run as subprocess
"""
from __future__ import annotations
import asyncio
from queue import Queue

from .config import BrowserRequiredConfig
from .Handler import HandlerEnums, HandlerExceptionRaises, Handler

# IMPORTANT: Import events_drivers to register driver classes with the metaclass
# Without this import, Handler.enum_driver_map will have None for all events
from .utils import events_drivers  # noqa: F401 - triggers metaclass registration

class Runner:
    """
    this is not optimized for performance and parallelism yet
    """
    __config: BrowserRequiredConfig
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Runner, cls).__new__(cls)
        return cls.__instance

    def __init__(self, config: BrowserRequiredConfig):
        # Check if already initialized (not just if instance exists)
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.__config = config
        self.__browser_process = None
        self.__running = False
        self.__agent = None
        self.__result = None  # Initialize result attribute
        self.__monitering = None
        self.__event_handler = None

    async def run(self):
        moving_forward_bus = Queue()
        all_results = []  # Collect all results from drivers

        try:
            # initial check ups for requirements and environment
            self.__event_handler = Handler()

            #### get returns the class of driver and then the execute method runs the class methods one by one and update the queue bus
            await self.__event_handler.get(self, HandlerEnums.ON_PRE_REQUIREMENTS).execute(moving_forward_bus)
            # setup phase and custom logic during setup
            await self.__event_handler.get(self, HandlerEnums.SET_UP).execute(moving_forward_bus)
            # start the agent and the browser process
            await self.__event_handler.get(self, HandlerEnums.ON_START).execute(moving_forward_bus)

            await self.__event_handler.get(self, HandlerEnums.ON_RUNNING).execute(moving_forward_bus)

            await self.__event_handler.get(self, HandlerEnums.ON_COMPLETE).execute(moving_forward_bus)

        except asyncio.CancelledError:
            raise
        except (HandlerExceptionRaises.CustomEventNotFound, HandlerExceptionRaises.DriverEventAlreadyRegistered) as e:
            # Store exception for ON_EXCEPTION driver to access
            self._Runner__last_exception = e
            await self.__event_handler.get(self, HandlerEnums.ON_EXCEPTION).execute(moving_forward_bus)
            moving_forward_bus.put({"error": str(e)})
        except Exception as e:
            # Store exception for ON_EXCEPTION driver to access
            self._Runner__last_exception = e
            # Catch any other exception and run ON_EXCEPTION handler
            await self.__event_handler.get(self, HandlerEnums.ON_EXCEPTION).execute(moving_forward_bus)
            moving_forward_bus.put({"error": str(e), "type": type(e).__name__})
        finally:
            await self.__event_handler.get(self, HandlerEnums.TEAR_DOWN).execute(moving_forward_bus)

            # Collect ALL results from the queue (non-blocking)
            while not moving_forward_bus.empty():
                try:
                    item = moving_forward_bus.get_nowait()
                    all_results.append(item)
                except Exception:
                    break

            self.__result = {
                "status": "completed",
                "results": all_results,
                "count": len(all_results)
            }
            return self.__result
