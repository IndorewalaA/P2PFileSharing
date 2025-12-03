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

def _recv_all(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed while receiving")
        data.extend(chunk)
    return bytes(data)

def send_message(sock: socket.socket, msg_type: int, payload: bytes = b""):
    length = 1 + len(payload)
    sock.sendall(struct.pack("!I", length) + bytes([msg_type]) + payload)

def recv_message(sock: socket.socket):
    header = _recv_all(sock, 4)
    (length,) = struct.unpack("!I", header)
    body = _recv_all(sock, length)
    msg_type = body[0]
    payload = body[1:]
    return msg_type, payload