# this file reads the .cfg files
import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "..", "configuration")

COMMON_PATH = os.path.abspath(os.path.join(CONFIG_DIR, "Common.cfg"))
PEERINFO_PATH = os.path.abspath(os.path.join(CONFIG_DIR, "PeerInfo.cfg"))

# reads Common.cfg
@dataclass
class Common:
    num_pref_neighbors: int
    unchoking_interval: int
    opt_unchoking_interval: int
    file_name: str
    file_size: int
    piece_size: int

def parse_config() -> Common:
    if not os.path.exists(COMMON_PATH):
        raise FileNotFoundError(f"Common.cfg not found at {COMMON_PATH}")

    values = []
    with open(COMMON_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            key, value = line.split()
            values.append(value)

    if len(values) < 6:
        raise ValueError("Common.cfg is missing required fields")

    return Common(
        num_pref_neighbors=int(values[0]),
        unchoking_interval=int(values[1]),
        opt_unchoking_interval=int(values[2]),
        file_name=values[3],
        file_size=int(values[4]),
        piece_size=int(values[5])
    )
    
# reads PeerInfo.cfg
@dataclass
class Peer:
    peer_ID: int
    host_name: str
    listening_port: int
    has_file: bool

def parse_peer_info():
    if not os.path.exists(PEERINFO_PATH):
        raise FileNotFoundError(f"PeerInfo.cfg not found at {PEERINFO_PATH}")

    peers_list = []
    with open(PEERINFO_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            peer_id, host, port, hasfile = line.split()
            peers_list.append(
                Peer(
                    peer_ID=int(peer_id),
                    host_name=host,
                    listening_port=int(port),
                    has_file=(hasfile == "1")
                )
            )

    return peers_list

def main():
    test = parse_config()
    test2 = parse_peer_info()

if __name__ == "__main__":
    main()