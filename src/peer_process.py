import socket
import threading
from config_parser import parse_config, parse_peer_info
from handshake import encode_handshake, decode_handshake
from message_handler import send_message, recv_message
from logger import log

class PeerProcess:
    def __init__(self, peer_id: int):
        self.peer_id = peer_id
        self.config = parse_config()
        self.peers = parse_peer_info()
        self.connections = []

    def start(self):
        log(self.peer_id, "Starting peer process.")
        self._connect_to_others()
        self._listen_for_incoming()
    
    def _connect_to_others(self):
        my_index = [p.peer_ID for p in self.peers].index(self.peer_id)
        for p in self.peers[:my_index]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((p.host_name, p.listening_port))
            s.sendall(encode_handshake(self.peer_id))
            remote_id = decode_handshake(s.recv(32))
            log(self.peer_id, f"makes a connection to Peer {remote_id}")
            self.connections.append(s)

    def _listen_for_incoming(self):
        my_peer = next(p for p in self.peers if p.peer_ID == self.peer_id)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', my_peer.listening_port))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=self._handle_connection, args=(conn,)).start()

    def _handle_connection(self, conn):
        handshake = conn.recv(32)
        remote_id = decode_handshake(handshake)
        log(self.peer_id, f"is connected from Peer {remote_id}")
        #need to work on more
