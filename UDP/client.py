# client.py
import socket
import os
import threading
import hashlib
import signal
import sys
import time
from rich.progress import Progress, BarColumn, TextColumn
import struct


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
# BUFFER_SIZE = 2048
BUFFER_SIZE = 8192
# BUFFER_SIZE = 12288
# BUFFER_SIZE = 16384
downloaded_files = set()


def calculate_checksum(data):
    """Calculate MD5 checksum for data."""
    return hashlib.md5(data).hexdigest()


# # using struct
# def download_chunk(file_name, offset, chunk_size, part_num, output_dir, progress, task_id):
#     """Download a file chunk using error detection protocol."""
#     retries = 20
#     total_received = 0
#     part_file_path = os.path.join(output_dir, f"{file_name}.part_{part_num + 1}")

#     while retries > 0:
#         try:
#             client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#             client_socket.settimeout(10)

#             request = f"GET {file_name} {offset} {chunk_size}"
#             client_socket.sendto(request.encode('utf-8'), (SERVER_HOST, SERVER_PORT))

#             with open(part_file_path, "wb") as f:
#                 while total_received < chunk_size:
#                     packet, _ = client_socket.recvfrom(BUFFER_SIZE + 50)

#                     # # Unpack data using struct: [Payload size (I), Checksum length (I), Checksum (variable), Payload (variable)]
#                     # payload_size = struct.unpack('!I', packet[:4])[0]
#                     # checksum_length = struct.unpack('!I', packet[4:8])[0]
#                     # checksum = packet[8:8 + checksum_length].decode()
#                     # data = packet[8 + checksum_length:8 + checksum_length + payload_size]
#                     # Unpack the data
#                     payload_size, checksum_length = struct.unpack('!II', packet[:8])
#                     checksum = struct.unpack(f'!{checksum_length}s', packet[8:8 + checksum_length])[0]
#                     data = struct.unpack(f'!{payload_size}s', packet[8 + checksum_length:8 + checksum_length + payload_size])[0]

#                     if calculate_checksum(data) == checksum.decode():
#                         remaining_size = chunk_size - total_received
#                         data_to_write = data[:remaining_size]

#                         f.write(data_to_write)
#                         total_received += len(data_to_write)
#                         progress.update(task_id, completed=total_received)
#                         client_socket.sendto(b"OK", (SERVER_HOST, SERVER_PORT))

#                         if total_received >= chunk_size:
#                             break
#                     else:
#                         client_socket.sendto(b"ERROR", (SERVER_HOST, SERVER_PORT))
#                         print(f"[CLIENT] Checksum mismatch. Requesting resend...")
#                         break
#             return
#         except socket.timeout:
#             print(f"[CLIENT] Timeout. Retrying chunk {part_num + 1}...")
#         finally:
#             client_socket.close()
#         retries -= 1

#     print(f"[ERROR] Failed to download part {part_num + 1} after retries.")

# not using struct
def download_chunk(file_name, offset, chunk_size, part_num, output_dir, progress, task_id):
    """Download a file chunk using error detection protocol."""
    retries = 20
    total_received = 0
    part_file_path = os.path.join(output_dir, f"{file_name}.part_{part_num + 1}")

    while retries > 0:
        try:
            # Each chunk download uses its own socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # TODO: know what this does?
            client_socket.settimeout(7)

            request = f"GET {file_name} {offset} {chunk_size}"
            client_socket.sendto(request.encode('utf-8'), (SERVER_HOST, SERVER_PORT))

            with open(part_file_path, "wb") as f:
                while total_received < chunk_size:
                    packet, _ = client_socket.recvfrom(BUFFER_SIZE + 50)
                    if b'CHECKSUM:' in packet:
                        data, checksum = packet.rsplit(b'CHECKSUM:', 1)
                        if calculate_checksum(data) == checksum.decode():
                            # Calculate remaining chunk size
                            remaining_size = chunk_size - total_received
                            data_to_write = data[:remaining_size]

                            f.write(data_to_write)
                            total_received += len(data_to_write)
                            progress.update(task_id, completed=total_received)
                            client_socket.sendto(b"OK", (SERVER_HOST, SERVER_PORT))

                            if total_received >= chunk_size:
                                break
                        else:
                            client_socket.sendto(b"ERROR", (SERVER_HOST, SERVER_PORT))
                            print(f"[CLIENT] Checksum mismatch. Requesting resend...")
                            break
                    else:
                        print(f"[CLIENT] Invalid packet format.")
                        break
            return
        except socket.timeout:
            print(f"[CLIENT] Timeout. Retrying chunk {part_num + 1}...")
        finally:
            client_socket.close()
        retries -= 1

    print(f"[ERROR] Failed to download part {part_num + 1} after retries.")


