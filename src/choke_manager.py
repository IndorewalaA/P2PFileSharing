import random
import threading
import time
from logger import log
from message_handler import send_message, UNCHOKE, CHOKE

class ChokeManager:
    def __init__(self, peer_id, config, peers_state, conn_map):
        self.peer_id = peer_id
        self.config = config
        self.peers_state = peers_state
        self.conn_map = conn_map
        self.running = True
        self.lock = threading.Lock()
        self.preferred_neighbors = set()
        self.optimistic_neighbor = None

    def start(self):
        threading.Thread(target=self._choke_unchoke_cycle, daemon=True).start()
        threading.Thread(target=self._optimistic_unchoke_cycle, daemon=True).start()

    def stop(self):
        self.running = False

    def _choke_unchoke_cycle(self):
        while self.running:
            time.sleep(self.config.unchoking_interval)
            self._select_preferred_neighbors()

    def _optimistic_unchoke_cycle(self):
        while self.running:
            time.sleep(self.config.opt_unchoking_interval)
            self._select_optimistic_neighbor()

    def _select_preferred_neighbors(self):
        with self.lock:
            interested = [
                (pid, ps.download_rate)
                for pid, ps in self.peers_state.items()
                if ps.is_interested and pid in self.conn_map
            ]

            if len(interested) == 0:
                return

            interested.sort(key=lambda x: x[1], reverse=True)

            k = self.config.num_pref_neighbors
            chosen = [pid for pid, _ in interested[:k]]

            new_set = set(chosen)
            for pid in self.peers_state.keys():
                if pid in new_set:
                    if pid not in self.preferred_neighbors:
                        send_message(self.conn_map[pid], UNCHOKE)
                elif pid in self.preferred_neighbors and pid != self.optimistic_neighbor:
                    send_message(self.conn_map[pid], CHOKE)

            self.preferred_neighbors = new_set
            log(self.peer_id, f"has the preferred neighbors {', '.join(map(str, new_set))}.")

    def _select_optimistic_neighbor(self):
        with self.lock:
            choked_interested = [
                pid for pid, ps in self.peers_state.items()
                if ps.is_choked and ps.is_interested and pid in self.conn_map
            ]
            if not choked_interested:
                return

            selected = random.choice(choked_interested)
            send_message(self.conn_map[selected], UNCHOKE)
            self.optimistic_neighbor = selected
            log(self.peer_id, f"has the optimistically unchoked neighbor {selected}.")
