# Handshake Section

# 32 bytes total
HANDSHAKE_HEADER = b"P2PFILESHARINGPROJ" # 18 bits
ZERO_BITS = b"\x00" * 10 # 10 bits
HANDSHAKE_FIRST = HANDSHAKE_HEADER + ZERO_BITS
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
    return HANDSHAKE_HEADER + ZERO_BITS + struct.pack("!I", peer_id) 

def decode_handshake(data: bytes) -> int:
    if(len(data) != 32 or data[:28] != HANDSHAKE_FIRST): # Must be 32 bytes 
        raise ValueError("Bad Handshake! Check length or header + zeros")
    return struct.unpack("!I", data[28:32])[0]

def encode_message(type: int, payload: bytes=b"") -> bytes:
    return struct.pack("!I", 1 + len(payload), + bytes([type]) + payload)


