import socket


class SocketCon:
    def __init__(self, client_socket: socket.socket):
        self.client_socket = client_socket

    def send_error(self, error_message: str, close_socket: bool = False):
        try:
            self.client_socket.sendall(error_message.encode('utf-8'))
        except socket.error as e:
            print(f"Error sending message: {e}")
        finally:
            if close_socket:
                self.client_socket.close()

    @staticmethod
    def receive_error(client_socket: socket.socket) -> str:
        try:
            data = client_socket.recv(1024)
            return data.decode('utf-8')
        except socket.error as e:
            print(f"Error receiving message: {e}")
            return ""


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
                while True and client_socket:
                    received_error = SocketCon.receive_error(client_socket)
                    if not received_error:
                        print("No data received, closing connection.")
                        break  # Client disconnected or error occurred
                    print(f"{received_error}")
                listening = False  # Exit the loop after handling the connection
            finally:
                client_socket.close()
    finally:
        server_socket.close()
