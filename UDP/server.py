# server.py
# chạy được với buffer_size nhỏ xíu
import socket
import os
import hashlib
import sys
import signal
import threading

import mmap
from concurrent.futures import ThreadPoolExecutor
import struct

HOST_ADDR = "0.0.0.0"
PORT_NUM = 8080
input_dir = "server_files"
# BUFFER_SIZE = 2048 # 2KB
BUFFER_SIZE = 8192 # 8KB
# BUFFER_SIZE = 16384 # 16KB


def calculate_checksum(data):
    """Calculate MD5 checksum for data."""
    return hashlib.md5(data).hexdigest()


# def send_file_error_protocol(server_socket, client_addr, file_path, offset, chunk_size):
#     """Send file chunks with error detection using checksum."""
#     with open(file_path, 'rb') as f:
#         mapped_file = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
#         mapped_file.seek(offset)
#         total_sent = 0

#         while total_sent < chunk_size:
#             remaining_size = chunk_size - total_sent
#             data = mapped_file.read(min(BUFFER_SIZE, remaining_size))
#             if not data:
#                 break

#             checksum = calculate_checksum(data)
#             checksum_bytes = checksum.encode()
#             # Pack data: [Payload size, Checksum size, Checksum, Payload]
#             packet = struct.pack(f'!II{len(checksum_bytes)}s{len(data)}s', len(data), len(checksum_bytes), checksum_bytes, data)

#             server_socket.sendto(packet, client_addr)
#             print(f"[SERVER] Sent {len(data)} bytes with checksum {checksum} to {client_addr}.")

#             try:
#                 server_socket.settimeout(10)
#                 response, _ = server_socket.recvfrom(BUFFER_SIZE)
#                 if response.decode() == "OK":
#                     print(f"[SERVER] Client {client_addr} confirmed successful reception.")
#                     total_sent += len(data)
#                 elif response.decode() == "ERROR":
#                     print(f"[SERVER] Client {client_addr} reported error. Resending data...")
#             except socket.timeout:
#                 print(f"[SERVER] Timeout waiting for client confirmation. Resending data...")

# not using struct
def send_file_error_protocol(server_socket, client_addr, file_path, offset, chunk_size):
    """Send file chunks with error detection using checksum."""
    # with open(file_path, 'rb') as f:
    #     f.seek(offset)
    #     total_sent = 0

    #     while total_sent < chunk_size:
    #         remaining_size = chunk_size - total_sent
    #         data = f.read(min(BUFFER_SIZE, remaining_size))

    # File Reading with Memory Mapping
    # Memory-mapping the file allows for efficient random access
    # and avoids reading the entire file into memory
    with open(file_path, 'rb') as f:
        # Memory-map the file for efficient random access
        mapped_file = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
        mapped_file.seek(offset)
        total_sent = 0

        while total_sent < chunk_size:
            remaining_size = chunk_size - total_sent
            data = mapped_file.read(min(BUFFER_SIZE, remaining_size))
            if not data:
                break

            checksum = calculate_checksum(data)
            packet = data + b'CHECKSUM:' + checksum.encode()

            # Send the packet
            server_socket.sendto(packet, client_addr)
            print(f"[SERVER] Sent {len(data)} bytes with checksum {checksum} to {client_addr}.")

            try:
                # Wait for client response
                server_socket.settimeout(2)
                response, _ = server_socket.recvfrom(BUFFER_SIZE)
                if response.decode() == "OK":
                    print(f"[SERVER] Client {client_addr} confirmed successful reception.")
                    total_sent += len(data)
                elif response.decode() == "ERROR":
                    print(f"[SERVER] Client {client_addr} reported error. Resending data...")
            except socket.timeout:
                print(f"[SERVER] Timeout waiting for client confirmation. Resending data...")


def handle_client_request(request, client_addr, server_socket):
    """Handle client requests."""
    try:
        if request.startswith("GET"):
            _, file_name, offset, chunk_size = request.split()
            offset = int(offset)
            chunk_size = int(chunk_size)

            file_path = os.path.join(input_dir, file_name)
            if os.path.exists(file_path):
                print(f"[SERVER] Sending file '{file_name}' to {client_addr}")
                send_file_error_protocol(server_socket, client_addr, file_path, offset, chunk_size)
            else:
                server_socket.sendto(b"FILE_NOT_FOUND", client_addr)
                print(f"[SERVER] File '{file_name}' not found.")
        elif request.startswith("CLOSE"):
            print(f"[SERVER] Client {client_addr} requested to close the connection.")
    except Exception as e:
        print(f"[SERVER] Error handling request from {client_addr}: {e}")


def client_handler_thread(request, client_addr, server_socket):
    """Threaded handler for each client request."""
    print(f"[SERVER] Starting thread for {client_addr}")
    handle_client_request(request, client_addr, server_socket)
    print(f"[SERVER] Finished handling request from {client_addr}")

# Handle the server shutdown gracefully
def shutdown_server(signal, frame):
    print("\n[SERVER] Shutting down the server...")
    server_socket.close()  # Close the server socket
    sys.exit(0)  # Exit the program

def start_server():
    global server_socket
    """Start the UDP server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST_ADDR, PORT_NUM))
    print(f"[SERVER] UDP server listening on {HOST_ADDR}:{PORT_NUM}")

    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    while True:
        try:
            request, client_addr = server_socket.recvfrom(BUFFER_SIZE)
            request = request.decode('utf-8')
            print(f"[SERVER] Received request from {client_addr}: {request}")

            # # Handle each request in a new thread
            # thread = threading.Thread(target=client_handler_thread, args=(request, client_addr, server_socket, input_dir))
            # thread.start()

            # Handle each request in a thread pool
            # This is more efficient than creating a new thread for each request
            # as it reuses existing threads
            # The number of threads can be adjusted as needed based on the server load
            # The ThreadPoolExecutor will automatically manage the thread pool
            # and reuse threads for new requests
            # Adjust the number of threads as needed
            
            executor = ThreadPoolExecutor(max_workers=10)  # Adjust the number of threads as needed
            executor.submit(client_handler_thread, request, client_addr, server_socket)
        except Exception as e:
            print(f"[SERVER] Server error: {e}")


if __name__ == "__main__":
    # Register the shutdown signal handler for graceful server shutdown
    signal.signal(signal.SIGINT, shutdown_server)
    # os.makedirs(input_dir, exist_ok=True)

    start_server()