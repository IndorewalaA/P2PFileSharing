import struct
import socket

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7

def send_message(sock: socket.socket, msg_type: int, payload: bytes = b""):
    msg_length = 1 + len(payload)
    sock.sendall(struct.pack("!I", msg_length) + bytes([msg_type]) + payload)

def recv_message(sock: socket.socket):
    header = sock.recv(4)
    if not header:
        return None
    (length,) = struct.unpack("!I", header)
    data = sock.recv(length)
    msg_type = data[0]
    payload = data[1:]
    return msg_type, payload
