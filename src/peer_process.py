import sys
import socket
import threading
import time
import random
from messages import encode_handshake, decode_handshake
from config import parse_config, parse_peer_info
from message_handler import send_message, recv_message, BITFIELD, HAVE, INTERESTED, NOT_INTERESTED, CHOKE, UNCHOKE, REQUEST, PIECE
from bitfield import Bitfield
from peer_state import PeerState
from transfer_manager import TransferManager
from choke_manager import ChokeManager
from logger import log
from file_manager import FileManager
import os

class PeerProcess:
    def __init__(self, peer_id: int):
        self.peer_id = peer_id
        self.config = parse_config()
        self.peers = parse_peer_info()
        self.peer_map = {p.peer_ID: p for p in self.peers}
        total_pieces = (self.config.file_size + self.config.piece_size - 1) // self.config.piece_size

        # ensure peer folder exists
        os.makedirs(f"peer_{self.peer_id}", exist_ok=True)

        # bitfield and file manager
        self.bitfield = Bitfield(total_pieces)
        self.file_mgr = FileManager(f"peer_{self.peer_id}/{self.config.file_name}", self.config.piece_size)

        # if peer starts with full file, mark all pieces present
        my_info = self.peer_map.get(self.peer_id)
        if my_info and my_info.has_file:
            for i in range(total_pieces):
                self.bitfield.set_piece(i)
            # ensure file exists (user should place it), but leave as-is if missing

        # per-peer state, excluding self
        self.peers_state = {p.peer_ID: PeerState(p.peer_ID, total_pieces) for p in self.peers if p.peer_ID != peer_id}
        self.conn_map = {}
        self.conn_lock = threading.Lock()

        # prevent duplicate download threads
        self.download_threads = {}

        # Pass a callback so choke manager can check whether local copy is complete
        self.choke_manager = ChokeManager(self.peer_id, self.config, self.peers_state, self.conn_map, lambda: self.bitfield.is_complete())
        self.transfer_mgr = TransferManager(self.peer_id, self.config, self.bitfield, self.file_mgr, self.peers_state, self.conn_map, self)

        self.running = True

    def start(self):
        log(self.peer_id, ("starts." 
                           f"\nSet Variables:"
                           f"\n--------------------------------"
                           f"\nConfig: Number of preferred neighbors = {self.config.num_pref_neighbors}, " 
                           f"\nUnchoking interval = {self.config.unchoking_interval} seconds, " 
                           f"\nOptimistic unchoking interval = {self.config.opt_unchoking_interval} seconds, "
                           f"\nFile: {self.config.file_name}, "
                           f"\nFile size: {self.config.file_size} bytes, "
                           f"\nPiece size: {self.config.piece_size} bytes."
                           f"\nInitial bitfield: {self.bitfield.to_bytes().hex()}"))
        
        # start listening for incoming connections
        threading.Thread(target=self._listen_for_incoming, daemon=True).start()
        time.sleep(0.5)
        # try to connect to earlier peers with retries
        self._connect_to_earlier_peers()
        self.choke_manager.start()
        threading.Thread(target=self._completion_watcher, daemon=True).start()

    def _listen_for_incoming(self):
        my_info = self.peer_map[self.peer_id]
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('', my_info.listening_port))
            server.listen(5)
            while self.running:
                try:
                    conn, addr = server.accept()
                    threading.Thread(target=self._handle_connection_incoming, args=(conn,), daemon=True).start()
                except Exception:
                    if self.running:
                        continue
        except Exception as e:
            print("Server error:", e)
            self.shutdown()

    def _connect_to_earlier_peers(self):
        ids = [p.peer_ID for p in self.peers]
        my_index = ids.index(self.peer_id)
        for p in self.peers[:my_index]:
            connected = False
            for attempt in range(5):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)
                    sock.connect((p.host_name, p.listening_port))
                    sock.settimeout(None)
                    # send handshake and wait reply
                    sock.sendall(encode_handshake(self.peer_id))
                    resp = sock.recv(32)
                    remote_id = decode_handshake(resp)
                    if remote_id != p.peer_ID:
                        sock.close()
                        break
                    with self.conn_lock:
                        self.conn_map[remote_id] = sock
                    log(self.peer_id, f"makes a connection to Peer {remote_id}.")
                    # send bitfield only if we have any pieces
                    # send remote_id to log
                    self._send_our_bitfield_if_any(sock, remote_id)
                    # start message listener for this connection
                    threading.Thread(target=self._message_listener, args=(remote_id, sock), daemon=True).start()
                    connected = True
                    break
                except Exception as e:
                    time.sleep(1.0)
                    continue
            if not connected:
                print(f"Could not connect to peer {p.peer_ID} after retries.")

    def _handle_connection_incoming(self, conn: socket.socket):
        try:
            data = conn.recv(32)
            remote_id = decode_handshake(data)
            # send handshake back
            conn.sendall(encode_handshake(self.peer_id))
            with self.conn_lock:
                self.conn_map[remote_id] = conn
            log(self.peer_id, f"is connected from Peer {remote_id}.")
            # send our bitfield only if we have pieces
            self._send_our_bitfield_if_any(conn, remote_id)
            threading.Thread(target=self._message_listener, args=(remote_id, conn), daemon=True).start()
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass

    def _send_our_bitfield_if_any(self, sock: socket.socket, remote_id: int):
        payload = self.bitfield.to_bytes()
        if any(b != 0 for b in payload):
            try:
                send_message(sock, BITFIELD, payload)
                log(self.peer_id, f"sent the 'bitfield' message to {remote_id}.")
            except Exception:
                pass

    def _message_listener(self, remote_id: int, sock: socket.socket):
        ps = self.peers_state[remote_id]
        while self.running:
            try:
                msg_type, payload = recv_message(sock)
            except Exception:
                break

            if msg_type == BITFIELD:
                ps.remote_bitfield.from_bytes(payload)
                log(self.peer_id, f"received the 'bitfield' message from {remote_id}.")
                self._evaluate_interest(remote_id)

            elif msg_type == HAVE:
                index = int.from_bytes(payload[:4], "big")
                ps.remote_bitfield.set_piece(index)
                log(self.peer_id, f"received the 'have' message from {remote_id} for the piece {index}.")
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
                if remote_id not in self.download_threads or not self.download_threads[remote_id].is_alive():
                    t = threading.Thread(target=self.transfer_mgr.download_loop, args=(remote_id,), daemon=True)
                    self.download_threads[remote_id] = t
                    t.start()

            elif msg_type == REQUEST:
                index = int.from_bytes(payload[:4], "big")
                if self.bitfield.has_piece(index):
                    self.transfer_mgr.handle_request_and_send_piece(sock, index, remote_id)

            elif msg_type == PIECE:
                piece_index = int.from_bytes(payload[:4], "big")
                piece_data = payload[4:]
                self.file_mgr.write_piece(piece_index, piece_data)
                self.bitfield.set_piece(piece_index)
                ps.update_download(len(piece_data))
                num_pieces = sum(1 for i in range(self.bitfield.num_pieces) if self.bitfield.has_piece(i))
                log(self.peer_id, f"has downloaded the piece {piece_index} from {remote_id}. Now the number of pieces it has is {num_pieces}.")
                with self.conn_lock:
                    for pid, s in list(self.conn_map.items()):
                        try:
                            send_message(s, HAVE, piece_index.to_bytes(4, "big"))
                        except Exception:
                            pass
                self._evaluate_interest(remote_id)

            else:
                pass

        with self.conn_lock:
            if remote_id in self.conn_map and self.conn_map[remote_id] is sock:
                try:
                    sock.close()
                except:
                    pass
                del self.conn_map[remote_id]

    def _evaluate_interest(self, remote_id: int):
        ps = self.peers_state[remote_id]
        sock = None
        with self.conn_lock:
            sock = self.conn_map.get(remote_id)
        if not sock:
            return
        missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
        if missing:
            try:
                send_message(sock, INTERESTED)
            except Exception:
                pass
            ps.is_interested = True
            log(self.peer_id, f"sent the 'interested' message to {remote_id}.")
        else:
            try:
                send_message(sock, NOT_INTERESTED)
            except Exception:
                pass
            ps.is_interested = False
            log(self.peer_id, f"sent the 'not interested' message to {remote_id}.")

    def _completion_watcher(self):
        while self.running:
            time.sleep(2)
            try:
                if not self.bitfield.is_complete():
                    continue
                all_complete = True
                for pid, ps in self.peers_state.items():
                    if not ps.remote_bitfield.is_complete():
                        all_complete = False
                        break
                if all_complete:
                    log(self.peer_id, "has downloaded the complete file.")
                    time.sleep(1.0)
                    self.shutdown()
                    break
            except Exception:
                continue

    def shutdown(self):
        self.running = False
        self.choke_manager.stop()
        with self.conn_lock:
            for s in list(self.conn_map.values()):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    s.close()
                except Exception:
                    pass
            self.conn_map.clear()
        log(self.peer_id, "has shut down.")

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
