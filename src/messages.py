import struct
# Handshake Section

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