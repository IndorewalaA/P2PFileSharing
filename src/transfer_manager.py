import random
import threading
import time
from message_handler import send_message, recv_message, REQUEST, PIECE, HAVE
from logger import log

class TransferManager:
    def __init__(self, peer_id, config, bitfield, file_mgr, peers_state, conn_map, parent_peer):
        self.peer_id = peer_id
        self.config = config
        self.bitfield = bitfield
        self.file_mgr = file_mgr
        self.peers_state = peers_state
        self.conn_map = conn_map
        self.parent = parent_peer

    def download_loop(self, remote_id):
        """
        Loop which continuously requests pieces from remote while unchoked and interested.
        This runs in a single thread per remote to avoid duplication.
        """
        while self.parent.running:
            ps = self.peers_state.get(remote_id)
            conn = None
            with self.parent.conn_lock:
                conn = self.conn_map.get(remote_id)
            if conn is None:
                break

            # if we are choked or not interested, wait
            if ps.is_choked or not ps.our_interest:
                time.sleep(0.5)
                continue

            # choose a piece randomly among missing ones that remote has
            missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
            if not missing:
                # nothing to request from this peer anymore
                time.sleep(0.5)
                continue

            idx = random.choice(missing)
            try:
                send_message(conn, REQUEST, idx.to_bytes(4, "big"))
                log(self.peer_id, f"requested piece {idx} from {remote_id}.")
            except Exception:
                break
            time.sleep(0.2)


    def handle_request_and_send_piece(self, conn, piece_index, remote_id):
        if not self.bitfield.has_piece(piece_index):
            return
        try:
            data = self.file_mgr.get_piece(piece_index)
            if data is None:
                return
            send_message(conn, PIECE, piece_index.to_bytes(4, "big") + data)
            log(self.peer_id, f"sent piece {piece_index} to {remote_id}.")
        except Exception:
            pass
