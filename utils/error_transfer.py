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

    print("Server is listening...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        try:
            while True and client_socket:
                received_error = SocketCon.receive_error(client_socket)
                if not received_error:
                    break  # Client disconnected or error occurred
                print(f"{received_error}")
        finally:
            client_socket.close()