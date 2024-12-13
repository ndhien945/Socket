import socket
import threading
import os
import time

# Save each chunk to a separate file part
def download_chunk(server_host, server_port, file_name, offset, chunk_size, part_num, output_dir):
    max_retries = 5
    retry_delay = 3  # seconds

    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_host, server_port))

            # Send the GET request with file name, offset, and chunk size
            request = f"GET {file_name} {offset} {chunk_size}\n"
            client.send(request.encode('utf-8'))

            # Receive the data and save it to a file part
            with open(f"{output_dir}/{file_name}.part_{part_num}", "wb") as f:
                while True:
                    data = client.recv(1024)
                    if not data:
                        break
                    f.write(data)
            print(f"[INFO] Successfully downloaded chunk {part_num} of {file_name}")
            return  # Success, exit the function
        except (ConnectionResetError, socket.error) as e:
            print(f"[ERROR] Connection error: {e}. Retrying ({attempt + 1}/{max_retries})...")
            time.sleep(retry_delay)
        finally:
            client.close()

    print(f"[ERROR] Failed to download chunk {part_num} of {file_name} after {max_retries} attempts.")

# Merge downloaded parts into the final file
def merge_chunks(file_name, num_parts, output_dir, output_file):
    with open(output_file, "wb") as final_file:
        for i in range(num_parts):
            part_file_path = f"{output_dir}/{file_name}.part_{i}"
            with open(part_file_path, "rb") as part_file:
                final_file.write(part_file.read())
            os.remove(part_file_path)
    print(f"[INFO] Merged all parts of {file_name} into {output_file}")

# Main client function
def download_file(server_host, server_port, file_name, file_size, chunk_size, output_dir):
    threads = []
    # num_parts = (file_size + chunk_size - 1) // chunk_size  # Calculate number of chunks
    num_parts = 4  # Number of parts to download
    chunk_size = file_size // 4  # Calculate chunk size to have 4 parts
    last_chunk_size = file_size - (chunk_size * 3)  # Calculate the size of the last chunk

    if chunk_size == last_chunk_size:
        for part_num in range(num_parts):
            offset = part_num * chunk_size
            t = threading.Thread(target=download_chunk, args=(server_host, server_port, file_name, offset, chunk_size, part_num, output_dir))
            threads.append(t)
            t.start()
    else:
        for part_num in range(num_parts - 1):
            offset = part_num * chunk_size
            t = threading.Thread(target=download_chunk, args=(server_host, server_port, file_name, offset, chunk_size, part_num, output_dir))
            threads.append(t)
            t.start()
        offset = (num_parts - 1) * chunk_size
        t = threading.Thread(target=download_chunk, args=(server_host, server_port, file_name, offset, last_chunk_size, 3, output_dir))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Merge the chunks into the final file
    output_file = os.path.join(output_dir, file_name)
    merge_chunks(file_name, num_parts, output_dir, output_file)

# Download multiple files from the server
# TODO: Modify code to serve numparts = 4 (not the fixed chunk size)
if __name__ == "__main__":
    server_host = "127.0.0.1"
    server_port = 8080
    file_list = [
        {"name": "file1.txt", "size": 140},  # Replace with actual file sizes
        {"name": "hala", "size": 47},
        {"name": "huge.zip", "size": 13325},
        {"name": "superhuge_2g.MOV", "size": 2301684714},
        {"name": "video.mov", "size": 41064525}
    ]
    chunk_size = 1000 # TODO: Adjust the chunk size as needed
    output_dir = "./downloads"

    os.makedirs(output_dir, exist_ok=True)

    for file_info in file_list:
        file_name = file_info["name"]
        file_size = file_info["size"]
        download_file(server_host, server_port, file_name, file_size, chunk_size, output_dir)