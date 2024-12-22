# server.py
import socket
import os
import signal
import sys
from msg import *
from config.server_config import *
from helper import mk_chksum, mk_packet, notcorrupt, switch_seq, has_seq, unpacker, extract


# Global Sequence Number
expected_seq = 0

def send_pkt(server_sock, UDP_Packet, addr):
    """Send a packet to the client."""
    server_sock.sendto(UDP_Packet, addr)
    # print(f"[SERVER] Sent packet: {unpacker.unpack(UDP_Packet)}")
def isAck(rcvdPacket, num):

    #if rcvdPacket is an ack and has the required sequence number
    if rcvdPacket[0] == 1 and rcvdPacket[1] == num:
        # print("Recieved acknowldegment with correct seq num", num)
        return True
    else:
        # print("Recieved acknowldegment with incorrect seq num", switch_seq(num))
        return False

def listen_for_ack(server_sock):
    """Listen for an acknowledgment."""
    global expected_seq
    while True:
        try:
            data, _ = server_sock.recvfrom(BUFFER_SIZE + 32 + 4 + 4)
            rcvd_packet = unpacker.unpack(data)
            if notcorrupt(rcvd_packet) and isAck(rcvd_packet, expected_seq):
                # print(f"[SERVER] Received valid ACK for seq {expected_seq}.")
                expected_seq = switch_seq(expected_seq)  # Toggle sequence
                return True
            else:
                print(f"[-] Invalid ACK or corruption detected. Resending data.")
        except socket.timeout:
            print("[-] ACK timeout. Resending data.")
            print('\n')
            return False

def send_file_rdt(server_sock, addr, file_path, offset, chunk_size):
    """Send file chunks using RDT 3.0 protocol."""
    global expected_seq
    with open(file_path, 'rb') as f:
        f.seek(offset)
        total_sent = 0

        while total_sent < chunk_size:
            remaining_size = chunk_size - total_sent
            data = f.read(min(BUFFER_SIZE, remaining_size))
            if not data:
                break

            chksum = mk_chksum((0, expected_seq, data))
            packet = mk_packet((0, expected_seq, data, chksum))

            # Send packet and wait for acknowledgment
            while True:
                send_pkt(server_sock, packet, addr)
                if listen_for_ack(server_sock):  # Wait for valid acknowledgment
                    total_sent += len(data)
                    # print(f"[SERVER] Sent {len(data)} bytes. Total sent: {total_sent}/{chunk_size}")
                    break  # Proceed to next data chunk

def handle_client_request(request, addr, server_sock):
    """Handle client requests."""
    if request.startswith(GET_REQUEST):
        _, file_name, offset, chunk_size = request.split()
        offset = int(offset)
        chunk_size = int(chunk_size)

        file_path = os.path.join(INPUT_DIR, file_name)
        if os.path.exists(file_path):
            print(f"[!] Handling file request: {file_name}")
            send_file_rdt(server_sock, addr, file_path, offset, chunk_size)
        else:
            data = (FILE_NOT_FOUND).encode("utf-8")
            chksum = mk_chksum((0, expected_seq, data))
            packet = mk_packet((0, expected_seq, data, chksum))
            send_pkt(server_sock, packet, addr)
            print(f"[-] File '{file_name}' not found.")
    elif request.startswith("CLOSE"):
        print(f"[SERVER] Client {addr} requested to close the connection.")

# Handle the server shutdown gracefully
def shutdown_server(signal, frame):
    print("\n[SERVER] Shutting down the server...")
    server_sock.close()  # Close the server socket
    sys.exit(0)  # Exit the program

def start_server():
    global server_sock
    """Start the RDT 3.0 UDP server."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((HOST_ADDR, PORT_NUM))
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 8)
    server_sock.settimeout(2)  # Timeout for retransmissions
    print(f"[SERVER] UDP server listening on {HOST_ADDR}:{PORT_NUM}")
    print("\n")

    while True:
        try:
            request, addr = server_sock.recvfrom(BUFFER_SIZE + 32 + 4 + 4)
            rcvd_packet = unpacker.unpack(request)
            if notcorrupt(rcvd_packet) and has_seq(rcvd_packet, expected_seq):
                data = extract(rcvd_packet).rstrip(b'\x00').decode("utf-8")
                handle_client_request(data, addr, server_sock)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[-] Server error: {e}")

if __name__ == "__main__":
    # print(BUFFER_SIZE)
    signal.signal(signal.SIGINT, shutdown_server)
    start_server()
