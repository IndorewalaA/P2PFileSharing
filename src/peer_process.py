# TODO: make sure that all the logs are consistent with the project spec.
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

class PeerProcess:
    def __init__(self, peer_id: int):
        self.peer_id = peer_id
        self.config = parse_config()
        self.peers = parse_peer_info()
        self.peer_map = {p.peer_ID: p for p in self.peers}
        total_pieces = (self.config.file_size + self.config.piece_size - 1) // self.config.piece_size
        # states
        self.bitfield = Bitfield(total_pieces)
        self.file_mgr = FileManager(f"peer_{self.peer_id}/{self.config.file_name}", self.config.piece_size)
        my_info = self.peer_map.get(self.peer_id)
        if my_info and my_info.has_file:
            for i in range(total_pieces):
                self.bitfield.set_piece(i)
        self.peers_state = {p.peer_ID: PeerState(p.peer_ID, total_pieces) for p in self.peers if p.peer_ID != peer_id}
        self.conn_map = {}  
        self.transfer_mgr = TransferManager(self.peer_id, self.config, self.bitfield, self.file_mgr, self.peers_state, self.conn_map)
        self.choke_manager = ChokeManager(self.peer_id, self.config, self.peers_state, self.conn_map)
        self.running = True

    def start(self):
        log(self.peer_id, "starts.")
        threading.Thread(target=self._listen_for_incoming, daemon=True).start()
        time.sleep(1)
        self._connect_to_earlier_peers()
        self.choke_manager.start()
        threading.Thread(target=self._completion_watcher, daemon=True).start()

    def _listen_for_incoming(self):
        my_info = self.peer_map[self.peer_id]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('', my_info.listening_port))
            s.listen(5)
            while self.running:
                conn, addr = s.accept()
                threading.Thread(target=self._handle_connection_incoming, args=(conn,), daemon=True).start()
        except Exception as e:
            print("Server error!")
            self.shutdown()

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
                if remote_id != p.peer_ID:
                    print(f"Expected peer {p.peer_ID}, got {remote_id}")
                    sock.close()
                    continue
                log(self.peer_id, f"makes a connection to Peer {remote_id}.")
                self.conn_map[remote_id] = sock
                self._send_our_bitfield(sock)
                threading.Thread(target=self._message_listener, args=(remote_id, sock), daemon=True).start()
            except Exception as e:
                print(f"connect error to {p.peer_ID}: {e}")

    def _handle_connection_incoming(self, conn: socket.socket):
        try:
            data = conn.recv(32)
            remote_id = decode_handshake(data)
            conn.sendall(encode_handshake(self.peer_id))
            log(self.peer_id, f"is connected from Peer {remote_id}.")
            self.conn_map[remote_id] = conn
            self._send_our_bitfield(conn)
            threading.Thread(target=self._message_listener, args=(remote_id, conn), daemon=True).start()
        except Exception as e:
            print("Handshake error!")
            conn.close()

    def _send_our_bitfield(self, sock: socket.socket):
        payload = self.bitfield.to_bytes()
        if payload:
            send_message(sock, BITFIELD, payload)

    def _message_listener(self, remote_id: int, sock: socket.socket):
        ps = self.peers_state[remote_id]
        while self.running:
            try:
                msg_type, payload = recv_message(sock)
            except Exception:
                break
            if msg_type == BITFIELD:
                ps.remote_bitfield.from_bytes(payload)
                self._evaluate_interest(remote_id)
            elif msg_type == HAVE:
                index = int.from_bytes(payload[:4], "big")
                ps.remote_bitfield.set_piece(index)
                log(self.peer_id, f"received 'have' from {remote_id} for {index}")
                self._evaluate_interest(remote_id)
            elif msg_type == INTERESTED:
                ps.is_interested = True
                log(self.peer_id, f"received 'interested' from {remote_id}")
            elif msg_type == NOT_INTERESTED:
                ps.is_interested = False
                log(self.peer_id, f"received 'not interested' from {remote_id}")
            elif msg_type == CHOKE:
                ps.is_choked = True
                log(self.peer_id, f"is choked by {remote_id}")
            elif msg_type == UNCHOKE:
                ps.is_choked = False
                log(self.peer_id, f"is unchoked by {remote_id}")
                self.transfer_mgr.download_from(remote_id)
            elif msg_type == REQUEST:
                index = int.from_bytes(payload[:4], "big")
                self.transfer_mgr.handle_request_and_send_piece(sock, index, remote_id)
            elif msg_type == PIECE:
                piece_index = int.from_bytes(payload[:4], "big")
                piece_data = payload[4:]
                self.file_mgr.write_piece(piece_index, piece_data)
                self.bitfield.set_piece(piece_index)
                ps.update_download(len(piece_data))
                num_pieces = sum(1 for i in range(self.bitfield.num_pieces) if self.bitfield.has_piece(i))
                log(self.peer_id, f"{piece_index} downloaded from {remote_id}. Total pieces: {num_pieces}")
                for pid, s in self.conn_map.items():
                    try:
                        send_message(s, HAVE, piece_index.to_bytes(4, "big"))
                    except:
                        pass
                self._evaluate_interest(remote_id)
                self.transfer_mgr.download_from(remote_id)
            else:
                pass

    def _evaluate_interest(self, remote_id: int):
        """Send interested or not interested depending on remote bitfield."""
        ps = self.peers_state[remote_id]
        sock = self.conn_map.get(remote_id)
        if not sock:
            return
        missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
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
            time.sleep(2)
            if self.bitfield.is_complete():
                all_complete = True
                for pid, ps in self.peers_state.items():
                    if not ps.remote_bitfield.is_complete():
                        all_complete = False
                        break
                if all_complete:
                    log(self.peer_id, "has downloaded the complete file.")
                    time.sleep(2.0)
                    self.shutdown()

    def shutdown(self):
        """Graceful shutdown: close sockets, stop managers."""
        self.running = False
        self.choke_manager.stop()
        for s in self.conn_map.values():
            try:
                s.close()
            except Exception:
                pass
        log(self.peer_id, "is shutting down.")
        sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print("Usage: python peer_process.py [peerID]")
        sys.exit(1)
    pid = int(sys.argv[1])
    try:
        p = PeerProcess(pid)
        p.start()
        while p.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Critical error!")

if __name__ == "__main__":
    main()
