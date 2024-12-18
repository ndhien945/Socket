import socket
import threading
import os
import sys
import signal

from msg import *
HOST_ADDR = "0.0.0.0"
PORT_NUM = 8080
input_dir = "server_files"
buffer_size = 1024


# Handle each client request
def handle_client(connection_socket, input_dir, addr):
    try:
        # Receive the client's request
        request = connection_socket.recv(buffer_size).decode('utf-8')
        if not request:
            print("[SERVER] Empty request received.")

        # Handle the CLOSE protocol
        elif request.startswith(MESSAGE_CLOSE_CONNECTION):
            print("[SERVER] Client requested to close the connection.")
            
        # Handle the GET protocol
        elif request.startswith(MESSAGE_GET_REQUEST):
            _, file_name, offset, chunk_size = request.split()
            offset = int(offset)
            chunk_size = int(chunk_size)

            # Find the requested file in the input directory
            file_path = os.path.join(input_dir, file_name)
            if os.path.exists(file_path):
            # Open the file and send the requested chunk
                with open(file_path, 'rb') as f:
                    f.seek(offset)  # Move to the requested offset
                    data = f.read(chunk_size)  # Read the specified chunk
                    connection_socket.sendall(data)
            else:
                connection_socket.sendall(MESSAGE_FILE_NOT_FOUND)
    finally:
        _connection_ip, _connection_port = addr
        print(f"[SERVER] Closing the connection of {_connection_ip}:{_connection_port}.")
        connection_socket.close()

# Handle the server shutdown gracefully
def shutdown_server(signal, frame):
    print("\n[SERVER] Shutting down the server...")
    server.close()  # Close the server socket
    sys.exit(0)  # Exit the program

# Main server function
def start_server():
    global server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST_ADDR, PORT_NUM))
    server.listen(4)  # Allow up to 4 concurrent connections
    print(f"[SERVER] Server listening on {HOST_ADDR}:{PORT_NUM}")

    while True:
        connection_socket, addr = server.accept()
        _connection_ip, _connection_port = addr
        print(f"[SERVER] Connection is accepted from {_connection_ip}:{_connection_port}")
        client_thread = threading.Thread(target=handle_client, args=(connection_socket, input_dir, addr))
        client_thread.start()

# Start the server with the list of files to serve
if __name__ == "__main__":
    
    # Register the shutdown signal handler for graceful server shutdown
    signal.signal(signal.SIGINT, shutdown_server)
    # Start the server
    start_server()