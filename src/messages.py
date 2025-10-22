import struct
# Handshake Section

# ABDUL'S WORK - MIGHT NEED TO BE DELETED 


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


# DYLAN'S WORK STARTS HERE

# 32 bytes total
HANDSHAKE_HEADER = b"P2PFILESHARINGPROJ" # 18 bytes
ZERO_BYTES = b"\x00" * 10 # 10 bytes
HANDSHAKE_FIRST = HANDSHAKE_HEADER + ZERO_BYTES # 28 bytes
# 4 bit peer ID left

# After handshakes, message
# msg length (4), msg type (1), msg payload (variable size)

# msg length specifies the message length in bytes

# msg types
# no payload types
CHOKE = 0 
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3

HAVE = 4 # 4-byte piece index field in payload

BITFIELD = 5
# N bytes of bitfield, bit i == 1 means that sender has piece i
# Each ith byte covers i -> i+7
# Spare bits are 0
# Shares bitfield at most 1 time, after a successful handshake
# A peer with no pieces may omit bitfield

REQUEST = 6 # 4-byte piece index field in payload, sent only when unchoked

PIECE = 7 # first 4-byte piece index field in payload, then raw piece bytes (full)
# sent only if peer is INTERESTED + UNCHOKED

# Explanation for struct.pack:
# https://docs.python.org/3/library/struct.html
# ! = Network byte order (Big-Endian)
# I = Unsigned int (4 bytes)
# Encode: Packs the peer_id as a 4-byte object
# Decode: Unpacks the 4-byte object as a Python Integer

def encode_handshake(peer_id: int) -> bytes: # Structures 32-byte handshake
    return HANDSHAKE_HEADER + ZERO_BYTES + struct.pack("!I", peer_id) 

def decode_handshake(data: bytes) -> int:
    if(len(data) != 32 or data[:28] != HANDSHAKE_FIRST): # Must be 32 bytes 
        raise ValueError("Bad Handshake! Check length or header + zeros")
    return struct.unpack("!I", data[28:32])[0]

# msg length (4), msg type (1), msg payload (variable size)

def encode_message(type: int, payload: bytes=b"") -> bytes:
    return struct.pack("!I", 1 + len(payload)) + bytes([type]) + payload

def decode_message(buffer: bytearray):
    if(len(buffer) < 4):
        return None
    (length,) = struct.unpack("!I", buffer[:4])
    if(len(buffer) < 4 + length):
        return None
    type = buffer[4]
    payload = bytes(buffer[5:4 + length])
    del buffer[:4 + length]
    return type, payload
