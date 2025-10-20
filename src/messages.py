# this part makes the handshake (prob from CLI input?)
def make_handshake(peer_id: int):
    header = b'P2PFILESHARINGPROJ'
    zero_bits = bytes(10)
    peer_id_bytes = peer_id.to_bytes(4, byteorder='big')
    return header + zero_bits + peer_id_bytes

# this func verifies that the handshake it recieves is valid
# i think this is right but idrk
def verify_handshake(handshake: bytes):
    if len(handshake) != 32:
        return False
    header = handshake[0:18]
    if header != b'P2PFILESHARINGPROJ':
        return False
    zero_bits = handshake[18:28]
    if zero_bits != bytes(10):
        return False
    peer_id_bytes = handshake[28:32]
    if len(peer_id_bytes) != 4: 
        return False
    return True


# After handshaking, each peer can send a stream of actual messages
# I THINK THIS IS COMPLETELY WRONG
def make_actual(payload=b''):
    length = payload[0:4]
    type = int(payload[4:5])
    if not 0 <= type <= 7:
        return "Must be between 0-7"
    if 0 <= type <= 3:
        if len(payload) != 5:
            return "No payload should be present!"
    elif type == 4 or type == 6:
        if len(payload) != 9:
            return "Incorrect payload size!"
    elif type == 5:
        if len(payload) < 6:
            return "Payload too small!"
    elif type == 7:
        if len(payload) < 9:
            return "Payload too small!"