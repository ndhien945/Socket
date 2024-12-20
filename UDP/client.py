# client.py
import os
import socket
import time
import signal
import sys
from msg import *
from client_help import *
from rich.progress import Progress, BarColumn, TextColumn

from helper import mk_chksum, mk_packet, notcorrupt, switch_seq, send_pkt, has_seq, unpacker, extract, BUFFER_SIZE

# Client Configuration

# Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
INPUT_FILE = "input.txt"
OUTPUT_DIR = "./downloads"
downloaded_files = set()

interval = 0.009  # Timeout interval
expected_seq = 0  # Sequence number
ack_msg = b"ACK__ACK"


def download_chunk(client_socket, file_name, offset, chunk_size, part_num, progress, task_id):
    """Download a file chunk using RDT 3.0."""
    global expected_seq
    retries = 20
    total_received = 0
    part_file_path = f"{OUTPUT_DIR}/{file_name}.part_{part_num + 1}"

    with open(part_file_path, "wb") as f:
        while retries > 0:
            try:
                data = f"{GET_REQUEST} {file_name} {offset} {chunk_size}".encode("utf-8")
                chksum = mk_chksum((0, expected_seq, data))
                packet = mk_packet((0, expected_seq, data, chksum))

                # Send the packet for the first time
                send_pkt(client_socket, packet, (SERVER_HOST, SERVER_PORT))
                
                # Receive data
                while total_received < chunk_size:
                    # response, _ = client_socket.recvfrom(BUFFER_SIZE)
                    response, _ = client_socket.recvfrom(BUFFER_SIZE + 32 + 4 + 4)
                    rcvd_packet = unpacker.unpack(response)
                    # Check if the recieved packet has been corrupted and has the correct sequence number
                    if notcorrupt(rcvd_packet) and has_seq(rcvd_packet, expected_seq):
                        remaining_size = chunk_size - total_received
                        data = extract(rcvd_packet)
                        # print("data IS THIS: ", data)
                        data_to_write = data[:remaining_size]
                        f.write(data_to_write)
                        total_received += len(data_to_write)
                        progress.update(task_id, completed=total_received)


                        # Acknowledge reception
                        chksum = mk_chksum((1, expected_seq, ack_msg))
                        ack_packet = mk_packet((1, expected_seq, ack_msg, chksum))
                        send_pkt(client_socket, ack_packet, (SERVER_HOST, SERVER_PORT))
                        expected_seq = switch_seq(expected_seq)
                    else:
                        # When packet loss or corruption occurs or wrong sequence number (duplicate packet)
                        # Acknowledge reception
                        chksum = mk_chksum((1, switch_seq(expected_seq), ack_msg))
                        packet = mk_packet((1, switch_seq(expected_seq), ack_msg, chksum))
                        send_pkt(packet, (SERVER_HOST, SERVER_PORT))
                        print("[-] Checksum mismatch or wrong sequence. Retrying...")
                        retries -= 1
                        break
                return
            except socket.timeout:
                retries -= 1
                print("[*] Timeout. Retrying...")
    print(f"[-] Failed to download part {part_num + 1} after retries.")


def merge_chunks(file_name, num_parts):
    """Merge downloaded chunks into the final file."""
    output_file = os.path.join(OUTPUT_DIR, file_name)
    with open(output_file, "wb") as final_file:
        for i in range(num_parts):
            part_file_path = f"{OUTPUT_DIR}/{file_name}.part_{i + 1}"
            with open(part_file_path, "rb") as part_file:
                final_file.write(part_file.read())
            os.remove(part_file_path)
    print(f"[CLIENT] Successfully merged file: {output_file}")


def is_file_downloaded(file_name):
    """
    Check if the file already exists in the output directory.
    Returns:
        bool: True if the file exists, False otherwise.
    """
    output_file = os.path.join(OUTPUT_DIR, file_name)
    return os.path.exists(output_file)

def download_file(file_name, file_size, output_dir):
     # Check if the file already exists
    if is_file_downloaded(file_name):
        print(f"[!] {file_name} already exists in {output_dir}. Skipping download.")
        print("\n")
        print("\n")
        return  # Skip download if file already exists


    """Download a file by splitting it into parts."""
    num_parts = 4
    chunk_size = file_size // num_parts
    last_chunk_size = file_size - (chunk_size * (num_parts - 1))

    # Create and reuse a single socket for all chunks
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.settimeout(5)

        with Progress(
            TextColumn("[bold blue]{task.fields[filename]}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} bytes ({task.percentage:>3.0f}%)"),
        ) as progress:
            tasks = []
            for part_num in range(num_parts):
                part_chunk_size = last_chunk_size if part_num == num_parts - 1 else chunk_size
                task_id = progress.add_task(
                    f"[%] Downloading {file_name} part {part_num + 1}",
                    filename=f"{file_name} part {part_num + 1}",
                    total=part_chunk_size,
                    completed=0,
                )
                tasks.append((part_num, part_chunk_size, task_id))

            for part_num, part_chunk_size, task_id in tasks:
                offset = part_num * chunk_size
                download_chunk(client_socket, file_name, offset, part_chunk_size, part_num, progress, task_id)
        
        # Close the socket
        data = (CLOSE_CONNECTION).encode("utf-8")
        chksum = mk_chksum((0, expected_seq, data))
        packet = mk_packet((0, expected_seq, data, chksum))
                           
        # Send the packet for the first time
        send_pkt(client_socket, packet, (SERVER_HOST, SERVER_PORT))
        client_socket.close()

    merge_chunks(file_name, num_parts)

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
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Define a signal handler to handle Ctrl+C gracefull
    def signal_handler(signum, frame):
        print("\n[CLIENT] Shutting down monitoring... Goodbye!")
        sys.exit(0)  # Exit the program

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            # Read the input file and check for new files
            file_list = read_file_to_list(INPUT_FILE)
            for file_info in file_list:
                file_name = file_info["name"]
                file_size = file_info["size"]

                # Check if the file has already been downloaded
                if file_name not in downloaded_files:
                    print(f"[!] New file detected: {file_name}")
                    download_file(file_name, file_size, OUTPUT_DIR)
                    downloaded_files.add(file_name)
        except Exception as e:
            print(f"[-] Failed to process input file: {e}")

        print("[*] Waiting for new request of downloading new file(s)...")
        time.sleep(5)  # Check for new files every 5 seconds

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "?"]:
        print_help()
    else:
        monitor_and_download()