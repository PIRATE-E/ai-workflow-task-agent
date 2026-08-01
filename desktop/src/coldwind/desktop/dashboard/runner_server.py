from coldwind.desktop.dashboard.dashboard_transport import SocketManager
from coldwind.desktop.dashboard.dashboard_printer import Printer

if __name__ == "__main__":
    SocketManager.ServerSocketManager().start_server()
    SocketManager.ServerSocketManager().recieve_raw_log(Printer.queue_ptr)
