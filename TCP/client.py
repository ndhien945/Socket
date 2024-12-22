import socket
import threading
import os
import time
import signal
import sys
from rich.progress import Progress, BarColumn, TextColumn
from msg import *
from config.client_config import *
from client_help import *

downloaded_files = set()
unavailable_files = set()


def download_chunk(file_name, offset, chunk_size, part_num, output_dir, progress, task_id):
    max_retries = 5
    retry_delay = 3  # seconds

    for attempt in range(max_retries):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            client_ip, client_port = client_socket.getsockname()
            print(f"[!] Client IP: {client_ip}, Client Port: {client_port} for part {part_num + 1}")
            

            # Send the GET request with file name, offset, and chunk size
            request = f"{GET_REQUEST} {file_name} {offset} {chunk_size}\n"
            client_socket.send(request.encode('utf-8'))

            # Save the chunk to a file and calculate progress
            part_file_path = f"{output_dir}/{file_name}.part_{part_num + 1}"
            with open(part_file_path, "wb") as f:
                total_received = 0  # Track how many bytes have been received
                flagFileNotFound = False
                while True:
                    data = client_socket.recv(buffer_size)
                    if not data:
                        break
                    elif MESSAGE_FILE_NOT_FOUND in data:
                        print(f"[-] File: {file_name} not found on the server for part {part_num + 1}.")
                        flagFileNotFound = True
                        break
                    f.write(data)
                    total_received += len(data)

                    # Calculate progress percentage
                    progress.update(task_id, completed=total_received)
            if flagFileNotFound == True:
                os.remove(part_file_path)
                unavailable_files.add(file_name)
                return # Stop the download if the file is not found
            if (total_received == chunk_size) or (part_num == 3 and total_received == chunk_size):
                return  # Success, exit the function
        except (ConnectionResetError, socket.error) as e:
            print(f"[-] Connection error: {e}. Retrying ({attempt + 1}/{max_retries})...")
            time.sleep(retry_delay)
        finally:
            client_socket.sendall(MESSAGE_CLOSE_CONNECTION)
            print(f"[!] Closing the connection {client_ip}:{client_port} for part {part_num + 1}.")
            client_socket.close()

    print(f"[-] Failed to download chunk {part_num + 1} of {file_name} after {max_retries} attempts.")
    # Explicitly notify the server when closing the connection due to failure (open new socket to send message)
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        client_socket.sendall(MESSAGE_CLOSE_CONNECTION)
    except Exception as e:
        print(f"[-] Unable to notify server: {e}")
    finally:
        client.close()


# Merge downloaded parts into the final file
def merge_chunks(file_name, num_parts, output_dir, output_file):
    # Check if all parts are present and complete
    for i in range(num_parts):
        part_file_path = f"{output_dir}/{file_name}.part_{i + 1}"
        if not os.path.exists(part_file_path):
            print(f"[-] Missing part {i + 1} for {file_name}. Cannot merge.")
            return  # Stop if any part is missing
        if os.path.getsize(part_file_path) == 0:
            print(f"[-] Part {i + 1} of {file_name} is incomplete. Cannot merge.")
            return  # Stop if any part is incomplete
    
    # Proceed to merge if all parts are complete
    with open(output_file, "wb") as final_file:
        for i in range(num_parts):
            # num_parts starts with 0, but we saved the parts starting with 1 => i + 1
            part_file_path = f"{output_dir}/{file_name}.part_{i + 1}"

            # Read each part and write to the final file
            # Then remove the part file
            with open(part_file_path, "rb") as part_file:
                final_file.write(part_file.read())
            os.remove(part_file_path)
    print(f"[!] Merged all parts of {file_name} into {output_file}")

def is_file_downloaded(file_name, output_dir):
    """
    Check if the file already exists in the output directory.
        bool: True if the file exists, False otherwise.
    """
    output_file = os.path.join(output_dir, file_name)
    return os.path.exists(output_file)

def download_file(file_name, file_size, output_dir):
    # Check if the file already exists
    if is_file_downloaded(file_name, output_dir):
        print(f"[!] {file_name} already exists in {output_dir}. Skipping download.")
        print("\n")
        print("\n")
        return  # Skip download if file already exists

    threads = []
    num_parts = 4  # Number of parts to download
    chunk_size = file_size // num_parts  # Calculate chunk size
    last_chunk_size = file_size - (chunk_size * (num_parts - 1))  # Last chunk size

    with Progress(
        TextColumn("[bold blue]{task.fields[filename]}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} bytes ({task.percentage:>3.0f}%)"),
    ) as progress:
        
        # Create progress bars for each chunk
        tasks = []
        for part_num in range(num_parts):
            if part_num == num_parts - 1:
                # Handle last chunk
                part_chunk_size = last_chunk_size
            else:
                part_chunk_size = chunk_size
            task_id = progress.add_task(
                f"Downloading {file_name} part {part_num + 1}",
                    filename=f"{file_name} part {part_num + 1}",
                    total=part_chunk_size,
                    completed=0,
            )
            tasks.append(task_id)
        
        # Start threads for each part
        for part_num in range(num_parts):
            if part_num == num_parts - 1:
                # Handle last chunk
                part_chunk_size = last_chunk_size
            else:
                part_chunk_size = chunk_size
            offset = part_num * chunk_size
            # Create a thread for each part
            task_id = tasks[part_num]

            # Start the thread
            t = threading.Thread(
                target=download_chunk,
                args=(file_name, offset, part_chunk_size, part_num, output_dir, progress, task_id)
            )

            # Add the thread to the list and start it
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

    # Merge the chunks into the final file
    output_file = os.path.join(output_dir, file_name)
    if file_name not in unavailable_files:
        merge_chunks(file_name, num_parts, output_dir, output_file)
    print("\n")
    print("\n")

def read_file_to_list(file_path):
    file_list = []
    with open(file_path, 'r') as f:
        for line in f:
            name, size = line.strip().split()
            file_list.append({"name": name, "size": int(size)})
    return file_list


# Monitor `input.txt` for new files and download them
def monitor_and_download():
    global downloaded_files

    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Define a signal handler to handle Ctrl+C gracefull
    def signal_handler(signum, frame):
        print("\n[CLIENT] Shutting down monitoring... Goodbye!")
        sys.exit(0)  # Exit the program

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    # numberAttempts = 0
    while True:
        try:
            # Read the input file and check for new files
            file_list = read_file_to_list(input_file)
            for file_info in file_list:
                file_name = file_info["name"]
                file_size = file_info["size"]

                # Check if the file has already been downloaded
                if file_name not in downloaded_files:
                    print(f"[!] New file detected: {file_name}")
                    download_file(file_name, file_size, output_dir)
                    downloaded_files.add(file_name)
        except Exception as e:
            print(f"[-] Failed to process input file: {e}")

        # numberAttempts += 1
        print("[*] Waiting for new request of downloading new file(s)...")
        time.sleep(5)  # Check for new files every 5 seconds


# Download multiple files from the server
# TODO: Modify code to serve numparts = 4 (not the fixed chunk size)
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "?"]:
        print_help()
    else:
        monitor_and_download()