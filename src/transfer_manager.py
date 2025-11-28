# TODO: make sure that all the logs are consistent with the project spec.
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

    def download_from(self, remote_id):
        ps = self.peers_state[remote_id]
        conn = self.conn_map[remote_id]
        if not conn or ps.is_choked:
            return
        else:
            missing = self.bitfield.missing_pieces_from(ps.remote_bitfield)
            if missing:
                idx = random.choice(missing)
                try: 
                    send_message(conn, REQUEST, idx.to_bytes(4, "big"))
                except Exception as e:
                    print(f"Failed to send Req to {remote_id}")
    def handle_request_and_send_piece(self, conn, piece_index, remote_id):
        if not self.bitfield.has_piece(piece_index):
            return
        try:
            data = self.file_mgr.get_piece(piece_index)
            send_message(conn, PIECE, piece_index.to_bytes(4, "big") + data)
            log(self.peer_id, f"sent piece {piece_index} to a requester.")
        except Exception as e:
            print("Error sending piece.")
