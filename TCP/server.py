import socket
import threading
import os
import json

HOST_ADDR = "0.0.0.0"
PORT_NUM = 8080

# Handle each client request
def handle_client(client_socket, file_list):
    try:
        # Receive the client's request
        request = client_socket.recv(1024).decode('utf-8')
        if request.startswith("GET"):
            _, file_name, offset, chunk_size = request.split()
            offset = int(offset)
            chunk_size = int(chunk_size)

            # Find the requested file in the file list
            file_path = next((f for f in file_list if os.path.basename(f) == file_name), None)
            if file_path and os.path.exists(file_path):
                # Open the file and send the requested chunk
                with open(file_path, 'rb') as f:
                    f.seek(offset)  # Move to the requested offset
                    data = f.read(chunk_size)  # Read the specified chunk
                    client_socket.sendall(data)
            else:
                client_socket.sendall(b"FILE_NOT_FOUND")
    finally:
        client_socket.close()

# Main server function
def start_server(file_list):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST_ADDR, PORT_NUM))
    server.listen(4)  # Allow up to 4 concurrent connections
    print(f"Server listening on {HOST_ADDR}:{PORT_NUM}")



    while True:
        client_socket, addr = server.accept()
        print(f"Connection is accepted from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, file_list))
        client_thread.start()

# Start the server with the list of files to serve
if __name__ == "__main__":
    # Load file_list from JSON file
    with open('server.json', 'r') as file:
        file_list = json.load(file)

    file_list_to_serve = ["server_files/file1.txt", "server_files/hala", "server_files/huge.zip", 
                          "server_files/superhuge_2g.MOV", "server_files/video.mov"]
    start_server(file_list_to_serve)
    # start_server(file_list)


