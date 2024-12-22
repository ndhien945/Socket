# helper.py
import hashlib
import struct
from config.server_config import *
from config.client_config import *


# Shared Configuration
unpacker = struct.Struct(f'I I {BUFFER_SIZE}s 32s')
ack_unpacker = struct.Struct('I I')  # Acknowledgments only have ack_num and seq_num

def mk_chksum(values):
    """Create checksum for the given tuple."""
    UDP_Data = struct.Struct('I I 32s')
    ack_num, seq_num, data = values

    # Truncate or pad data to 32 bytes
    data = data[:32].ljust(32, b'\x00')
    packed_data = UDP_Data.pack(ack_num, seq_num, data)

    # Return checksum as a 32-byte MD5 hash
    return bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

def mk_packet(values_with_chksum):
    """Create a packet with the given data tuple."""
    UDP_Data = struct.Struct(f'I I {BUFFER_SIZE}s 32s')
    ack_num, seq_num, data, chksum = values_with_chksum

    # Truncate or pad data to BUFFER_SIZE bytes
    data = data[:BUFFER_SIZE].ljust(BUFFER_SIZE, b'\x00')
    # Truncate or pad checksum to 32 bytes
    chksum = chksum[:32].ljust(32, b'\x00')

    # Return the packed packet
    return UDP_Data.pack(ack_num, seq_num, data, chksum)

def notcorrupt(UDP_Packet):
    """Check if a packet is corrupted."""
    ack_num, seq_num, data, chksum = UDP_Packet
    # Truncate or pad data and calculate checksum
    data = data[:BUFFER_SIZE].ljust(BUFFER_SIZE, b'\x00')
    calculated_chksum = mk_chksum((ack_num, seq_num, data))

    # Compare with received checksum
    return chksum.rstrip(b'\x00') == calculated_chksum

def send_pkt(sock, packet, addr):
    """Send a packet."""
    sock.sendto(packet, addr)

def switch_seq(seq):
    """Switch the sequence number."""
    if seq == 0:
        return 1
    else:
        return 0

def extract(UDP_Packet):
    """Extract data from a packet."""
    return UDP_Packet[2][:BUFFER_SIZE].rstrip(b'\x00')

def deliver(data):
    """Deliver data upwards."""
    string = data.decode("utf-8")
    print(f"Received data: {string}, successfully delivered upwards")


def has_seq(UDP_Packet,num):
    if UDP_Packet[1] == num:
        # print('Packet has correct sequence number: seq =', num)
        return True
    else:
        print('Packet has incorrect sequence number: seq =', switch_seq(num))
        return False
    
def extract(UDP_Packet):
    """Extract data from a packet."""
    return UDP_Packet[2]

