import time
from bitfield import Bitfield

class PeerState:
    def __init__(self, peer_id: int, total_pieces: int):
        self.peer_id = peer_id
        self.is_choked = True
        self.is_interested = False
        self.download_rate = 0.0
        self._last_bytes = 0
        self._last_time = time.time()
        self.remote_bitfield = Bitfield(total_pieces)
        self.bytes_received_total = 0

    def update_download(self, bytes_received_since_last_call: int):
        now = time.time()
        diff = now - self._last_time
        self.bytes_received_total += bytes_received_since_last_call
        if diff > 0:
            self.download_rate = (self.bytes_received_total - self._last_bytes) / diff
        self._last_time = now
        self._last_bytes = self.bytes_received_total