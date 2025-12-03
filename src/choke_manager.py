import random
import threading
import time
from logger import log
from message_handler import send_message, UNCHOKE, CHOKE

class ChokeManager:
    def __init__(self, peer_id, config, peers_state, conn_map, have_complete_fn):
        """
        have_complete_fn: callable that returns True when this peer has full file.
        """
        self.peer_id = peer_id
        self.config = config
        self.peers_state = peers_state
        self.conn_map = conn_map
        self.have_complete_fn = have_complete_fn
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
            try:
                self._select_preferred_neighbors()
            except Exception:
                continue

    def _optimistic_unchoke_cycle(self):
        while self.running:
            time.sleep(self.config.opt_unchoking_interval)
            try:
                self._select_optimistic_neighbor()
            except Exception:
                continue

    def _select_preferred_neighbors(self):
        with self.lock:
            # consider only peers that are connected and interested
            available = [(pid, ps.download_rate) for pid, ps in self.peers_state.items() if ps.is_interested and pid in self.conn_map]

            if not available:
                for pid in list(self.preferred_neighbors):
                    if pid != self.optimistic_neighbor and pid in self.conn_map:
                        try:
                            send_message(self.conn_map[pid], CHOKE)
                        except Exception:
                            pass
                self.preferred_neighbors.clear()
                log(self.peer_id, "has the preferred neighbors .")
                return

            k = self.config.num_pref_neighbors

            # if we have the complete file, choose randomly among interested
            if self.have_complete_fn():
                chosen = [pid for pid, _ in random.sample(available, min(k, len(available)))]
            else:
                available.sort(key=lambda x: x[1], reverse=True)
                chosen = [pid for pid, _ in available[:k]]

            new_set = set(chosen)

            # unchoke newly preferred neighbors
            for pid in new_set:
                if pid not in self.preferred_neighbors:
                    if pid in self.conn_map:
                        try:
                            send_message(self.conn_map[pid], UNCHOKE)
                        except Exception:
                            pass

            # choke those that were preferred before but not anymore (and not optimistic)
            for pid in list(self.preferred_neighbors):
                if pid not in new_set and pid != self.optimistic_neighbor:
                    if pid in self.conn_map:
                        try:
                            send_message(self.conn_map[pid], CHOKE)
                        except Exception:
                            pass

            self.preferred_neighbors = new_set
            log(self.peer_id, f"has the preferred neighbors {', '.join(map(str, sorted(list(new_set))))}.")

    def _select_optimistic_neighbor(self):
        with self.lock:
            # pick choked & interested peers
            candidates = [pid for pid, ps in self.peers_state.items() if ps.is_interested and ps.is_choked and pid in self.conn_map]
            if not candidates:
                return
            selected = random.choice(candidates)
            if selected in self.conn_map:
                try:
                    send_message(self.conn_map[selected], UNCHOKE)
                except Exception:
                    pass
            self.optimistic_neighbor = selected
            log(self.peer_id, f"has the optimistically unchoked neighbor {selected}.")
