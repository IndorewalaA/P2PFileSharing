import sys
import socket
import threading
import time
import random
from handshake import encode_handshake, decode_handshake
from config_parser import parse_config, parse_peer_info
from message_handler import send_message, recv_message, BITFIELD, HAVE, INTERESTED, NOT_INTERESTED, CHOKE, UNCHOKE, REQUEST, PIECE
from bitfield import Bitfield
from peer_state import PeerState
from transfer_manager import TransferManager
from choke_manager import ChokeManager
from logger import log
from file_manager import FileManager

class PeerProcess:
    def __init__(self, peer_id: int):
        self.peer_id = peer_id
        self.config = parse_config()
        self.peers = parse_peer_info()
        self.peer_map = {p.peer_ID: p for p in self.peers}
        total_pieces = (self.config.file_size + self.config.piece_size - 1) // self.config.piece_size
        # states
        self.peers_state = {p.peer_ID: PeerState(p.peer_ID, total_pieces) for p in self.peers if p.peer_ID != peer_id}
        self.conn_map = {}
        self.lock = threading.Lock()
        self.file_mgr = FileManager(f"../peer_{self.peer_id}/{self.config.file_name}", self.config.piece_size)
        self.bitfield = Bitfield(total_pieces)
        my_info = self.peer_map.get(self.peer_id) or next((p for p in self.peers if p.peer_ID == self.peer_id), None)
        if my_info and my_info.has_file:
            try:
                pieces = self.file_mgr.split_file()
                for i, _ in enumerate(pieces):
                    self.bitfield.set_piece(i)
            except Exception:
                pass

        self.transfer_mgr = TransferManager(self.peer_id, self.config, self.bitfield, self.file_mgr, self.peers_state, self.conn_map)
        self.choke_manager = ChokeManager(self.peer_id, self.config, self.peers_state, self.conn_map)
        self.running = True

    def start(self):
        log(self.peer_id, "starts.")
        threading.Thread(target=self._listen_for_incoming, daemon=True).start()
        time.sleep(0.3)
        self._connect_to_earlier_peers()
        self.choke_manager.start()
        threading.Thread(target=self._completion_watcher, daemon=True).start()

    def _listen_for_incoming(self):
        my_info = next(p for p in self.peers if p.peer_ID == self.peer_id)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', my_info.listening_port))
        s.listen()
        while self.running:
            conn, addr = s.accept()
            threading.Thread(target=self._handle_connection_incoming, args=(conn,), daemon=True).start()

    def _connect_to_earlier_peers(self):
        ids = [p.peer_ID for p in self.peers]
        my_index = ids.index(self.peer_id)
        for p in self.peers[:my_index]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((p.host_name, p.listening_port))
                sock.sendall(encode_handshake(self.peer_id))
                resp = sock.recv(32)
                remote_id = decode_handshake(resp)
                log(self.peer_id, f"makes a connection to Peer {remote_id}.")
                self.conn_map[remote_id] = sock
                self._send_our_bitfield(sock)
                self._recv_and_process_initial_bitfield(sock, remote_id)
                threading.Thread(target=self._message_listener, args=(remote_id, sock), daemon=True).start()
            except Exception as e:
                print(f"connect error to {p.peer_ID}: {e}")

    def _handle_connection_incoming(self, conn: socket.socket):
        try:
            data = conn.recv(32)
            remote_id = decode_handshake(data)
            log(self.peer_id, f"is connected from Peer {remote_id}.")
            conn.sendall(encode_handshake(self.peer_id))
            self.conn_map[remote_id] = conn
            self._send_our_bitfield(conn)
            try:
                conn.settimeout(1.0)
                msg_type, payload = recv_message(conn)
                conn.settimeout(None)
                if msg_type == BITFIELD:
                    self.peers_state[remote_id].remote_bitfield.from_bytes(payload)
                    self._evaluate_interest(remote_id)
                else:
                    pass
            except Exception:
                conn.settimeout(None)
            threading.Thread(target=self._message_listener, args=(remote_id, conn), daemon=True).start()
        except Exception as e:
            print("incoming connection error:", e)

    def _send_our_bitfield(self, sock: socket.socket):
        payload = self.bitfield.to_bytes()
        if payload:
            send_message(sock, BITFIELD, payload)

    def _recv_and_process_initial_bitfield(self, sock: socket.socket, remote_id: int):
        try:
            msg_type, payload = recv_message(sock)
            if msg_type == BITFIELD:
                self.peers_state[remote_id].remote_bitfield.from_bytes(payload)
                self._evaluate_interest(remote_id)
            else:
                pass
        except Exception:
            pass

    def _message_listener(self, remote_id: int, sock: socket.socket):
        """Central message loop per connection — handles all incoming messages."""
        ps = self.peers_state[remote_id]
        while self.running:
            try:
                msg_type, payload = recv_message(sock)
            except ConnectionError:
                break
            except Exception:
                continue

            if msg_type == BITFIELD:
                ps.remote_bitfield.from_bytes(payload)
                self._evaluate_interest(remote_id)

            elif msg_type == HAVE:
                idx = int.from_bytes(payload[:4], "big")
                ps.remote_bitfield.set_piece(idx)
                log(self.peer_id, f"received the 'have' message from {remote_id} for the piece {idx}.")
                self._evaluate_interest(remote_id)

            elif msg_type == INTERESTED:
                ps.is_interested = True
                log(self.peer_id, f"received the 'interested' message from {remote_id}.")
            elif msg_type == NOT_INTERESTED:
                ps.is_interested = False
                log(self.peer_id, f"received the 'not interested' message from {remote_id}.")
            elif msg_type == CHOKE:
                ps.is_choked = True
                log(self.peer_id, f"is choked by {remote_id}.")
            elif msg_type == UNCHOKE:
                ps.is_choked = False
                log(self.peer_id, f"is unchoked by {remote_id}.")
                threading.Thread(target=self.transfer_mgr.download_from, args=(remote_id,), daemon=True).start()
            elif msg_type == REQUEST:
                idx = int.from_bytes(payload[:4], "big")
                if self.bitfield.has_piece(idx):
                    data = self.file_mgr.get_piece(idx)
                    send_message(sock, PIECE, idx.to_bytes(4, "big") + data)
                    log(self.peer_id, f"sent piece {idx} to {remote_id}.")
            elif msg_type == PIECE:
                piece_index = int.from_bytes(payload[:4], "big")
                piece_data = payload[4:]
                self.file_mgr.write_piece(piece_index, piece_data)
                self.bitfield.set_piece(piece_index)
                log(self.peer_id, f"has downloaded the piece {piece_index} from {remote_id}. Now the number of pieces it has is unknown_in_this_context.")
                for pid, s in list(self.conn_map.items()):
                    try:
                        send_message(s, HAVE, piece_index.to_bytes(4, "big"))
                    except Exception:
                        pass
            else:
                pass

    def _evaluate_interest(self, remote_id: int):
        """Send interested or not interested depending on remote bitfield."""
        ps = self.peers_state[remote_id]
        missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
        sock = self.conn_map.get(remote_id)
        if not sock:
            return
        if missing:
            send_message(sock, INTERESTED)
            ps.is_interested = True
            log(self.peer_id, f"sent the 'interested' message to {remote_id}.")
        else:
            send_message(sock, NOT_INTERESTED)
            ps.is_interested = False
            log(self.peer_id, f"sent the 'not interested' message to {remote_id}.")

    def _completion_watcher(self):
        """Every few seconds check whether all peers have complete file and terminate if so."""
        while self.running:
            try:
                all_complete = True
                if not self.bitfield.is_complete():
                    all_complete = False
                for pid, ps in self.peers_state.items():
                    if not ps.remote_bitfield.is_complete():
                        all_complete = False
                        break
                if all_complete:
                    log(self.peer_id, "has downloaded the complete file.")
                    time.sleep(1.0)
                    self.shutdown()
                    break
                time.sleep(2.0)
            except Exception:
                time.sleep(2.0)

    def shutdown(self):
        """Graceful shutdown: close sockets, stop managers."""
        self.running = False
        self.choke_manager.stop()
        for s in list(self.conn_map.values()):
            try:
                s.close()
            except Exception:
                pass
        log(self.peer_id, "is shutting down.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python peer_process.py [peerID]")
        sys.exit(1)
    pid = int(sys.argv[1])
    pp = PeerProcess(pid)
    pp.start()
    try:
        while pp.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pp.shutdown()

if __name__ == "__main__":
    main()
