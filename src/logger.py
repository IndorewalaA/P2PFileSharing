from datetime import datetime

def log(peer_id: int, message: str):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{time_str}]: Peer {peer_id} {message}\n"
    with open(f"../log_peer_{peer_id}.log", "a") as log_file:
        log_file.write(log_msg)