def merge_chunks(file_name, num_parts, output_dir):
    """Merge downloaded chunks into the final file."""
    output_file = os.path.join(output_dir, file_name)
    with open(output_file, "wb") as final_file:
        for i in range(num_parts):
            part_file_path = os.path.join(output_dir, f"{file_name}.part_{i + 1}")
            with open(part_file_path, "rb") as part_file:
                final_file.write(part_file.read())
            os.remove(part_file_path)
    print(f"[INFO] Successfully merged file: {output_file}")


def is_file_downloaded(file_name, output_dir):
    """Check if the file already exists in the output directory."""
    output_file = os.path.join(output_dir, file_name)
    return os.path.exists(output_file)


def download_file(file_name, file_size, output_dir):
    if is_file_downloaded(file_name, output_dir):
        print(f"[CLIENT][NOTIFICATION] {file_name} already exists. Skipping download.")
        return

    num_parts = 4
    chunk_size = file_size // num_parts
    last_chunk_size = file_size - (chunk_size * (num_parts - 1))

    threads = []
    with Progress(
        TextColumn("[bold blue]{task.fields[filename]}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} bytes ({task.percentage:>3.0f}%)"),
    ) as progress:
        tasks = []
        
        # Initialize progress tasks for all parts
        for part_num in range(num_parts):
            part_chunk_size = last_chunk_size if part_num == num_parts - 1 else chunk_size
            task_id = progress.add_task(
                f"Downloading {file_name} part {part_num + 1}",
                filename=f"{file_name} part {part_num + 1}",
                total=part_chunk_size,
                completed=0,
            )
            tasks.append(task_id)

        # Start all threads simultaneously
        for part_num in range(num_parts):
            part_chunk_size = last_chunk_size if part_num == num_parts - 1 else chunk_size
            offset = part_num * chunk_size
            task_id = tasks[part_num]

            # Start a separate thread for each part
            t = threading.Thread(
                target=download_chunk,
                args=(file_name, offset, part_chunk_size, part_num, output_dir, progress, task_id),
                daemon=True  # Set threads as daemon to ensure cleanup on termination
            )
            t.start()
            threads.append(t)

        # Wait for all threads to finish
        for t in threads:
            t.join()

    # Merge downloaded chunks after all parts finish
    merge_chunks(file_name, num_parts, output_dir)

def read_file_to_list(file_path):
    file_list = []
    with open(file_path, "r") as f:
        for line in f:
            name, size = line.strip().split()
            file_list.append({"name": name, "size": int(size)})
    return file_list


def monitor_and_download(input_file, output_dir):
    global downloaded_files

    def signal_handler(signum, frame):
        print("\n[CLIENT][INFO] Shutting down monitoring... Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    i = 0
    while True:
        print(f"[CLIENT][INFO] Monitoring for new files... (Attempt {i + 1})")
        try:
            file_list = read_file_to_list(input_file)
            for file_info in file_list:
                file_name = file_info["name"]
                file_size = file_info["size"]

                if file_name not in downloaded_files:
                    print(f"[CLIENT][NOTIFICATION] New file detected: {file_name}")
                    download_file(file_name, file_size, output_dir)
                    downloaded_files.add(file_name)
        except Exception as e:
            print(f"[CLIENT][ERROR] Failed to process input file: {e}")

        i += 1
        print("[CLIENT][INFO] Waiting for new requests...")
        time.sleep(5)


if __name__ == "__main__":
    output_dir = "./downloads"
    os.makedirs(output_dir, exist_ok=True)

    input_file = "input.txt"
    monitor_and_download(input_file, output_dir)
