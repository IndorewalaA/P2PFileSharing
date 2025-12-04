from datetime import datetime
import os

# ensures parent directory exists (for log)
def _ensure_log_dir():
    parent = os.path.abspath("..")
    if not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass

# logs to file for each peer 
def log(peer_id: int, message: str):
    _ensure_log_dir()
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{time_str}]: Peer {peer_id} {message}\n"
    with open(f"../log_peer_{peer_id}.log", "a") as log_file:
        log_file.write(log_msg)