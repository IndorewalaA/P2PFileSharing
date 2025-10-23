import random
import threading
import time
from message_handler import send_message, recv_message, REQUEST, PIECE, HAVE
from logger import log

class TransferManager:
    def __init__(self, peer_id, config, bitfield, file_mgr, peers_state, conn_map):
        self.peer_id = peer_id
        self.config = config
        self.bitfield = bitfield
        self.file_mgr = file_mgr
        self.peers_state = peers_state  
        self.conn_map = conn_map  
        self.lock = threading.Lock()
        self.running = True

    def download_from(self, remote_id):
        conn = self.conn_map[remote_id]
        ps = self.peers_state[remote_id]
        while self.running:
            try:
                if not ps.is_choked and ps.is_interested:
                    missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
                    if missing:
                        idx = random.choice(missing)
                        send_message(conn, REQUEST, idx.to_bytes(4, "big"))
                        msg_type, payload = recv_message(conn)
                        if msg_type == PIECE:
                            piece_index = int.from_bytes(payload[:4], "big")
                            piece_data = payload[4:]
                            self.file_mgr.write_piece(piece_index, piece_data)
                            self.bitfield.set_piece(piece_index)
                            ps.update_download(len(piece_data))
                            log(self.peer_id, f"has downloaded the piece {piece_index} from {remote_id}. Now the number of pieces it has is unknown_in_this_context.")
                            for pid, sock in list(self.conn_map.items()):
                                try:
                                    send_message(sock, HAVE, piece_index.to_bytes(4, "big"))
                                except Exception:
                                    pass
                            time.sleep(0.1)
                        else:
                            time.sleep(0.1)
                    else:
                        time.sleep(0.5)
                else:
                    time.sleep(0.5)
            except ConnectionError:
                break

    def handle_request_and_send_piece(self, conn, piece_index):
        data = self.file_mgr.get_piece(piece_index)
        send_message(conn, PIECE, piece_index.to_bytes(4, "big") + data)
        log(self.peer_id, f"sent piece {piece_index} to a requester.")
