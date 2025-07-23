import socket
import sys
import winsound


class SocketCon:
    def __init__(self, _client_socket: socket.socket):
        self.client_socket = _client_socket

    def send_error(self, error_message: str, close_socket: bool = False):
        try:
            #     check whether the socket is connected
            if not self._is_connected():
                print(error_message, flush=True, file=sys.stderr)
                raise socket.error("Socket is not connected.")
            # Send the error message
            else:
                # print("Sending error message: ", error_message, flush=True, file=sys.stderr)
                winsound.Beep(7933, 500)  # Beep sound for error notification
                self.client_socket.sendall(error_message.encode('utf-8'))
            # self.client_socket.sendall(error_message.encode('utf-8'))
        except socket.error as e:
            print(f"Error sending message: {e}")
        finally:
            if close_socket:
                self.client_socket.close()

    def receive_error(self) -> str:
        try:
            data = self.client_socket.recv(1024)
            return data.decode('utf-8')
        except socket.error as e:
            print(f"Error receiving message: {e}")
            return ""

    def _is_connected(self):
        try:
            # Use getsockopt to check socket state without sending data
            # This works for both unidirectional and bidirectional connections
            error = self.client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error:
                return False

            # Additional check: see if socket is still connected
            # This uses a more reliable method that doesn't send data
            try:
                # Check if socket is readable (has data or is closed)
                import select
                ready, _, _ = select.select([self.client_socket], [], [], 0)
                if ready:
                    # Socket is readable - peek at data without consuming it
                    data = self.client_socket.recv(1, socket.MSG_PEEK)
                    return len(data) > 0  # If no data, connection is closed
                return True  # Socket exists and no error
            except socket.error:
                return False
        except socket.error:
            return False
        except Exception as e:
            print(f"Unexpected error in connection check: {e}")
            return False


if __name__ == '__main__':
    # Example usage
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 5390))
    server_socket.listen(1)
    server_socket.settimeout(30)  # Set a 30-second timeout for accepting connections
    listening = True

    print("Server is listening...")
    try:
        while listening:
            try:
                client_socket, addr = server_socket.accept()
            except socket.timeout:
                print("No connection made within 30 seconds. Timing out.")
                break  # Exit the loop after timeout
            print(f"Connection from {addr}")
            try:
                socket_con = SocketCon(client_socket)
                while True and client_socket:
                    received_error = socket_con.receive_error()
                    if not received_error:
                        print("No data received, closing connection.", flush=True, file=sys.stderr)
                        break  # Client disconnected or error occurred
                    print(f"{received_error}", flush=True, file=sys.stderr)
                listening = False  # Exit the loop after handling the connection
            finally:
                client_socket.close()
    finally:
        server_socket.close()
