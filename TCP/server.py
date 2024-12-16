import socket
import threading
import os
import json

HOST_ADDR = "0.0.0.0"
PORT_NUM = 8080

# Handle each client request
def handle_client(connection_socket, input_dir, addr):
    try:
        # Receive the client's request
        request = connection_socket.recv(1024).decode('utf-8')
        if not request:
            print("[SERVER] Empty request received.")

        # Handle the CLOSE protocol
        elif request.startswith("CLOSE"):
            print("[SERVER] Client requested to close the connection.")
            
        # Handle the GET protocol
        elif request.startswith("GET"):
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
                connection_socket.sendall(b"FILE_NOT_FOUND")
    finally:
        _connection_ip, _connection_port = addr
        print(f"[SERVER] Closing the connection of {_connection_ip}:{_connection_port}.")
        print("\n\n")
        connection_socket.close()

# Main server function
def start_server(input_dir):
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

    # Define the input directory that contains the files to serve
    input_dir = "server_files"  # TODO: change this to be read from a config file

    # Load file_list from JSON file
    with open('server.json', 'r') as file:
        file_list = json.load(file)

    # Start the server
    start_server(input_dir)