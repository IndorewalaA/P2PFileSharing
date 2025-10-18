# this file reads the .cfg files
from dataclasses import dataclass

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
    # store everything in a list to store into obj later
    common_list = []
    with open('../configuration/Common.cfg', 'r', encoding='utf-8') as common_file:
        for line in common_file:
            common_list.append(line.strip().split()[1])
    return Common(
        num_pref_neighbors=int(common_list[0]), 
        unchoking_interval=int(common_list[1]),
        opt_unchoking_interval=int(common_list[2]),
        file_name=common_list[3],
        file_size=int(common_list[4]),
        piece_size=int(common_list[5])
    )
    
# reads PeerInfo.cfg
@dataclass
class Peer:
    peer_ID: int
    host_name: str
    listening_port: int
    has_file: bool

def parse_peer_info():
    peers_list = []
    with open('../configuration/PeerInfo.cfg', 'r', encoding='utf-8') as peer_info_file:
        for line in peer_info_file:
            peer_info = line.strip().split()
            peers_list.append(
                Peer(
                    peer_ID=int(peer_info[0]),
                    host_name=peer_info[1],
                    listening_port=int(peer_info[2]),
                    has_file = True if int(peer_info[3]) == 1 else False
                )
            )
        return peers_list

def main():
    test = parse_config()
    test2 = parse_peer_info()

if __name__ == "__main__":
    main()