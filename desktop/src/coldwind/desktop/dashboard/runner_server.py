from coldwind.desktop.dashboard.dashboard_transport import SocketManager
from coldwind.desktop.dashboard.dashboard_printer import Printer, console

if __name__ == "__main__":
    # WHAT: Print startup banner and pass Printer.process_log callable to recieve_raw_log.
    # WHY: Previously passed Printer.queue_ptr directly, which silently appended JSON strings
    #      to an in-memory deque without rendering anything to the terminal. Passing
    #      Printer.process_log activates the live Rich panel formatter for incoming logs.
    console.print(
        "[bold cyan]Cold Wind Debug Dashboard Initialized • Listening on port 59700...[/bold cyan]\n"
    )
    server = SocketManager.ServerSocketManager()
    server.start_server()
    server.recieve_raw_log(Printer.process_log)

